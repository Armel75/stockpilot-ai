"""Ingestion SAGE X3 — lecture des vues SQL Server (ODBC Driver 18).

⚠️ ADAPTEZ ICI : les noms de colonnes de VOS vues X3 (V_VENTES / V_STOCKS).
Le mapping ci-dessous est une hypothèse documentée — ajustez-le à votre schéma réel.
"""
import logging
from datetime import date, datetime
from typing import Any

import pyodbc
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import IngestionLog, Product, Sale, StockSnapshot

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------
# ADAPTEZ ICI : mapping colonnes des vues X3
# ---------------------------------------------------------------
SALES_COLS = {
    "ref": "PRODUIT_REF",
    "name": "PRODUIT_DESIGNATION",
    "category": "FAMILLE",
    "date": "DATE_FACTURE",
    "quantity": "QUANTITE",
    "revenue": "MONTANT",
}

STOCK_COLS = {
    "ref": "PRODUIT_REF",
    "date": "DATE_STOCK",
    "quantity": "STOCK",
    "reserved": "RESERVE",
    "in_transit": "EN_TRANSIT",
}


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
        f"SELECT [{cols['ref']}] AS ref, [{cols['name']}] AS name, "
        f"[{cols['category']}] AS category, [{cols['date']}] AS date, "
        f"[{cols['quantity']}] AS quantity, [{cols['revenue']}] AS revenue "
        f"FROM [{settings.X3_SALES_VIEW}] "
        f"WHERE [{cols['date']}] >= DATEADD(day, -270, GETDATE())"
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
        logger.info("X3 VENTES : %d lignes", len(rows))
        return rows
    finally:
        conn.close()


def _fetch_stock() -> list[dict[str, Any]]:
    cols = STOCK_COLS
    sql = (
        f"SELECT [{cols['ref']}] AS ref, [{cols['date']}] AS date, "
        f"[{cols['quantity']}] AS quantity, "
        f"[{cols['reserved']}] AS reserved, [{cols['in_transit']}] AS in_transit "
        f"FROM [{settings.X3_STOCK_VIEW}]"
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
        logger.info("X3 STOCKS : %d lignes", len(rows))
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
            refs.setdefault(str(r.get("ref")).strip(), {"name": "?", "category": ""})

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

        sales_count = 0
        for r in sales_rows:
            ref = str(r.get("ref")).strip()
            pid = products.get(ref)
            if pid is None:
                continue
            db.add(Sale(
                product_id=pid,
                date=_to_date(r.get("date")),
                quantity=_to_float(r.get("quantity")),
                revenue=_to_float(r.get("revenue")),
            ))
            sales_count += 1

        stock_count = 0
        for r in stock_rows:
            ref = str(r.get("ref")).strip()
            pid = products.get(ref)
            if pid is None:
                continue
            db.add(StockSnapshot(
                product_id=pid,
                date=_to_date(r.get("date")),
                quantity=_to_float(r.get("quantity")),
                reserved=_to_float(r.get("reserved")),
                in_transit=_to_float(r.get("in_transit")),
            ))
            stock_count += 1

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
