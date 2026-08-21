"""Endpoints Signaux — signaux ouverts détectés par les règles métier."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import Product, Signal
from app.schemas.api import SignalOut

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=list[SignalOut])
def list_signals(
    status: str = "open",
    signal_type: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    stmt = (
        select(Signal, Product)
        .join(Product, Product.id == Signal.product_id)
        .where(Signal.status == status)
        .order_by(Signal.computed_at.desc())
        .limit(limit)
    )
    if signal_type:
        stmt = stmt.where(Signal.signal_type == signal_type)

    rows = db.execute(stmt).all()
    out = []
    for sig, prod in rows:
        item = SignalOut.model_validate(sig)
        item.product_ref = prod.ref
        item.product_name = prod.name
        out.append(item)
    return out
