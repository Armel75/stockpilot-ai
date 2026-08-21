"""Moteur de signaux — règles métier déterministes (0 LLM ici).

Détecte : rupture imminente, surstock, stock dormant, accélération des ventes,
opportunités commerciales et besoin de réapprovisionnement.
"""
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Product, Sale, Signal, StockSnapshot

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ProductContext:
    product: Product
    stock: float = 0.0
    reserved: float = 0.0
    in_transit: float = 0.0
    daily_avg_30: float = 0.0
    prev_avg_30: float = 0.0
    growth_pct: float | None = None
    last_sale_date: date | None = None
    forecast_30_mid: float | None = None
    coverage_days: float | None = None
    metrics: dict = field(default_factory=dict)


@dataclass
class SignalSpec:
    product_id: int
    signal_type: str
    priority: str
    metrics: dict


def load_contexts(db: Session, as_of: date) -> list[ProductContext]:
    """Construit un snapshot par produit : stock + ventes récentes + couverture."""
    products = db.scalars(select(Product)).all()
    if not products:
        return []

    # Dernier snapshot de stock par produit
    stock_rows = db.execute(
        select(
            StockSnapshot.product_id,
            func.max(StockSnapshot.date).label("max_date"),
        ).where(StockSnapshot.date <= as_of).group_by(StockSnapshot.product_id)
    ).all()
    latest_stock: dict[int, dict] = {}
    for pid, max_date in stock_rows:
        row = db.execute(
            select(StockSnapshot)
            .where(StockSnapshot.product_id == pid, StockSnapshot.date == max_date)
            .limit(1)
        ).scalar_one_or_none()
        if row:
            latest_stock[pid] = {"qty": row.quantity, "reserved": row.reserved, "in_transit": row.in_transit}

    # Ventes des 60 derniers jours, agrégées par produit et jour
    since = as_of - timedelta(days=60)
    sale_rows = db.execute(
        select(Sale.product_id, Sale.date, func.sum(Sale.quantity).label("qty"))
        .where(Sale.date > since, Sale.date <= as_of)
        .group_by(Sale.product_id, Sale.date)
    ).all()

    by_product: dict[int, dict[date, float]] = {}
    for pid, d, qty in sale_rows:
        by_product.setdefault(pid, {})[d] = float(qty or 0.0)

    contexts: list[ProductContext] = []
    for p in products:
        ctx = ProductContext(product=p)
        st = latest_stock.get(p.id)
        if st:
            ctx.stock = st["qty"]
            ctx.reserved = st["reserved"]
            ctx.in_transit = st["in_transit"]

        daily = by_product.get(p.id, {})
        today = as_of
        last30 = [daily.get(today - timedelta(days=i), 0.0) for i in range(30)]
        prev30 = [daily.get(today - timedelta(days=30 + i), 0.0) for i in range(30)]
        ctx.daily_avg_30 = sum(last30) / 30
        prev_avg = sum(prev30) / 30
        ctx.prev_avg_30 = prev_avg
        if prev_avg > 0:
            ctx.growth_pct = (ctx.daily_avg_30 - prev_avg) / prev_avg
        elif ctx.daily_avg_30 > 0:
            ctx.growth_pct = None  # démarrage récent

        if daily:
            ctx.last_sale_date = max(daily.keys())

        if ctx.daily_avg_30 > 0:
            ctx.coverage_days = ctx.stock / ctx.daily_avg_30

        ctx.metrics = {
            "stock": round(ctx.stock, 2),
            "reserved": round(ctx.reserved, 2),
            "in_transit": round(ctx.in_transit, 2),
            "daily_avg_30": round(ctx.daily_avg_30, 2),
            "growth_pct": round(ctx.growth_pct, 4) if ctx.growth_pct is not None else None,
            "coverage_days": round(ctx.coverage_days, 1) if ctx.coverage_days is not None else None,
            "last_sale_days_ago": (as_of - ctx.last_sale_date).days if ctx.last_sale_date else None,
        }
        contexts.append(ctx)
    return contexts


def build_signals(contexts: list[ProductContext], as_of: date) -> list[SignalSpec]:
    """Applique les règles métier. Retourne les signaux détectés."""
    specs: list[SignalSpec] = []

    for ctx in contexts:
        p = ctx.product
        m = ctx.metrics
        coverage = ctx.coverage_days

        # 1. Rupture imminente
        if ctx.stock > 0 and coverage is not None and coverage < settings.RUPTURE_COVERAGE_DAYS:
            priority = "P0" if coverage < settings.RUPTURE_CRITICAL_COVERAGE_DAYS else "P1"
            specs.append(SignalSpec(p.id, "rupture", priority, {**m, "lead_time_days": p.lead_time_days}))

        # 2. Surstock
        if ctx.stock > 0 and coverage is not None and coverage > settings.OVERSTOCK_COVERAGE_DAYS:
            priority = "P1" if coverage > 2 * settings.OVERSTOCK_COVERAGE_DAYS else "P2"
            specs.append(SignalSpec(p.id, "surstock", priority, m))

        # 3. Stock dormant
        if ctx.stock > 0 and ctx.last_sale_date is not None:
            days_ago = (as_of - ctx.last_sale_date).days
            if days_ago >= settings.DORMANT_DAYS:
                specs.append(SignalSpec(p.id, "dormant", "P2", {**m, "dormant_days": days_ago}))

        # 4. Accélération des ventes
        if ctx.growth_pct is not None and ctx.growth_pct >= settings.ACCELERATION_PCT:
            specs.append(SignalSpec(p.id, "acceleration", "P1", m))

        # 5. Opportunités commerciales (marge + rotation)
        high_margin = p.margin_rate >= 0.25
        if high_margin:
            if coverage is not None and coverage > 45 and (ctx.growth_pct or 0) <= 0:
                specs.append(
                    SignalSpec(p.id, "opportunite", "P2",
                               {**m, "opportunity": "stock_excedent_marge_elevee"})
                )
            if coverage is not None and coverage < settings.RUPTURE_COVERAGE_DAYS and (ctx.growth_pct or 0) > 0:
                specs.append(
                    SignalSpec(p.id, "opportunite", "P1",
                               {**m, "opportunity": "demande_forte_marge_elevee"})
                )

        # 6. Réapprovisionnement recommandé
        daily = ctx.daily_avg_30
        if daily > 0:
            lead_time = p.lead_time_days or 15
            min_qty = p.min_order_qty or 1
            forecast_lead = (ctx.forecast_30_mid or (daily * 30)) / 30 * lead_time
            safety = settings.SAFETY_STOCK_DAYS * daily
            suggested = forecast_lead + safety - ctx.stock - ctx.in_transit
            if suggested > max(min_qty, 1):
                priority = "P1" if coverage is not None and coverage < settings.RUPTURE_COVERAGE_DAYS else "P2"
                specs.append(
                    SignalSpec(p.id, "reappro", priority,
                               {**m, "suggested_qty": round(suggested, 0), "safety_stock": round(safety, 0)})
                )

    return specs


def persist_signals(db: Session, specs: list[SignalSpec], as_of: date) -> list[Signal]:
    """Marque les signaux ouverts obsolètes comme résolus, puis insère les nouveaux."""
    db.execute(
        Signal.__table__.update()
        .where(Signal.status == "open")
        .values(status="resolved")
    )
    db.flush()

    created: list[Signal] = []
    for spec in specs:
        sig = Signal(
            product_id=spec.product_id,
            signal_type=spec.signal_type,
            priority=spec.priority,
            status="open",
            metrics=spec.metrics,
            computed_at=as_of,
        )
        db.add(sig)
        created.append(sig)
    db.commit()
    return created
