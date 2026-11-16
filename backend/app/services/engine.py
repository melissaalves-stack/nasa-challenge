"""Orquestração pura: linhas -> séries -> baselines -> regras. Sem banco."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from . import baseline as bl
from . import rules as rl
from .series import series_from_rows


@dataclass
class AnalysisResult:
    series: dict
    workload_days: set
    events: list
    baselines: dict          # baselines vigentes (já com atualizações)
    updated_baselines: dict  # só os que mudaram nesta análise
    hits: list


def analyze(sleep_rows, vital_rows, diary_rows, current_baselines, as_of: date,
            *, block_baseline_updates: bool, rules: list[dict]) -> AnalysisResult:
    series, workload, events = series_from_rows(sleep_rows, vital_rows, diary_rows, as_of)
    updated = bl.refresh_all(series, workload, current_baselines, as_of, block=block_baseline_updates)
    baselines = {**current_baselines, **updated}
    hits = rl.evaluate_rules(rules, series, baselines, events, as_of)
    return AnalysisResult(series, workload, events, baselines, updated, hits)
