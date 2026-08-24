"""Vérifie les horloges et les dates max réelles (lecture seule)."""
import sys

sys.path.insert(0, ".")
import datetime

import pyodbc

from app.core.config import get_settings

s = get_settings()

print("Horloge conteneur (date.today) :", datetime.date.today())

cs = (
    f"DRIVER={{{s.X3_ODBC_DRIVER}}};SERVER={s.X3_SALES_SERVER};"
    "TrustServerCertificate=yes;Encrypt=no;"
    f"UID={s.X3_SALES_USER};PWD={s.X3_SALES_PASSWORD};DATABASE=basex3"
)
conn = pyodbc.connect(cs, timeout=30, autocommit=True)
cur = conn.cursor()
cur.execute("SELECT GETDATE()")
print("GETDATE() SQL Server      :", cur.fetchone()[0])
cur.execute("SELECT MAX(CONVERT(date, DATE_FACTURE)) FROM dbo.VENTES_X3")
print("MAX(DATE_FACTURE) vue     :", cur.fetchone()[0])
conn.close()

# Ce qui est réellement chargé dans l'app (Postgres via la même app)
from app.core.database import SessionLocal
from app.models.entities import Sale, StockSnapshot
from sqlalchemy import func, select

db = SessionLocal()
print("MAX(Sale.date) en base app :", db.scalar(select(func.max(Sale.date))))
print("MAX(StockSnapshot.date)    :", db.scalar(select(func.max(StockSnapshot.date))))
print("COUNT(Sale) >= date 24/08  :", db.scalar(select(func.count(Sale.id)).where(Sale.date >= datetime.date(2026, 8, 24))))
db.close()
