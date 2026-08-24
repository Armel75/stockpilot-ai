"""Ingestion SAGE X3 — lecture des vues SQL Server (ODBC Driver 18).

⚠️ ADAPTEZ ICI : les noms de colonnes de VOS vues X3.
Mapping validé sur les vues réelles du parc (base `basex3`) :
  - Ventes : `VENTES_X3` (REFERENCE, DESIGNATION, FAMILLE, DATE_FACTURE, QTE)
             → agrégées par (référence, jour) pour respecter la contrainte d'unicité.
  - Stocks : `STOCK_TOTAL` (CODE_X3, QTE_TT) → total par produit, date = jour J.
"""
import logging
from datetime import date, datetime
from typing import Any

import pyodbc
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import IngestionLog, Product, Sale, StockSnapshot

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------
# ADAPTEZ ICI : mapping colonnes des vues X3
# ---------------------------------------------------------------
SALES_COLS = {
    "ref": "REFERENCE",
    "name": "DESIGNATION",
    "category": "FAMILLE",
    "date": "DATE_FACTURE",
    "quantity": "QTE",
    # pas de colonne montant : le chiffre d'affaires est confidentiel (revenue = 0)
}

STOCK_COLS = {
    "ref": "CODE_X3",
    "name": "DESIGNATION",
    "category": "FAMILLE",
    "quantity": "QTE_TT",
    # pas de colonne date : snapshot au jour de l'ingestion
}

# Fenêtre d'historique de ventes chargée (jours)
SALES_WINDOW_DAYS = 270


def _connstr(server: str, database: str, user: str, password: str, driver: str) -> str:
    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={server}",
        "TrustServerCertificate=yes",
        "Encrypt=no",
        f"UID={user}",
        f"PWD={password}",
    ]
    if database:
        parts.append(f"DATABASE={database}")
    return ";".join(parts)


def _connect(server: str, database: str, user: str, password: str, driver: str) -> pyodbc.Connection:
    conn = pyodbc.connect(
        _connstr(server, database, user, password, driver),
        timeout=settings.X3_QUERY_TIMEOUT_SECONDS,
        autocommit=True,
    )
    conn.timeout = settings.X3_QUERY_TIMEOUT_SECONDS
    return conn


def _fetch_sales() -> list[dict[str, Any]]:
    cols = SALES_COLS
    sql = (
        f"SELECT [{cols['ref']}] AS ref, "
        f"MAX([{cols['name']}]) AS name, "
        f"MAX([{cols['category']}]) AS category, "
        f"CONVERT(date, [{cols['date']}]) AS date, "
        f"SUM([{cols['quantity']}]) AS quantity "
        f"FROM [{settings.X3_SALES_VIEW}] "
        f"WHERE [{cols['date']}] >= DATEADD(day, -{SALES_WINDOW_DAYS}, GETDATE()) "
        f"AND [{cols['date']}] <= GETDATE() "  # exclut les documents datés dans le futur (pré-factures)
        f"GROUP BY [{cols['ref']}], CONVERT(date, [{cols['date']}])"
    )
    conn = _connect(
        settings.X3_SALES_SERVER, settings.X3_SALES_DATABASE,
        settings.X3_SALES_USER, settings.X3_SALES_PASSWORD, settings.X3_ODBC_DRIVER,
    )
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [c[0] for c in cursor.description]
        rows = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
        logger.info("X3 VENTES : %d lignes (agrégées réf×jour, fenêtre %d j)", len(rows), SALES_WINDOW_DAYS)
        return rows
    finally:
        conn.close()


def _fetch_stock() -> list[dict[str, Any]]:
    cols = STOCK_COLS
    sql = (
        f"SELECT [{cols['ref']}] AS ref, "
        f"MAX([{cols['name']}]) AS name, "
        f"MAX([{cols['category']}]) AS category, "
        f"SUM([{cols['quantity']}]) AS quantity "
        f"FROM [{settings.X3_STOCK_VIEW}] "
        f"GROUP BY [{cols['ref']}]"
    )
    conn = _connect(
        settings.X3_STOCK_SERVER, settings.X3_STOCK_DATABASE,
        settings.X3_STOCK_USER, settings.X3_STOCK_PASSWORD, settings.X3_ODBC_DRIVER,
    )
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [c[0] for c in cursor.description]
        rows = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
        logger.info("X3 STOCKS : %d lignes (total par produit)", len(rows))
        return rows
    finally:
        conn.close()


def _to_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _to_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def ingest_sagex3(db: Session) -> tuple[str, str]:
    """Charge les ventes + stocks X3 dans le stockage applicatif.

    Retourne (source, message). Lève une exception si X3 est injoignable.
    """
    log = IngestionLog(source="sagex3", status="running")
    db.add(log)
    db.commit()

    try:
        sales_rows = _fetch_sales()
        stock_rows = _fetch_stock()
        if not sales_rows and not stock_rows:
            raise RuntimeError("Aucune ligne retournée par les vues X3 (vérifiez le mapping des colonnes)")

        # --- Upsert produits (par référence) ---
        refs: dict[str, dict[str, Any]] = {}
        for r in sales_rows:
            ref = str(r.get("ref")).strip()
            refs.setdefault(ref, {"name": str(r.get("name") or "?"), "category": str(r.get("category") or "")})
        for r in stock_rows:
            ref = str(r.get("ref")).strip()
            # Les produits uniquement présents en stock reçoivent le vrai nom (si dispo)
            refs.setdefault(ref, {"name": "?", "category": ""})
            if refs[ref]["name"] == "?" and r.get("name"):
                refs[ref]["name"] = str(r["name"])[:255]
            if not refs[ref]["category"] and r.get("category"):
                refs[ref]["category"] = str(r["category"])[:100]

        existing = {p.ref: p for p in db.query(Product).filter(Product.ref.in_(refs.keys())).all()}
        for ref, info in refs.items():
            p = existing.get(ref)
            if p is None:
                db.add(Product(ref=ref, name=info["name"][:255], category=info["category"][:100] or None))
            elif not p.name or p.name == "?":
                p.name = info["name"][:255]
        db.commit()

        products = {p.ref: p.id for p in db.query(Product).all()}

        # --- Remplacement des ventes + stocks (FK cascade) ---
        db.execute(delete(Sale))
        db.execute(delete(StockSnapshot))

        sales_rows_db = []
        for r in sales_rows:
            ref = str(r.get("ref")).strip()
            pid = products.get(ref)
            if pid is None:
                continue
            sales_rows_db.append(
                {
                    "product_id": pid,
                    "date": _to_date(r.get("date")),
                    "quantity": _to_float(r.get("quantity")),
                    "revenue": _to_float(r.get("revenue")),  # 0.0 si absente (confidentiel)
                }
            )

        stock_rows_db = []
        for r in stock_rows:
            ref = str(r.get("ref")).strip()
            pid = products.get(ref)
            if pid is None:
                continue
            stock_rows_db.append(
                {
                    "product_id": pid,
                    "date": _to_date(r.get("date")) if r.get("date") else date.today(),
                    "quantity": _to_float(r.get("quantity")),
                    "reserved": _to_float(r.get("reserved")),
                    "in_transit": _to_float(r.get("in_transit")),
                }
            )

        # Insertion en masse (executemany) — volumétrie X3 réelle
        if sales_rows_db:
            db.execute(insert(Sale), sales_rows_db)
        if stock_rows_db:
            db.execute(insert(StockSnapshot), stock_rows_db)
        sales_count = len(sales_rows_db)
        stock_count = len(stock_rows_db)

        db.commit()

        log.status = "success"
        log.finished_at = datetime.utcnow()
        log.rows_loaded = sales_count + stock_count
        log.message = f"{len(products)} produits, {sales_count} ventes, {stock_count} lignes de stock"
        db.commit()

        return "sagex3", f"Données SAGE X3 chargées : {log.message}"
    except Exception as exc:
        db.rollback()
        log.status = "error"
        log.finished_at = datetime.utcnow()
        log.message = str(exc)[:500]
        db.commit()
        raise
