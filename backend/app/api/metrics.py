"""Métriques Prometheus — exposées sur /metrics.

Les métriques « métier » sont relues depuis PostgreSQL au moment du scrape :
elles reflètent l'état réel du pipeline (API + worker), pas un processus isolé.
"""
from fastapi import APIRouter, Depends
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    generate_latest,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.core.database import get_db
from app.models.entities import AgentRun, Signal

router = APIRouter(tags=["metrics"])
registry = CollectorRegistry()

HTTP_REQUESTS = Counter(
    "http_requests_total", "Requêtes HTTP reçues", ["method", "path"], registry=registry
)
LAST_RUN_DURATION = Gauge(
    "agent_last_run_duration_seconds", "Durée de la dernière exécution de l'agent", registry=registry
)
LAST_RUN_TIMESTAMP = Gauge(
    "agent_last_run_timestamp", "Timestamp de fin de la dernière exécution", registry=registry
)
RUNS_BY_STATUS = Gauge(
    "agent_runs_total", "Exécutions de l'agent par statut", ["status"], registry=registry
)
SIGNALS_OPEN = Gauge("agent_signals_open", "Signaux ouverts (non résolus)", registry=registry)


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    last = db.execute(
        select(AgentRun)
        .where(AgentRun.status.in_(["finished", "failed"]))
        .order_by(AgentRun.finished_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if last and last.finished_at:
        LAST_RUN_DURATION.set(float((last.result or {}).get("duration_seconds", 0)))
        LAST_RUN_TIMESTAMP.set(last.finished_at.timestamp())
    else:
        LAST_RUN_DURATION.set(0)
        LAST_RUN_TIMESTAMP.set(0)

    for status in ("queued", "started", "finished", "failed"):
        count = db.scalar(select(func.count(AgentRun.id)).where(AgentRun.status == status)) or 0
        RUNS_BY_STATUS.labels(status=status).set(count)

    SIGNALS_OPEN.set(db.scalar(select(func.count(Signal.id)).where(Signal.status == "open")) or 0)

    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
