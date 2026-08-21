"""Tests du moteur de signaux (règles métier pures)."""
from datetime import date, timedelta

from app.models.entities import Product
from app.services.signals import ProductContext, build_signals


def _ctx(**overrides) -> ProductContext:
    defaults = {
        "stock": 1000.0,
        "reserved": 0.0,
        "in_transit": 0.0,
        "daily_avg_30": 25.0,
        "prev_avg_30": 25.0,
        "growth_pct": 0.0,
        "last_sale_date": date.today() - timedelta(days=1),
        "coverage_days": 40.0,
    }
    defaults.update(overrides)
    return ProductContext(product=Product(ref="P1", name="Produit 1", margin_rate=0.3, lead_time_days=15), **defaults)


def test_rupture_imminente():
    signals = build_signals([_ctx(stock=120.0, daily_avg_30=25.0, coverage_days=4.8)], date.today())
    rupture = [s for s in signals if s.signal_type == "rupture"]
    assert len(rupture) == 1
    assert rupture[0].priority == "P0"  # < 7 jours → critique


def test_rupture_p1():
    signals = build_signals([_ctx(stock=300.0, daily_avg_30=25.0, coverage_days=12.0)], date.today())
    rupture = [s for s in signals if s.signal_type == "rupture"]
    assert rupture and rupture[0].priority == "P1"


def test_surstock():
    signals = build_signals([_ctx(stock=5000.0, daily_avg_30=25.0, coverage_days=200.0)], date.today())
    assert any(s.signal_type == "surstock" for s in signals)


def test_dormant():
    signals = build_signals(
        [_ctx(stock=500.0, daily_avg_30=0.0, last_sale_date=date.today() - timedelta(days=80), coverage_days=None)],
        date.today(),
    )
    assert any(s.signal_type == "dormant" for s in signals)


def test_acceleration():
    signals = build_signals([_ctx(growth_pct=0.6, daily_avg_30=40.0, prev_avg_30=25.0)], date.today())
    assert any(s.signal_type == "acceleration" for s in signals)


def test_no_signal_on_healthy_product():
    signals = build_signals([_ctx()], date.today())
    assert len(signals) == 0
