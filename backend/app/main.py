"""Point d'entrée FastAPI — StockPilot AI."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import accuracy, forecasts, metrics, pilotage, products, signals, system
from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.jobs import scheduler as scheduler_mod

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


def _ensure_demo_data() -> None:
    """Au démarrage : si la base est vide, charge le jeu de démo (déterministe, rapide)."""
    from sqlalchemy import func, select

    from app.ingestion.seed import seed_demo_data
    from app.models.entities import Product

    db = SessionLocal()
    try:
        count = db.scalar(select(func.count(Product.id))) or 0
        if count == 0:
            source, message = seed_demo_data(db)
            logger.info("Démarrage : %s — %s", source, message)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Seed de démarrage ignoré: %s", exc)
    finally:
        db.close()


def _ensure_initial_report() -> None:
    """Déclenche une analyse AUTOMATIQUE au démarrage si aucun rapport du jour.

    Garantit que l'agent est fonctionnel dès le lancement, même en dehors
    de l'heure planifiée (08:30). Passe par la file Redis/worker si dispo,
    sinon exécution de fond (thread) pour ne pas bloquer le démarrage.
    """
    from datetime import date

    from sqlalchemy import func, select

    from app.models.entities import DailyReport

    db = SessionLocal()
    try:
        today = date.today()
        count = db.scalar(
            select(func.count(DailyReport.id)).where(DailyReport.report_date == today)
        ) or 0
    finally:
        db.close()
    if count > 0:
        return  # rapport du jour déjà généré → on ne relance pas

    from app.worker import queue as worker_queue

    if worker_queue.redis_available():
        try:
            job_id = worker_queue.enqueue_agent_run(None)
            logger.info("Agent : premier rapport auto déclenché au démarrage (job %s)", job_id)
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Mise en file au démarrage échouée, repli thread : %s", exc)

    import threading

    def _run_initial() -> None:
        from app.agent.orchestrator import run_agent

        s = SessionLocal()
        try:
            result = run_agent(s)
            logger.info("Agent (démarrage) : %s — %s", result.status, result.message[:120])
        except Exception:  # noqa: BLE001
            logger.exception("Agent (démarrage) en échec")
        finally:
            s.close()

    threading.Thread(target=_run_initial, daemon=True, name="agent-startup").start()
    logger.info("Agent : premier rapport auto déclenché au démarrage (thread de fond)")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    _ensure_demo_data()
    scheduler_mod.start_scheduler()
    _ensure_initial_report()
    logger.info("%s démarré — mode ingestion: %s", settings.APP_NAME, settings.INGESTION_MODE)
    yield
    scheduler_mod.shutdown_scheduler()


app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router, prefix=settings.API_V1_PREFIX)
app.include_router(pilotage.router, prefix=settings.API_V1_PREFIX)
app.include_router(signals.router, prefix=settings.API_V1_PREFIX)
app.include_router(forecasts.router, prefix=settings.API_V1_PREFIX)
app.include_router(products.router, prefix=settings.API_V1_PREFIX)
app.include_router(accuracy.router, prefix=settings.API_V1_PREFIX)
app.include_router(metrics.router)


@app.middleware("http")
async def count_http_requests(request, call_next):
    from app.api.metrics import HTTP_REQUESTS

    response = await call_next(request)
    HTTP_REQUESTS.labels(method=request.method, path=request.url.path).inc()
    return response


@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/system/health",
        "pilotage": f"{settings.API_V1_PREFIX}/pilotage",
    }
