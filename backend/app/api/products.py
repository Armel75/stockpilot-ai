"""Endpoints Produits — catalogue avec statut stock / signaux ouverts."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.entities import Product, Sale, Signal, StockSnapshot
from app.schemas.api import ProductOut

router = APIRouter(prefix="/products", tags=["products"])
settings = get_settings()


class ProductStatusOut(BaseModel):
    product: ProductOut
    stock: float = 0.0
    coverage_days: float | None = None
    daily_avg_30: float = 0.0
    open_signals: list[str] = []

    class Config:
        from_attributes = True


@router.get("", response_model=list[ProductStatusOut])
def list_products(
    q: str | None = None,
    category: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    stmt = select(Product)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Product.ref.ilike(like)) | (Product.name.ilike(like)))
    if category:
        stmt = stmt.where(Product.category == category)
    products = db.execute(stmt.order_by(Product.ref).offset(skip).limit(limit)).scalars().all()

    # Dernier stock par produit
    stock_rows = db.execute(
        select(
            StockSnapshot.product_id,
            func.max(StockSnapshot.date).label("max_date"),
        ).group_by(StockSnapshot.product_id)
    ).all()
    latest_stock: dict[int, float] = {}
    for pid, max_date in stock_rows:
        row = db.execute(
            select(StockSnapshot.quantity)
            .where(StockSnapshot.product_id == pid, StockSnapshot.date == max_date)
            .limit(1)
        ).scalar_one_or_none()
        if row is not None:
            latest_stock[pid] = float(row)

    # Signaux ouverts
    open_sig = db.execute(
        select(Signal.product_id, Signal.signal_type)
        .where(Signal.status == "open")
    ).all()
    signals_by_product: dict[int, list[str]] = {}
    for pid, st in open_sig:
        signals_by_product.setdefault(pid, []).append(st)

    out: list[ProductStatusOut] = []
    for p in products:
        stock = latest_stock.get(p.id, 0.0)
        daily_avg = 0.0
        sales = db.execute(
            select(Sale.date, Sale.quantity)
            .where(Sale.product_id == p.id)
            .order_by(Sale.date.desc())
            .limit(30)
        ).all()
        if sales:
            daily_avg = sum(q for _, q in sales) / len(sales)
        coverage = stock / daily_avg if daily_avg > 0 else None
        out.append(
            ProductStatusOut(
                product=ProductOut.model_validate(p),
                stock=round(stock, 2),
                coverage_days=round(coverage, 1) if coverage is not None else None,
                daily_avg_30=round(daily_avg, 2),
                open_signals=signals_by_product.get(p.id, []),
            )
        )
    return out


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Product.category).where(Product.category.is_not(None)).distinct().order_by(Product.category)
    ).scalars().all()
    return [c for c in rows if c]
