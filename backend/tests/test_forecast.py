"""Tests du moteur de prévision (Holt-Winters + repli)."""
from datetime import date, timedelta

import numpy as np

from app.services.forecast import forecast_series, forecast_totals


def _series(days: int = 180, base: float = 50.0, rng: np.random.Generator | None = None):
    rng = rng or np.random.default_rng(7)
    today = date.today()
    dates = [today - timedelta(days=days - 1 - i) for i in range(days)]
    values = [max(0.0, base * (1 + rng.normal(0, 0.15))) for _ in range(days)]
    return dates, values


def test_forecast_returns_horizon_points():
    dates, values = _series()
    result = forecast_series(dates, values, 30)
    assert result is not None
    assert len(result) == 30
    for r in result:
        assert 0 <= r.low <= r.mid <= r.high


def test_forecast_increasing_series_positive():
    today = date.today()
    dates = [today - timedelta(days=120 - i) for i in range(120)]
    values = [10 + i * 0.5 for i in range(120)]  # tendance haussière nette
    result = forecast_series(dates, values, 30)
    assert result is not None
    assert all(r.mid > 0 for r in result)


def test_forecast_empty_returns_none():
    assert forecast_series([], [], 30) is None


def test_forecast_too_short_returns_none():
    dates, values = _series(days=5)
    assert forecast_series(dates, values, 30) is None


def test_forecast_totals_aggregates():
    dates, values = _series()
    result = forecast_series(dates, values, 30)
    totals = forecast_totals(result)
    assert totals is not None
    assert totals["low"] <= totals["mid"] <= totals["high"]
