"""Transforma linhas brutas (ORM ou qualquer objeto com os mesmos atributos)
em séries diárias por indicador. Função pura: fácil de testar sem banco."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

import numpy as np

# Indicadores só de contexto (sem baseline nem regra): ex. proxy sintético.
CONTEXT_METRICS = ("muscle_density", "sleep_latency_min", "sleep_awakenings")


def _put(s, metric, d, value):
    if value is not None:
        s[metric][d] = float(value)


def series_from_rows(sleep_rows, vital_rows, diary_rows, as_of: date, lookback_days: int = 60):
    """Retorna (series, workload_days, events).

    series:        {metric: {date: value}}  (apenas dados de qualidade "good")
    workload_days: dias marcados high_workload (excluídos do baseline)
    events:        features do diário por registro (para regras de evento)
    """
    start = as_of - timedelta(days=lookback_days)
    s: dict[str, dict[date, float]] = defaultdict(dict)
    workload: set[date] = set()

    for r in sleep_rows:
        d = r.night
        if d < start or d > as_of:
            continue
        if getattr(r, "high_workload", False):
            workload.add(d)
        if r.data_quality != "good":
            continue
        _put(s, "sleep_duration_h", d, r.duration_h)
        _put(s, "sleep_efficiency", d, r.efficiency)
        _put(s, "sleep_perceived_quality", d, r.perceived_quality)
        _put(s, "cog_rt_ms", d, getattr(r, "cognitive_rt_ms", None))
        _put(s, "muscle_density", d, r.muscle_density)
        _put(s, "sleep_latency_min", d, r.latency_min)
        _put(s, "sleep_awakenings", d, r.awakenings)

    by_day_fat, by_day_spo2 = defaultdict(list), defaultdict(list)
    for v in vital_rows:
        d = v.ts.date()
        if d < start or d > as_of or v.data_quality != "good":
            continue
        if v.fatigue_score is not None:
            by_day_fat[d].append(v.fatigue_score)
        if v.spo2 is not None:
            by_day_spo2[d].append(v.spo2)
    for d, xs in by_day_fat.items():
        s["fatigue"][d] = float(np.mean(xs))
    for d, xs in by_day_spo2.items():
        s["spo2"][d] = float(np.mean(xs))

    stress, neg = defaultdict(list), defaultdict(list)
    events = []
    for r in diary_rows:
        if not getattr(r, "consent", True):
            continue
        d = r.ts.date()
        if d < start or d > as_of:
            continue
        f = r.features
        stress[d].append(f["stress_score"])
        neg[d].append(f["neg_emotion_score"])
        events.append({"date": d, "ts": r.ts, "features": f})
    for d, xs in stress.items():
        s["diary_stress"][d] = float(np.mean(xs))
    for d, xs in neg.items():
        s["diary_neg_emotion"][d] = float(np.mean(xs))

    events.sort(key=lambda e: e["ts"])
    return dict(s), workload, events
