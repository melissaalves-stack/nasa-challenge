from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from . import pipeline
from .series import CONTEXT_METRICS, series_from_rows


def build_timeline(db: Session, user_id: str, as_of: date, days: int = 45) -> dict:
    sleep, vitals, diary = pipeline.fetch_rows(db, user_id, as_of, lookback=days)
    series, workload, _ = series_from_rows(sleep, vitals, diary, as_of, lookback_days=days)
    baselines = pipeline.load_baselines(db, user_id)

    metrics = {}
    for m, pts in sorted(series.items()):
        b = baselines.get(m)
        band = None
        if b:
            sd = b.effective_std(m)
            band = {"mean": round(b.mean, 3), "std": round(sd, 3),
                    "lower": round(b.mean - sd, 3), "upper": round(b.mean + sd, 3), "n": b.n}
        metrics[m] = {
            "exploratory": m.startswith("diary_"),     # seção "Exploratório" no dashboard
            "context_only": m in CONTEXT_METRICS,      # ex.: densidade muscular (proxy)
            "baseline": band,
            "points": [{"date": d.isoformat(), "value": round(v, 3)} for d, v in sorted(pts.items())],
        }
    alerts = db.scalars(select(models.Alert).where(models.Alert.user_id == user_id)
                        .order_by(models.Alert.id.desc()).limit(50)).all()
    return {
        "user_id": user_id,
        "range": [(as_of - timedelta(days=days)).isoformat(), as_of.isoformat()],
        "metrics": metrics,
        "high_workload_days": sorted(d.isoformat() for d in workload),
        "alerts": [{"id": a.id, "severity": a.severity, "priority": a.priority, "status": a.status,
                    "rule_ids": a.rule_ids, "created_at": a.created_at.isoformat()} for a in alerts],
    }
