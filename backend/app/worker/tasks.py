"""Tâches exécutées par le worker RQ (processus séparé).

Une tâche = une exécution complète de la boucle de l'agent.
La trace est persistée dans `agent_runs` (robuste même si Redis purge).
"""
import logging
from datetime import datetime

from rq import get_current_job

from app.core.database import SessionLocal
from app.models.entities import AgentRun

logger = logging.getLogger(__name__)


def run_agent_task(mode: str | None = None) -> dict:
    from app.agent.orchestrator import run_agent

    job = get_current_job()
    job_id = job.id if job else "manual"

    db = SessionLocal()
    try:
        run = db.query(AgentRun).filter(AgentRun.job_id == job_id).first()
        if run is None:
            run = AgentRun(job_id=job_id, mode=mode or "auto", status="started")
            db.add(run)
        run.status = "started"
        db.commit()
        logger.info("Agent (worker) : démarrage du job %s", job_id)

        result = run_agent(db, mode=mode)
        payload = result.model_dump()
        run.status = "finished" if result.status == "success" else "failed"
        run.result = payload
        if result.status != "success":
            run.error = result.message
        run.finished_at = datetime.utcnow()
        db.commit()
        logger.info("Agent (worker) : job %s terminé (%s)", job_id, run.status)
        return payload
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        run = db.query(AgentRun).filter(AgentRun.job_id == job_id).first()
        if run is not None:
            run.status = "failed"
            run.error = str(exc)[:1000]
            run.finished_at = datetime.utcnow()
            db.commit()
        logger.exception("Agent (worker) : job %s en échec", job_id)
        raise
    finally:
        db.close()
