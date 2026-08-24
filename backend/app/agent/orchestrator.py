"""ORCHESTRATEUR — la boucle complète de l'Agent.

percevoir (ingestion) → analyser (prévision + signaux) → décider (narration LLM)
→ agir (persistance du point de situation) → apprendre (score hebdo séparé).
"""
import logging
import time
from datetime import date, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import (
    Assertion,
    DailyReport,
    Forecast,
    Product,
    Sale,
    Signal,
)
from app.schemas.api import AgentRunResult
from app.services import forecast as fsvc
from app.services import narrator
from app.services import signals as signals_svc

logger = logging.getLogger(__name__)
settings = get_settings()

_MAX_FORECAST_PRODUCTS = 800


def _ingest(db: Session, mode: str) -> tuple[str, str]:
    """Charge les données (percevoir). Retourne (source, message)."""
    from app.ingestion.sagex3 import ingest_sagex3
    from app.ingestion.seed import seed_demo_data

    if mode == "seed":
        return seed_demo_data(db)
    if mode == "sagex3":
        return ingest_sagex3(db)

    # auto : X3 d'abord, repli seed si injoignable
    try:
        source, message = ingest_sagex3(db)
        return source, message
    except Exception as exc:  # noqa: BLE001
        logger.warning("SAGE X3 injoignable (%s) — bascule seed démo", exc)
        return seed_demo_data(db)


def _run_forecasts(db: Session, as_of: date) -> tuple[int, dict[int, float]]:
    """Calcule et persiste les prévisions 30 j. Retourne (nb produits, mid par produit)."""
    # Nettoyage des vieux lots déjà évalués + ré-exécution du jour (1 lot max par jour)
    old_cutoff = as_of - timedelta(days=settings.FORECAST_HORIZON_DAYS + 5)
    db.execute(
        delete(Forecast).where(func.date(Forecast.created_at) < old_cutoff)
    )
    db.execute(delete(Forecast).where(func.date(Forecast.created_at) == as_of))
    db.flush()

    horizon = settings.FORECAST_HORIZON_DAYS
    products = db.scalars(select(Product).limit(_MAX_FORECAST_PRODUCTS)).all()
    forecasted = 0
    forecast_mid: dict[int, float] = {}

    for p in products:
        rows = db.execute(
            select(Sale.date, Sale.quantity)
            .where(Sale.product_id == p.id, Sale.date <= as_of)
            .order_by(Sale.date)
        ).all()
        if not rows:
            continue
        dates = [r[0] for r in rows]
        values = [float(r[1]) for r in rows]

        result = fsvc.forecast_series(dates, values, horizon)
        if not result:
            continue

        for r in result:
            db.add(
                Forecast(
                    product_id=p.id,
                    forecast_date=r.horizon_date,
                    low=r.low,
                    mid=r.mid,
                    high=r.high,
                    model=r.model,
                )
            )
        forecast_mid[p.id] = round(sum(r.mid for r in result), 1)
        forecasted += 1

    db.commit()
    return forecasted, forecast_mid


def _compute_signals(db: Session, as_of: date, forecast_mid: dict[int, float]) -> list[Signal]:
    contexts = signals_svc.load_contexts(db, as_of)
    for ctx in contexts:
        ctx.forecast_30_mid = forecast_mid.get(ctx.product.id)
    specs = signals_svc.build_signals(contexts, as_of)
    return signals_svc.persist_signals(db, specs, as_of)


def _narrate_and_persist(
    db: Session, as_of: date, signals: list[Signal]
) -> tuple[str, int, bool]:
    products = {p.id: p for p in db.scalars(select(Product)).all()}
    sig_product = [(s, products[s.product_id]) for s in signals if s.product_id in products]

    summary, assertions, llm_used = narrator.narrate(db, as_of, sig_product)

    # Remplace les affirmations du jour (ré-exécution sûre)
    db.execute(delete(Assertion).where(Assertion.report_date == as_of))
    db.flush()

    for a in assertions:
        db.add(
            Assertion(
                report_date=as_of,
                priority=a.priority,
                type=a.type,
                title=a.title,
                message=a.message,
                product_ref=a.product_ref or None,
                product_name=a.product_name or None,
                confidence=a.confidence,
                action=a.action,
                evidence=[
                    e.model_dump() if hasattr(e, "model_dump") else e
                    for e in a.evidence
                ],
            )
        )

    kpis = _compute_kpis(db, as_of, signals)

    # Remplace le rapport du jour (ré-exécution sûre, contrainte UNIQUE)
    db.execute(delete(DailyReport).where(DailyReport.report_date == as_of))
    db.flush()
    db.add(
        DailyReport(
            report_date=as_of,
            summary=summary,
            nb_assertions=len(assertions),
            top_p0=[a.title for a in assertions if a.priority == "P0"][:8],
            kpis=kpis,
        )
    )
    db.commit()
    return summary, len(assertions), llm_used


def _compute_kpis(db: Session, as_of: date, signals: list[Signal]) -> dict:
    from app.services.signals import load_contexts

    contexts = load_contexts(db, as_of)
    coverage_values = [c.coverage_days for c in contexts if c.coverage_days is not None]
    counts = {"rupture": 0, "surstock": 0, "dormant": 0, "opportunite": 0, "reappro": 0}
    for s in signals:
        if s.signal_type in counts:
            counts[s.signal_type] += 1

    return {
        "nb_ruptures": counts["rupture"],
        "nb_overstock": counts["surstock"],
        "nb_dormant": counts["dormant"],
        "nb_opportunities": counts["opportunite"],
        "nb_reappro": counts["reappro"],
        "avg_coverage_days": round(sum(coverage_values) / len(coverage_values), 1)
        if coverage_values else 0.0,
        "nb_products": len(contexts),
    }


def run_agent(db: Session, mode: str | None = None) -> AgentRunResult:
    """Exécute une passe complète de l'agent. Thread-safe (sa propre session)."""
    t0 = time.time()
    mode = mode or settings.INGESTION_MODE
    as_of = date.today()

    try:
        source, message = _ingest(db, mode)
        nb_forecast, forecast_mid = _run_forecasts(db, as_of)
        signals = _compute_signals(db, as_of, forecast_mid)
        summary, nb_assertions, llm_used = _narrate_and_persist(db, as_of, signals)

        nb_products = db.scalar(select(func.count(Product.id))) or 0
        return AgentRunResult(
            status="success",
            message=summary,
            data_source=source,
            nb_products=nb_products,
            nb_forecast=nb_forecast,
            nb_signals=len(signals),
            nb_assertions=nb_assertions,
            llm_used=llm_used,
            duration_seconds=round(time.time() - t0, 1),
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception("Échec de la passe agent")
        return AgentRunResult(
            status="error",
            message=f"{message if 'message' in locals() else ''} Erreur: {exc}",
            data_source=source if "source" in locals() else mode,
            duration_seconds=round(time.time() - t0, 1),
        )
