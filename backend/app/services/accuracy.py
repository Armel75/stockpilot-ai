"""Boucle d'apprentissage — compare « prévision vs réalité ».

Produit un score MAPE (erreur moyenne %) et un biais (sur/sous-prévision)
par produit et global. C'est la mesure de confiance publiée à l'équipe.
"""
import logging
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import AccuracyScore, Forecast, Product, Sale

logger = logging.getLogger(__name__)
settings = get_settings()


def _window_actuals(db: Session, product_id: int, start: date, end: date) -> float:
    value = db.execute(
        select(func.coalesce(func.sum(Sale.quantity), 0)).where(
            Sale.product_id == product_id,
            Sale.date >= start,
            Sale.date <= end,
        )
    ).scalar_one()
    return float(value or 0.0)


def compute_accuracy(db: Session, as_of: date) -> list[AccuracyScore]:
    """Évalue les prévisions dont la fenêtre est arrivée à échéance."""
    horizon = settings.FORECAST_HORIZON_DAYS
    cutoff = as_of - timedelta(days=horizon)

    products = db.scalars(select(Product)).all()
    per_product: list[tuple[str, float, float]] = []

    for p in products:
        batch_date = db.execute(
            select(func.max(func.date(Forecast.created_at))).where(
                Forecast.product_id == p.id,
                func.date(Forecast.created_at) <= cutoff,
            )
        ).scalar_one_or_none()
        if not batch_date:
            continue

        rows = db.execute(
            select(Forecast).where(
                Forecast.product_id == p.id,
                func.date(Forecast.created_at) == batch_date,
            )
        ).scalars().all()
        if not rows:
            continue

        pred_mid = sum(r.mid for r in rows)
        start = batch_date + timedelta(days=1)
        end = batch_date + timedelta(days=horizon)
        actual = _window_actuals(db, p.id, start, end)
        if actual <= 0:
            continue

        mape = abs(actual - pred_mid) / actual
        bias = (pred_mid - actual) / actual
        per_product.append((p.ref, mape, bias))

    saved: list[AccuracyScore] = []

    if per_product:
        g_mape = sum(x[1] for x in per_product) / len(per_product)
        g_bias = sum(x[2] for x in per_product) / len(per_product)
        saved.append(
            AccuracyScore(
                score_date=as_of, scope="global", mape=g_mape, bias=g_bias, sample_size=len(per_product)
            )
        )
        for ref, mape, bias in per_product:
            saved.append(
                AccuracyScore(
                    score_date=as_of, scope="product", product_ref=ref, mape=mape, bias=bias, sample_size=1
                )
            )

    if saved:
        db.add_all(saved)
        db.commit()
        logger.info("Précision calculée : %d produits (MAPE global %.1f %%)", len(per_product), g_mape * 100)

    return saved
