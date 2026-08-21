"""Moteur de prévision — Holt-Winters (ETS) + repli moyenne mobile.

Choisi pour la production :
- rapide au démarrage (contrairement à Prophet) ;
- robuste sur 8 mois de données quotidiennes avec saisonnalité hebdomadaire ;
- fournit un intervalle de confiance (low/high) — jamais de fausse précision.
"""
import logging
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SEASONAL_PERIODS = 7  # saisonnalité hebdomadaire


@dataclass
class ForecastResult:
    horizon_date: date
    low: float
    mid: float
    high: float
    model: str


def _moving_average(values: np.ndarray, horizon: int) -> ForecastResult:
    """Repli simple quand l'historique est trop court ou creux."""
    if len(values) == 0:
        return None
    window = max(1, min(30, len(values)))
    mean = float(np.mean(values[-window:]))
    sigma = float(np.std(values[-window:])) if len(values) >= 2 else max(mean * 0.2, 0.0)
    sigma = max(sigma, mean * 0.1)
    return ForecastResult(
        horizon_date=date.today() + timedelta(days=horizon),
        low=max(0, mean - 1.28 * sigma),
        mid=max(0, mean),
        high=mean + 1.28 * sigma,
        model="ma",
    )


def forecast_series(
    dates: list[date], values: list[float], horizon_days: int
) -> list[ForecastResult] | None:
    """Prévoit `horizon_days` jours à partir d'une série quotidienne.

    Retourne une liste de ForecastResult (un par jour d'horizon),
    ou None si la série est vide.
    """
    if not dates or not values or len(dates) != len(values):
        return None
    if len(values) < settings.MIN_HISTORY_DAYS:
        return None

    series = pd.Series(np.asarray(values, dtype=float), index=pd.to_datetime(dates))
    series = series[~series.index.duplicated(keep="last")].sort_index()
    if series.sum() <= 0 or len(series) < settings.MIN_HISTORY_DAYS:
        return None

    horizon = max(1, horizon_days)
    model_name = "ets"

    try:
        use_seasonal = len(series) >= 2 * SEASONAL_PERIODS and series.nunique() > 1
        if use_seasonal:
            model = ExponentialSmoothing(
                series,
                trend="add",
                seasonal="add",
                seasonal_periods=SEASONAL_PERIODS,
                damped_trend=True,
            )
        else:
            model = ExponentialSmoothing(series, trend="add", damped_trend=True)
        fitted = model.fit(optimized=True)

        fc = np.asarray(fitted.forecast(horizon))
        resid = np.asarray(fitted.resid)
        sigma = float(np.std(resid)) if len(resid) > 1 else max(float(fc.mean()) * 0.15, 0.0)
        sigma = max(sigma, float(fc.mean()) * 0.05)

        last_date = pd.Timestamp(series.index[-1]).date()
        results = []
        for i, m in enumerate(fc):
            d = last_date + timedelta(days=i + 1)
            mid = max(0.0, float(m))
            low = max(0.0, mid - 1.28 * sigma)
            high = mid + 1.28 * sigma
            results.append(ForecastResult(horizon_date=d, low=low, mid=mid, high=high, model=model_name))
        return results
    except Exception as exc:  # noqa: BLE001 — repli sûr
        logger.warning("ETS échoué, repli moyenne mobile: %s", exc)
        mean_fc = _moving_average(series.values, horizon)
        return [mean_fc] * horizon if mean_fc else None


def forecast_totals(results: list[ForecastResult] | None) -> dict[str, float] | None:
    """Agrège un horizon en totaux low/mid/high (ex: 30 jours)."""
    if not results:
        return None
    return {
        "low": round(sum(r.low for r in results), 1),
        "mid": round(sum(r.mid for r in results), 1),
        "high": round(sum(r.high for r in results), 1),
    }
