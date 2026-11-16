"""Baseline adaptativo individual, com travas de segurança.

Regras (alinhadas ao documento do projeto):
  1. só calcula com >= MIN_SAMPLES amostras de qualidade "good";
  2. dias marcados como high_workload NÃO entram (não viram "novo normal");
  3. só atualiza com mudança SUSTENTADA (>= SUSTAIN_DAYS) e SIGNIFICATIVA (>= 1 DP);
  4. nunca atualiza enquanto há alerta aberto / hit recente (`block=True`);
  5. histórico é preservado (quem persiste grava nova linha, não sobrescreve).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

MIN_SAMPLES = 14
WINDOW_DAYS = 30
SUSTAIN_DAYS = 7
SIGNIFICANCE_SD = 1.0

# Piso do desvio-padrão por indicador: evita z-scores explosivos quando a
# pessoa é muito regular. Também define quais indicadores têm baseline.
METRIC_FLOOR = {
    "sleep_duration_h": 0.3,
    "sleep_efficiency": 0.02,
    "sleep_perceived_quality": 0.8,
    "fatigue": 0.4,
    "cog_rt_ms": 10.0,
    "spo2": 0.4,
    "diary_stress": 0.05,
    "diary_neg_emotion": 0.05,
}
BASELINE_METRICS = tuple(METRIC_FLOOR)


@dataclass(frozen=True)
class BaselineStat:
    mean: float
    std: float
    n: int
    window_start: date | None = None
    window_end: date | None = None

    def effective_std(self, metric: str) -> float:
        return max(self.std, METRIC_FLOOR.get(metric, 1e-6))


def zscore(value: float, stat: BaselineStat, metric: str) -> float:
    return (value - stat.mean) / stat.effective_std(metric)


def fit_baseline(values: dict[date, float], as_of: date, window_days: int = WINDOW_DAYS):
    start = as_of - timedelta(days=window_days - 1)
    pts = {d: v for d, v in values.items() if start <= d <= as_of}
    if not pts:
        return None
    arr = np.array(list(pts.values()), dtype=float)
    std = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
    return BaselineStat(float(arr.mean()), std, len(arr), min(pts), max(pts))


def compute_baseline_update(
    values: dict[date, float],
    prev: BaselineStat | None,
    as_of: date,
    *,
    metric: str,
    block: bool = False,
    min_samples: int = MIN_SAMPLES,
    sustain_days: int = SUSTAIN_DAYS,
) -> BaselineStat | None:
    """Devolve um NOVO baseline, ou None se o atual deve ser mantido.

    `values` já deve vir sem dias ruins e sem dias de alta carga.
    """
    cand = fit_baseline(values, as_of)
    if cand is None or cand.n < min_samples:
        return None
    if prev is None:
        return cand  # primeiro baseline
    if block:
        return None  # há alerta/hit recente: não normalizar a deterioração

    sd = prev.effective_std(metric)
    if abs(cand.mean - prev.mean) < SIGNIFICANCE_SD * sd:
        return None  # mudança não significativa

    recent = [v for d, v in values.items() if as_of - timedelta(days=sustain_days - 1) <= d <= as_of]
    if len(recent) < math.ceil(sustain_days * 0.7):
        return None  # sem dados suficientes para afirmar que é sustentada
    r_mean = float(np.mean(recent))
    if abs(r_mean - prev.mean) < SIGNIFICANCE_SD * sd:
        return None
    if (r_mean - prev.mean) * (cand.mean - prev.mean) <= 0:
        return None  # direções divergentes: não é mudança consistente
    return cand


def refresh_all(
    series: dict[str, dict[date, float]],
    workload_days: set[date],
    current: dict[str, BaselineStat],
    as_of: date,
    *,
    block: bool,
) -> dict[str, BaselineStat]:
    """Aplica `compute_baseline_update` a todos os indicadores. Devolve só os que mudaram."""
    updated: dict[str, BaselineStat] = {}
    for metric in BASELINE_METRICS:
        vals = {d: v for d, v in series.get(metric, {}).items() if d not in workload_days}
        new = compute_baseline_update(vals, current.get(metric), as_of, metric=metric, block=block)
        if new is not None:
            updated[metric] = new
    return updated
