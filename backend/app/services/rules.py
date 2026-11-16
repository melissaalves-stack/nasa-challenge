"""Motor de regras explicável. Puro (sem banco): recebe séries + baselines."""
from __future__ import annotations

import operator
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import yaml

from .baseline import BaselineStat

SEVERITY_RANK = {"info": 0, "watch": 1, "review_required": 2}
OPS = {
    "<": operator.lt, ">": operator.gt, "<=": operator.le,
    ">=": operator.ge, "==": operator.eq, "!=": operator.ne,
}
TREND_AGGS = {"mean_z", "days_z_below", "days_z_above", "mean", "slope"}
RULES_PATH = Path(__file__).with_name("rules.yaml")


@dataclass
class RuleHit:
    rule_id: str
    severity: str
    priority: str
    auto_action: bool
    explanation: str
    evidence: list = field(default_factory=list)
    window_start: date | None = None
    window_end: date | None = None


def load_rules(path: Path | str | None = None) -> list[dict]:
    rules = yaml.safe_load(Path(path or RULES_PATH).read_text(encoding="utf-8"))
    ids = set()
    for r in rules:
        for key in ("id", "severity", "window_days", "all", "explanation"):
            if key not in r:
                raise ValueError(f"rule {r.get('id', '?')}: missing '{key}'")
        if r["severity"] not in SEVERITY_RANK:
            raise ValueError(f"rule {r['id']}: invalid severity")
        if r["id"] in ids:
            raise ValueError(f"duplicate rule id {r['id']}")
        ids.add(r["id"])
        for c in r["all"]:
            if r.get("type", "trend") == "trend" and c.get("agg") not in TREND_AGGS:
                raise ValueError(f"rule {r['id']}: invalid agg {c.get('agg')}")
            if "op" in c and c["op"] not in OPS:
                raise ValueError(f"rule {r['id']}: invalid op {c['op']}")
    for r in rules:
        for dep in r.get("requires_rules", []):
            if dep not in ids:
                raise ValueError(f"rule {r['id']}: unknown dependency {dep}")
    return rules


def _window_points(metric_series: dict[date, float], as_of: date, window_days: int):
    start = as_of - timedelta(days=window_days - 1)
    return sorted((d, v) for d, v in metric_series.items() if start <= d <= as_of)


def _eval_trend_condition(cond, rule, series, baselines, as_of):
    metric, agg = cond["metric"], cond["agg"]
    pts = _window_points(series.get(metric, {}), as_of, rule["window_days"])
    need = cond.get("min_days", rule.get("min_days", 1))
    ev = {"metric": metric, "agg": agg, "n_days": len(pts)}
    if len(pts) < need:
        ev.update(observed=None, reason="insufficient_data")
        return False, ev
    vals = np.array([v for _, v in pts], dtype=float)

    if agg in ("mean_z", "days_z_below", "days_z_above"):
        stat: BaselineStat | None = baselines.get(metric)
        if stat is None:
            ev.update(observed=None, reason="no_baseline")
            return False, ev
        z = (vals - stat.mean) / stat.effective_std(metric)
        if agg == "mean_z":
            observed = float(z.mean())
            ok = OPS[cond["op"]](observed, cond["value"])
            ev.update(threshold=f'{cond["op"]} {cond["value"]}')
        elif agg == "days_z_below":
            observed = int((z < cond["z"]).sum())
            ok = observed >= cond["min_count"]
            ev.update(threshold=f'>= {cond["min_count"]} dias com z < {cond["z"]}')
        else:
            observed = int((z > cond["z"]).sum())
            ok = observed >= cond["min_count"]
            ev.update(threshold=f'>= {cond["min_count"]} dias com z > {cond["z"]}')
        ev["baseline"] = {"mean": round(stat.mean, 3), "std": round(stat.effective_std(metric), 3)}
    elif agg == "mean":
        observed = float(vals.mean())
        ok = OPS[cond["op"]](observed, cond["value"])
        ev.update(threshold=f'{cond["op"]} {cond["value"]}')
    else:  # slope
        if len(vals) < 3:
            ev.update(observed=None, reason="insufficient_data")
            return False, ev
        observed = float(np.polyfit([d.toordinal() for d, _ in pts], vals, 1)[0])
        ok = OPS[cond["op"]](observed, cond["value"])
        ev.update(threshold=f'{cond["op"]} {cond["value"]} por dia')
    ev["observed"] = round(observed, 3) if isinstance(observed, float) else observed
    return bool(ok), ev


def _eval_event_rule(rule, events, as_of):
    start = as_of - timedelta(days=rule["window_days"] - 1)
    for e in reversed(events):
        if not (start <= e["date"] <= as_of):
            continue
        evidence, all_ok = [], True
        for c in rule["all"]:
            val = e["features"].get(c["field"])
            if val is None:
                all_ok = False
                break
            ok = OPS[c["op"]](val, c["value"])
            evidence.append({"field": c["field"], "observed": val, "threshold": f'{c["op"]} {c["value"]}'})
            all_ok = all_ok and ok
        if all_ok:
            evidence.append({"event_ts": e["ts"].isoformat()})  # só metadado, nunca texto
            return True, evidence
    return False, []


def evaluate_rules(rules, series, baselines, events, as_of: date) -> list[RuleHit]:
    hits: dict[str, RuleHit] = {}
    # regras sem dependência primeiro
    for rule in sorted(rules, key=lambda r: 1 if r.get("requires_rules") else 0):
        if any(dep not in hits for dep in rule.get("requires_rules", [])):
            continue
        start = as_of - timedelta(days=rule["window_days"] - 1)
        if rule.get("type", "trend") == "event":
            ok, evidence = _eval_event_rule(rule, events, as_of)
        else:
            results = [_eval_trend_condition(c, rule, series, baselines, as_of) for c in rule["all"]]
            ok = all(r[0] for r in results)
            evidence = [r[1] for r in results]
        if ok:
            hits[rule["id"]] = RuleHit(
                rule_id=rule["id"],
                severity=rule["severity"],
                priority=rule.get("priority", "normal"),
                auto_action=bool(rule.get("auto_action", False)),
                explanation=rule["explanation"],
                evidence=evidence,
                window_start=start,
                window_end=as_of,
            )
    return list(hits.values())
