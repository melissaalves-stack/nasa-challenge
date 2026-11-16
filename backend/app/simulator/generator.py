"""Gerador sintético determinístico (seed fixa => demo reproduzível).

Gera FEATURES de diário (nunca texto), alinhado ao princípio de privacy-preserving.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

import numpy as np

from .scenarios import SCENARIOS, DayProfile

# (média, desvio) do astronauta "saudável"
HEALTHY = {
    "duration_h": (7.2, 0.4), "efficiency": (0.90, 0.03), "latency": (18, 5),
    "perceived": (7, 0.8), "fatigue": (3.0, 0.5), "cog": (300, 15),
    "stress": (0.25, 0.05), "muscle": (42.0, 0.3),
}
READING_HOURS = (0, 6, 12, 18)


@dataclass
class DayRecord:
    date: date
    phase: str              # "baseline" | "scenario"
    index: int              # dia dentro da fase
    sleep: dict
    vitals: list
    diary: dict


def _clip(x, lo=0.0, hi=1.0):
    return float(min(hi, max(lo, x)))


def _diary_features(rng, prof: DayProfile) -> dict:
    stress = _clip(rng.normal(*HEALTHY["stress"])) if prof.stress is None else _clip(prof.stress + rng.normal(0, 0.03))
    delta = stress - 0.25
    flag = prof.suicidal_flag if prof.suicidal_flag is not None else abs(float(rng.normal(0.02, 0.01)))
    return {
        "neg_emotion_score": round(_clip(0.2 + 0.6 * delta + rng.normal(0, 0.04)), 3),
        "pos_emotion_score": round(_clip(0.55 - 0.5 * delta + rng.normal(0, 0.04)), 3),
        "stress_score": round(stress, 3),
        "loneliness_score": round(_clip(0.2 + 0.4 * delta + rng.normal(0, 0.04)), 3),
        "anhedonia_score": round(_clip(0.15 + 0.4 * delta + rng.normal(0, 0.04)), 3),
        "suicidal_ideation_flag": round(_clip(flag), 3),
        "suicidal_ideation_confidence": prof.suicidal_confidence,
        "text_length": int(rng.integers(150, 600)),
        "complexity": round(_clip(rng.normal(0.58, 0.05)), 3),
        "topic_tags": list(prof.topics),
    }


def _day(rng, d: date, prof: DayProfile, seed: int) -> tuple[dict, list, dict]:
    dur = max(2.0, rng.normal(*HEALTHY["duration_h"]) + prof.duration_delta)
    eff = _clip(rng.normal(*HEALTHY["efficiency"]) + prof.efficiency_delta, 0.3, 0.99)
    sleep = {
        "night": d,
        "duration_h": round(dur, 2),
        "latency_min": round(max(1.0, rng.normal(*HEALTHY["latency"]) - prof.duration_delta * 8), 1),
        "awakenings": int(max(0, round(1.5 - prof.duration_delta * 1.2 + rng.normal(0, 0.7)))),
        "efficiency": round(eff, 3),
        "perceived_quality": int(min(10, max(1, round(rng.normal(*HEALTHY["perceived"]) + prof.duration_delta * 1.5)))),
        "muscle_density": round(rng.normal(*HEALTHY["muscle"]), 2),   # proxy sintético
        "cognitive_rt_ms": round(rng.normal(*HEALTHY["cog"]) + prof.cog_delta, 1),
        "high_workload": prof.high_workload,
        "data_quality": "good",
    }
    day_fatigue = rng.normal(*HEALTHY["fatigue"]) + prof.fatigue_delta
    vitals = []
    for h in READING_HOURS:
        vitals.append({
            "ts": datetime.combine(d, time(h), tzinfo=timezone.utc),
            "systolic": int(rng.normal(118, 5)), "diastolic": int(rng.normal(76, 4)),
            "spo2": round(float(rng.normal(97.5, 0.6)), 1),
            "fatigue_score": round(_clip(day_fatigue + rng.normal(0, 0.3), 0, 10), 2),
        })
    features = _diary_features(rng, prof)
    diary = {
        "ts": datetime.combine(d, time(21), tzinfo=timezone.utc),
        "features": features,
        # hash determinístico só para a demo; no app real: HMAC do texto, no dispositivo
        "text_hash": hashlib.sha256(f"sim|{seed}|{d.isoformat()}".encode()).hexdigest(),
        "local_model_version": "sim-local-v0",
    }
    return sleep, vitals, diary


def generate_scenario(name: str, seed: int = 42, start: date | None = None,
                      baseline_days: int = 20) -> list[DayRecord]:
    if name not in SCENARIOS:
        raise KeyError(f"unknown scenario '{name}'. Options: {sorted(SCENARIOS)}")
    sc = SCENARIOS[name]
    total = baseline_days + sc.days
    start = start or (date.today() - timedelta(days=total - 1))
    rng = np.random.default_rng(seed)
    records = []
    for i in range(total):
        in_base = i < baseline_days
        prof = DayProfile() if in_base else sc.profile(i - baseline_days)
        sleep, vitals, diary = _day(rng, start + timedelta(days=i), prof, seed)
        records.append(DayRecord(start + timedelta(days=i), "baseline" if in_base else "scenario",
                                 i if in_base else i - baseline_days, sleep, vitals, diary))
    return records
