"""Endpoints Prévisions — séries 30 j pour les graphiques."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import Forecast, Product
from app.schemas.api import ForecastOut, ForecastPoint

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


def _latest_batch_date(db: Session) -> date | None:
    value = db.execute(select(func.max(func.date(Forecast.created_at)))).scalar_one_or_none()
    return value


@router.get("", response_model=list[ForecastOut])
def get_forecasts(
    product_ref: str | None = None,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    batch_date = _latest_batch_date(db)
    if batch_date is None:
        return []

    stmt = (
        select(Forecast, Product)
        .join(Product, Product.id == Forecast.product_id)
        .where(func.date(Forecast.created_at) == batch_date)
    )
    if product_ref:
        stmt = stmt.where(Product.ref == product_ref)
    rows = db.execute(stmt).all()

    grouped: dict[int, tuple[Product, list[tuple[Forecast, Product]]]] = {}
    for f, p in rows:
        grouped.setdefault(p.id, (p, []))[1].append((f, p))

    # Tri par volume total prévu (milieu de fourchette)
    totals = {pid: sum(f.mid for f, _ in items) for pid, (p, items) in grouped.items()}
    ranked = sorted(totals, key=totals.get, reverse=True)

    if not product_ref:
        ranked = ranked[:limit]

    out: list[ForecastOut] = []
    for pid in ranked:
        p, items = grouped[pid]
        items.sort(key=lambda x: x[0].forecast_date)
        out.append(
            ForecastOut(
                product_ref=p.ref,
                product_name=p.name,
                horizon_days=len(items),
                points=[
                    ForecastPoint(
                        date=f.forecast_date,
                        low=round(f.low, 1),
                        mid=round(f.mid, 1),
                        high=round(f.high, 1),
                    )
                    for f, _ in items
                ],
            )
        )
    return out
