"""File de travail asynchrone — Redis + RQ.

L'exécution de l'agent (prévisions + signaux + narration DeepSeek) est
déportée dans un worker : l'API répond instantanément, le calcul tourne
en arrière-plan. Repli synchrone si Redis est indisponible.
"""
import logging

import redis
from rq import Queue
from rq.job import Job

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)
    return _redis


def get_queue() -> Queue:
    return Queue(settings.RQ_QUEUE_NAME, connection=get_redis())


def redis_available() -> bool:
    try:
        return bool(get_redis().ping())
    except Exception:  # noqa: BLE001
        return False


def enqueue_agent_run(mode: str | None = None) -> str:
    """Met une exécution de l'agent en file. Retourne le job_id. Lève si Redis KO."""
    from app.core.database import SessionLocal
    from app.models.entities import AgentRun

    resolved = mode or settings.INGESTION_MODE
    job = get_queue().enqueue(
        "app.worker.tasks.run_agent_task",
        resolved,
        job_timeout=1800,
        result_ttl=86400,
    )

    db = SessionLocal()
    try:
        db.add(AgentRun(job_id=job.id, mode=resolved, status="queued"))
        db.commit()
    except Exception:  # noqa: BLE001 — la trace RQ suffit en secours
        db.rollback()
    finally:
        db.close()
    logger.info("Agent en file : job %s (mode %s)", job.id, resolved)
    return job.id


def fetch_job(job_id: str) -> Job | None:
    try:
        return Job.fetch(job_id, connection=get_redis())
    except Exception:  # noqa: BLE001 — job expiré/inconnu
        return None
