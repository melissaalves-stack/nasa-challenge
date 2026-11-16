"""Cenários sintéticos. Cada um é uma função k -> DayProfile (k = dia do cenário,
depois dos `baseline_days` dias saudáveis)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class DayProfile:
    duration_delta: float = 0.0
    efficiency_delta: float = 0.0
    fatigue_delta: float = 0.0
    cog_delta: float = 0.0
    stress: float | None = None          # None = valor saudável
    high_workload: bool = False
    suicidal_flag: float | None = None   # None = ~0.02 (ruído)
    suicidal_confidence: str = "low"
    topics: list = field(default_factory=lambda: ["trabalho"])


@dataclass
class Scenario:
    name: str
    description: str
    days: int
    profile: Callable[[int], DayProfile]


def _healthy(k):
    return DayProfile()


def _isolated_bad_night(k):
    if k == 2:   # uma noite péssima
        return DayProfile(duration_delta=-2.7, efficiency_delta=-0.2, topics=["sono"])
    if k == 3:   # fadiga no dia seguinte, sem persistência
        return DayProfile(fatigue_delta=1.0)
    return DayProfile()


def _deteriorating(k):
    n = k + 1
    return DayProfile(
        duration_delta=-1.8 * min(1.0, (k + 2) / 4),
        efficiency_delta=-0.12 * min(1.0, (k + 2) / 4),
        fatigue_delta=0.4 * n,
        cog_delta=8.0 * n,
        stress=min(0.95, 0.30 + 0.08 * n),
        high_workload=True,
        topics=["sono", "trabalho"],
    )


def _recovery(k):
    if k < 7:
        return _deteriorating(k)
    r = k - 7  # 0..9
    f = max(0.0, 1.0 - (r + 1) / 4)  # volta ao normal em ~4 dias
    base = _deteriorating(6)
    return DayProfile(
        duration_delta=base.duration_delta * f,
        efficiency_delta=base.efficiency_delta * f,
        fatigue_delta=base.fatigue_delta * f,
        cog_delta=base.cog_delta * f,
        stress=None if f == 0 else 0.25 + (0.8 - 0.25) * f,
        high_workload=False,
        topics=["sono"] if f else ["trabalho"],
    )


def _suicidal_marker(k):
    p = DayProfile(
        duration_delta=-0.6, fatigue_delta=0.6, stress=min(0.9, 0.45 + 0.08 * k),
        topics=["isolamento", "sono"],
    )
    if k == 4:   # marcador sintético: sinaliza para REVISÃO HUMANA, não diagnostica
        p.suicidal_flag, p.suicidal_confidence = 0.78, "medium"
        p.stress = 0.85
    return p


SCENARIOS = {
    "healthy_baseline": Scenario("healthy_baseline", "Baseline saudável (normalidade).", 5, _healthy),
    "isolated_bad_night": Scenario("isolated_bad_night", "Uma noite ruim isolada: NÃO deve alertar.", 7, _isolated_bad_night),
    "integrated_deterioration": Scenario(
        "integrated_deterioration", "3+ noites ruins + carga + diário estressado: watch -> review_required.", 10, _deteriorating),
    "suicidal_marker": Scenario(
        "suicidal_marker", "Diário com marcador sintético de ideação: fila prioritária, sem ação automática.", 7, _suicidal_marker),
    "recovery": Scenario("recovery", "Deterioração seguida de recuperação: alerta fecha, baseline intacto.", 17, _recovery),
}
