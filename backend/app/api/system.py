"""Endpoints Système — santé, ingestion, exécution asynchrone de l'agent."""
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.entities import AgentRun, IngestionLog, Product, Sale, StockSnapshot
from app.schemas.api import AgentJobOut, AgentRunResult

router = APIRouter(prefix="/system", tags=["system"])
settings = get_settings()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    nb_products = db.scalar(select(func.count(Product.id))) or 0
    nb_sales = db.scalar(select(func.count(Sale.id))) or 0
    last_ingestion = db.execute(
        select(IngestionLog).order_by(IngestionLog.id.desc()).limit(1)
    ).scalar_one_or_none()
    data_date = db.scalar(select(func.max(StockSnapshot.date)))
    if data_date is None:
        data_date = db.scalar(select(func.max(Sale.date)))
    last_run = db.execute(
        select(AgentRun)
        .where(AgentRun.status.in_(["finished", "failed"]))
        .order_by(AgentRun.finished_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "nb_products": nb_products,
        "nb_sales": nb_sales,
        "data_date": str(data_date) if data_date else None,
        "ingestion_mode": settings.INGESTION_MODE,
        "last_ingestion": last_ingestion.status if last_ingestion else None,
        "last_agent_run": last_run.status if last_run else None,
        "deepseek_configured": bool(settings.DEEPSEEK_API_KEY),
    }


def _start_agent(mode: str | None, db: Session) -> AgentJobOut:
    """Lance l'agent. Async via Redis/RQ si dispo, sinon synchrone (repli)."""
    from app.agent.orchestrator import run_agent
    from app.worker import queue as worker_queue

    if worker_queue.redis_available():
        job_id = worker_queue.enqueue_agent_run(mode)
        return AgentJobOut(job_id=job_id, status="queued", mode=mode or settings.INGESTION_MODE)

    # Repli synchrone (pas de Redis) — préserve le comportement existant
    result = run_agent(db, mode=mode)
    status = "finished" if result.status == "success" else "failed"
    db.add(
        AgentRun(
            job_id=f"sync-{uuid4().hex[:12]}",
            mode=mode or settings.INGESTION_MODE,
            status=status,
            result=result.model_dump(),
            error=None if result.status == "success" else result.message,
            finished_at=datetime.utcnow(),
        )
    )
    db.commit()
    return AgentJobOut(
        job_id=None,
        status=status,
        mode=mode or settings.INGESTION_MODE,
        result=result,
        error=None if result.status == "success" else result.message,
    )


@router.post("/agent/run", response_model=AgentJobOut)
def run_agent_now(mode: str | None = None, db: Session = Depends(get_db)):
    return _start_agent(mode, db)


@router.post("/ingest", response_model=AgentJobOut)
def ingest(mode: str | None = None, db: Session = Depends(get_db)):
    return _start_agent(mode or "seed", db)


@router.get("/agent/jobs/{job_id}", response_model=AgentJobOut)
def agent_job_status(job_id: str, db: Session = Depends(get_db)):
    run = db.execute(
        select(AgentRun).where(AgentRun.job_id == job_id)
    ).scalar_one_or_none()

    if run is None:
        # Tâche sans trace locale : interroge directement Redis/RQ
        from app.worker import queue as worker_queue

        job = worker_queue.fetch_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Tâche inconnue ou expirée")
        status = (
            "failed"
            if job.is_failed
            else ("finished" if job.is_finished else ("started" if job.started_at else "queued"))
        )
        result = job.result if isinstance(job.result, dict) else None
        return AgentJobOut(
            job_id=job_id,
            status=status,
            result=AgentRunResult.model_validate(result) if result else None,
            error=str(job.exc_info) if job.exc_info else None,
        )

    return AgentJobOut(
        job_id=run.job_id,
        status=run.status,
        mode=run.mode,
        result=AgentRunResult.model_validate(run.result) if run.result else None,
        error=run.error,
    )


@router.get("/agent/runs", response_model=list[AgentJobOut])
def recent_agent_runs(limit: int = 20, db: Session = Depends(get_db)):
    rows = db.execute(
        select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit)
    ).scalars().all()
    return [
        AgentJobOut(
            job_id=r.job_id,
            status=r.status,
            mode=r.mode,
            result=AgentRunResult.model_validate(r.result) if r.result else None,
            error=r.error,
        )
        for r in rows
    ]


@router.get("/ingestion-logs", response_model=list[dict])
def ingestion_logs(limit: int = 20, db: Session = Depends(get_db)):
    rows = db.execute(
        select(IngestionLog).order_by(IngestionLog.id.desc()).limit(limit)
    ).scalars().all()
    return [
        {
            "id": r.id,
            "source": r.source,
            "status": r.status,
            "rows_loaded": r.rows_loaded,
            "message": r.message,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
        }
        for r in rows
    ]
