"""Endpoints Précision — score prévision vs réalité (boucle d'apprentissage)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import AccuracyScore

router = APIRouter(prefix="/accuracy", tags=["accuracy"])


@router.get("/latest")
def latest(db: Session = Depends(get_db)):
    global_row = db.execute(
        select(AccuracyScore)
        .where(AccuracyScore.scope == "global")
        .order_by(AccuracyScore.score_date.desc())
        .limit(1)
    ).scalar_one_or_none()
    return {
        "has_score": global_row is not None,
        "score_date": global_row.score_date if global_row else None,
        "mape": round(global_row.mape * 100, 1) if global_row and global_row.mape is not None else None,
        "bias": round(global_row.bias * 100, 1) if global_row and global_row.bias is not None else None,
        "sample_size": global_row.sample_size if global_row else 0,
        "message": "Aucun score disponible : les prévisions doivent être évaluées après échéance (30 j)."
        if global_row is None else None,
    }


@router.get("/history")
def history(db: Session = Depends(get_db)):
    rows = db.execute(
        select(AccuracyScore)
        .where(AccuracyScore.scope == "global")
        .order_by(AccuracyScore.score_date.desc())
        .limit(52)
    ).scalars().all()
    rows.reverse()
    return [
        {
            "score_date": r.score_date,
            "mape": round(r.mape * 100, 1) if r.mape is not None else None,
            "bias": round(r.bias * 100, 1) if r.bias is not None else None,
            "sample_size": r.sample_size,
        }
        for r in rows
    ]


@router.get("/products")
def products_accuracy(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.execute(
        select(AccuracyScore)
        .where(AccuracyScore.scope == "product")
        .order_by(AccuracyScore.score_date.desc())
        .limit(limit)
    ).scalars().all()
    return [
        {
            "product_ref": r.product_ref,
            "score_date": r.score_date,
            "mape": round(r.mape * 100, 1) if r.mape is not None else None,
            "bias": round(r.bias * 100, 1) if r.bias is not None else None,
        }
        for r in rows
    ]
