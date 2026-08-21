"""Jeu de données de démonstration — 8 mois de ventes + stocks réalistes.

Permet de faire tourner l'agent immédiatement (sans SAGE X3) et de tester
toutes les règles : rupture, surstock, dormant, accélération, opportunité, réappro.
"""
import logging
from datetime import date, timedelta

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import IngestionLog, Product, Sale, StockSnapshot

logger = logging.getLogger(__name__)

RNG = np.random.default_rng(42)

# ref, name, category, brand, unit_price, margin_rate, supplier, lead_time, min_qty, base_daily, profile
PRODUCTS = [
    # --- Ciment ---
    ("CIM-001", "Ciment CPJ 42.5 50kg", "Ciment", "Dangote", 5200, 0.22, "Dangote Cement", 21, 200, 85, "rupture"),
    ("CIM-002", "Ciment CPJ 32.5 50kg", "Ciment", "CIMENCAM", 4700, 0.20, "CIMENCAM", 21, 200, 70, "rupture"),
    ("CIM-003", "Ciment blanc 25kg", "Ciment", "Dangote", 6800, 0.28, "Dangote Cement", 30, 100, 12, "normal"),
    # --- Fer & Acier ---
    ("FER-001", "Fer à béton Ø8 (barre 12m)", "Fer & Acier", "ALUCAM", 2900, 0.30, "ALUCAM", 15, 50, 60, "rupture"),
    ("FER-002", "Fer à béton Ø10 (barre 12m)", "Fer & Acier", "ALUCAM", 3600, 0.30, "ALUCAM", 15, 50, 55, "normal"),
    ("FER-003", "Fer à béton Ø12 (barre 12m)", "Fer & Acier", "ALUCAM", 4300, 0.32, "ALUCAM", 15, 50, 48, "normal"),
    ("FER-004", "Tôle ondulée 3m", "Fer & Acier", "ALUCAM", 8500, 0.25, "ALUCAM", 20, 30, 18, "normal"),
    ("SRT-FER-01", "Tôle bac acier 2m (lot)", "Fer & Acier", "ALUCAM", 12000, 0.24, "ALUCAM", 25, 20, 6, "surstock"),
    # --- Carrelage ---
    ("CAR-001", "Carrelage 40x40 (m²)", "Carrelage", "Ceramica", 4500, 0.35, "Ceramica", 30, 100, 40, "normal"),
    ("CAR-002", "Carrelage 60x60 (m²)", "Carrelage", "Ceramica", 6800, 0.35, "Ceramica", 30, 100, 32, "normal"),
    ("ACC-CAR-01", "Carrelage imitation bois 60x60", "Carrelage", "Granito", 9200, 0.38, "Granito", 35, 50, 22, "acceleration"),
    ("CAR-003", "Faïence murale 25x40", "Carrelage", "Ceramica", 3600, 0.32, "Ceramica", 30, 80, 26, "normal"),
    # --- Peinture ---
    ("PNT-001", "Peinture acrylique blanche 10L", "Peinture", "La PAMOL", 9800, 0.30, "La PAMOL", 14, 40, 30, "normal"),
    ("PNT-002", "Peinture glycéro rouge 5L", "Peinture", "Seynab", 7800, 0.32, "Seynab", 14, 40, 14, "normal"),
    ("DRM-PNT-01", "Peinture glycéro bleu 5L", "Peinture", "Seynab", 7800, 0.30, "Seynab", 14, 40, 15, "dormant"),
    ("PNT-003", "Peinture antirouille 1L", "Peinture", "La PAMOL", 4200, 0.28, "La PAMOL", 14, 50, 20, "normal"),
    ("PNT-004", "Enduit de lissage 25kg", "Peinture", "La PAMOL", 5200, 0.26, "La PAMOL", 14, 60, 34, "normal"),
    # --- Plomberie ---
    ("PLM-001", "Tuyau PVC Ø50 (4m)", "Plomberie", "Polyform", 2800, 0.34, "Polyform", 10, 50, 25, "normal"),
    ("PLM-002", "Tuyau PVC Ø100 (4m)", "Plomberie", "Polyform", 5200, 0.34, "Polyform", 10, 50, 16, "normal"),
    ("PLM-003", "Robinet équerre laiton", "Plomberie", "Ets Moderne", 3500, 0.38, "Ets Moderne", 12, 40, 22, "normal"),
    ("PLM-004", "Ballon d'eau 1000L", "Plomberie", "Tricel", 85000, 0.30, "Tricel", 40, 5, 3, "normal"),
    # --- Électricité ---
    ("ELE-001", "Câble électrique 2,5mm² (100m)", "Électricité", "Sotici", 45000, 0.25, "Sotici", 20, 10, 9, "normal"),
    ("ELE-002", "Câble électrique 6mm² (100m)", "Électricité", "Sotici", 98000, 0.25, "Sotici", 20, 10, 5, "normal"),
    ("ELE-003", "Interrupteur simple", "Électricité", "Legrand", 1800, 0.40, "Legrand", 15, 60, 35, "normal"),
    ("ELE-004", "Prise de courant 2P+T", "Électricité", "Legrand", 2200, 0.40, "Legrand", 15, 60, 30, "normal"),
    ("ELE-005", "Disjoncteur 20A", "Électricité", "Schneider", 5200, 0.36, "Schneider", 15, 40, 12, "normal"),
    # --- Quincaillerie ---
    ("QNC-001", "Sachet vis à bois 5cm (100)", "Quincaillerie", "Simpson", 1500, 0.42, "Simpson", 10, 100, 40, "normal"),
    ("QNC-002", "Cheville 8mm (paquet 100)", "Quincaillerie", "Simpson", 1200, 0.42, "Simpson", 10, 100, 45, "normal"),
    ("QNC-003", "Cadenas 50mm", "Quincaillerie", "Serrure Pro", 4800, 0.38, "Serrure Pro", 12, 30, 18, "normal"),
    ("QNC-004", "Serrure 3 points", "Quincaillerie", "Serrure Pro", 22000, 0.35, "Serrure Pro", 15, 10, 4, "normal"),
    ("QNC-005", "Marteau 500g", "Quincaillerie", "Stanley", 3500, 0.33, "Stanley", 12, 30, 12, "normal"),
    # --- Bois & Panneaux ---
    ("BIS-001", "Planche sapin 4m", "Bois", "Scierie", 3200, 0.25, "Scierie du Sud", 7, 40, 28, "normal"),
    ("BIS-002", "Contreplaqué 10mm (1,22x2,44)", "Bois", "Scierie", 15500, 0.26, "Scierie du Sud", 10, 20, 14, "normal"),
    # --- Sanitaire ---
    ("SAN-001", "WC complet à poser", "Sanitaire", "Ideal Standard", 65000, 0.30, "Ideal Standard", 25, 5, 2, "normal"),
    ("SAN-002", "Lavabo 60cm", "Sanitaire", "Ideal Standard", 28000, 0.30, "Ideal Standard", 25, 5, 3, "normal"),
    ("SAN-003", "Mélangeur robinet", "Sanitaire", "Ideal Standard", 12000, 0.32, "Ideal Standard", 20, 10, 6, "normal"),
    # --- Outillage ---
    ("OUT-001", "Brouette 100L", "Outillage", "Profix", 28000, 0.28, "Profix", 15, 5, 2, "normal"),
    ("OUT-002", "Pelle ronde", "Outillage", "Profix", 4500, 0.30, "Profix", 12, 20, 8, "normal"),
    ("OUT-003", "Seau maçon 15L", "Outillage", "Profix", 1500, 0.32, "Profix", 10, 40, 16, "normal"),
]


def _weekly_factor(d: date) -> float:
    return 0.55 if d.weekday() >= 5 else 1.0 + 0.08 * (4 - d.weekday())


def _generate_sales(profile: str, base: float, days: int, today: date, trend: float = 0.0):
    """Série quotidienne déterministe. Retourne [(date, qty), ...]."""
    out = []
    for i in range(days):
        d = today - timedelta(days=days - 1 - i)
        if profile == "dormant" and d >= today - timedelta(days=60):
            continue  # plus aucune vente sur les 60 derniers jours
        weekly = _weekly_factor(d)
        drift = 1.0 + trend * (i / max(days, 1))
        noise = 1.0 + RNG.normal(0, 0.18)
        promo = 1.8 if RNG.random() < 0.02 else 1.0
        qty = max(0, round(base * weekly * drift * noise * promo))
        if qty > 0:
            out.append((d, qty))
    return out


def seed_demo_data(db: Session, force: bool = False) -> tuple[str, str]:
    """Génère le jeu de démo si la base est vide. Retourne (source, message)."""
    existing = db.scalar(select(func.count(Product.id))) or 0
    has_sales = db.scalar(select(func.count(Sale.id))) or 0
    if existing > 0 and has_sales > 0 and not force:
        return "seed", "Données de démonstration déjà en place (aucune régénération)."

    log = IngestionLog(source="seed", status="running")
    db.add(log)

    try:
        # Suppression du jeu précédent si régénération
        if force:
            db.query(Sale).delete()
            db.query(StockSnapshot).delete()
            db.query(Product).delete()

        today = date.today()
        days = 240  # ~8 mois

        coverage_by_profile = {
            "rupture": 5,        # → P0 rupture imminente
            "surstock": 150,     # → surstock massif
            "dormant": 100,      # stock présent, aucune vente récente
            "acceleration": 35,  # demande en forte hausse
            "normal": 40,
        }
        trend_by_profile = {
            "rupture": 0.35,
            "surstock": 0.0,
            "dormant": 0.0,
            "acceleration": 0.9,
            "normal": 0.10,
        }

        for ref, name, cat, brand, price, margin, supplier, lead, min_qty, base, profile in PRODUCTS:
            p = Product(
                ref=ref, name=name, category=cat, brand=brand,
                unit_price=price, margin_rate=margin, supplier=supplier,
                lead_time_days=lead, min_order_qty=min_qty,
            )
            db.add(p)
            db.flush()

            sales = _generate_sales(profile, base, days, today, trend=trend_by_profile[profile])
            for d, qty in sales:
                db.add(Sale(product_id=p.id, date=d, quantity=qty, revenue=round(qty * price, 2)))

            # Stock : couverture cible selon le profil (en jours)
            if sales:
                recent = [q for d, q in sales if d >= today - timedelta(days=30)]
                daily_avg = sum(recent) / len(recent) if recent else base
            else:
                daily_avg = base
            coverage = coverage_by_profile[profile]
            stock_qty = max(round(daily_avg * coverage), 1)
            db.add(StockSnapshot(
                product_id=p.id, date=today, quantity=stock_qty,
                reserved=0.0, in_transit=0.0,
            ))

        db.commit()
        log.status = "success"
        log.finished_at = None
        log.rows_loaded = len(PRODUCTS)
        log.message = f"{len(PRODUCTS)} produits, {days} jours de ventes générés"
        db.commit()

        return "seed", f"Jeu de démonstration généré : {log.message}"
    except Exception as exc:
        db.rollback()
        log.status = "error"
        log.message = str(exc)[:500]
        db.commit()
        raise
