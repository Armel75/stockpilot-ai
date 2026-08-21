"""Planification — APScheduler : point de situation quotidien + score hebdo."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler: BackgroundScheduler | None = None


def _run_agent_job() -> None:
    from app.worker import queue as worker_queue

    if worker_queue.redis_available():
        try:
            job_id = worker_queue.enqueue_agent_run(None)
            logger.info("Agent planifié : job %s en file", job_id)
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Mise en file échouée, repli synchrone : %s", exc)

    from app.agent.orchestrator import run_agent

    db = SessionLocal()
    try:
        result = run_agent(db)
        logger.info("Agent (planifié, synchrone) : %s — %s", result.status, result.message[:120])
    finally:
        db.close()


def _run_accuracy_job() -> None:
    from datetime import date

    from app.services.accuracy import compute_accuracy

    db = SessionLocal()
    try:
        scores = compute_accuracy(db, date.today())
        logger.info("Score de précision hebdo : %d lignes", len(scores))
    finally:
        db.close()


def start_scheduler() -> None:
    global scheduler
    if scheduler is not None:
        return

    scheduler = BackgroundScheduler(timezone="Africa/Douala")
    scheduler.add_job(
        _run_agent_job,
        CronTrigger(
            hour=settings.BRIEFING_HOUR,
            minute=settings.BRIEFING_MINUTE,
        ),
        id="daily_briefing",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_accuracy_job,
        CronTrigger(day_of_week="sun", hour=7, minute=30),
        id="weekly_accuracy",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler démarré : briefing quotidien à %02d:%02d, score hebdo dimanche 07:30",
        settings.BRIEFING_HOUR,
        settings.BRIEFING_MINUTE,
    )


def shutdown_scheduler() -> None:
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
