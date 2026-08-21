"""Endpoints Pilotage — le « point de situation » affiché aux utilisateurs."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.entities import Assertion, DailyReport, IngestionLog, Product, Sale, Signal, StockSnapshot
from app.schemas.api import (
    AssertionOut,
    FeedbackIn,
    Freshness,
    Kpis,
    PilotageOut,
)

router = APIRouter(tags=["pilotage"])
settings = get_settings()

_PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2}


@router.get("/pilotage", response_model=PilotageOut)
def get_pilotage(db: Session = Depends(get_db)):
    today = date.today()
    report = db.execute(
        select(DailyReport).where(DailyReport.report_date == today).order_by(DailyReport.id.desc())
    ).scalars().first()
    if report is None:
        report = db.execute(
            select(DailyReport).order_by(DailyReport.created_at.desc())
        ).scalars().first()

    assertions: list[Assertion] = []
    if report:
        assertions = db.execute(
            select(Assertion).where(Assertion.report_date == report.report_date)
        ).scalars().all()
    assertions.sort(key=lambda a: (_PRIORITY_RANK.get(a.priority, 3), -a.confidence))

    # Fraîcheur des données
    data_date = db.scalar(select(func.max(StockSnapshot.date)))
    if data_date is None:
        data_date = db.scalar(select(func.max(Sale.date)))
    if data_date is not None and isinstance(data_date, str):
        data_date = date.fromisoformat(data_date[:10])

    source = None
    last_log = db.execute(
        select(IngestionLog).order_by(IngestionLog.id.desc()).limit(1)
    ).scalar_one_or_none()
    if last_log:
        source = last_log.source

    fresh = data_date is not None and (today - data_date).days <= settings.DATA_MAX_AGE_DAYS

    kpis_data = report.kpis if report and report.kpis else {}
    kpis = Kpis(
        nb_ruptures=kpis_data.get("nb_ruptures", 0),
        nb_overstock=kpis_data.get("nb_overstock", 0),
        nb_dormant=kpis_data.get("nb_dormant", 0),
        nb_opportunities=kpis_data.get("nb_opportunities", 0),
        nb_reappro=kpis_data.get("nb_reappro", 0),
        avg_coverage_days=kpis_data.get("avg_coverage_days", 0.0),
        nb_products=kpis_data.get("nb_products", 0),
    )

    freshness_msg = (
        f"Données de stock du {data_date.isoformat() if data_date else '—'} : "
        f"potentiellement obsolètes (max {settings.DATA_MAX_AGE_DAYS} jours)."
    )
    freshness = Freshness(
        data_date=data_date,
        is_fresh=fresh,
        source=source,
        message="" if fresh else freshness_msg,
    )

    # Décisions du jour — synthèse exécutive DÉTERMINISTE (sans LLM)
    from app.services.decisions import build_decisions

    sig_rows = db.execute(
        select(Signal).where(Signal.status == "open").order_by(Signal.computed_at.desc())
    ).scalars().all()
    products = {p.id: p for p in db.scalars(select(Product)).all()}
    decisions = build_decisions(
        [(s, products[s.product_id]) for s in sig_rows if s.product_id in products]
    )

    return PilotageOut(
        report_date=report.report_date if report else today,
        summary=report.summary if report else "Aucun point de situation généré. Lancez l'agent.",
        kpis=kpis,
        freshness=freshness,
        assertions=[AssertionOut.model_validate(a) for a in assertions],
        decisions=decisions,
        agent_last_run=report.created_at if report else None,
    )





@router.get("/assertions", response_model=list[AssertionOut])
def list_assertions(
    priority: str | None = None,
    report_date: date | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Assertion)
    if priority:
        stmt = stmt.where(Assertion.priority == priority.upper())
    if report_date:
        stmt = stmt.where(Assertion.report_date == report_date)
    rows = db.execute(stmt.order_by(Assertion.created_at.desc()).limit(100)).scalars().all()
    return [AssertionOut.model_validate(a) for a in rows]


@router.post("/assertions/{assertion_id}/feedback", response_model=AssertionOut)
def submit_feedback(assertion_id: int, payload: FeedbackIn, db: Session = Depends(get_db)):
    assertion = db.get(Assertion, assertion_id)
    if assertion is None:
        raise HTTPException(status_code=404, detail="Affirmation introuvable")
    assertion.feedback = payload.feedback
    assertion.feedback_note = payload.note
    db.commit()
    return AssertionOut.model_validate(assertion)
