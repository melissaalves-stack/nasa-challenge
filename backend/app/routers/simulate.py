"""Modo demo: injeta cenários sintéticos e roda o pipeline dia a dia."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import models
from ..auth import require_roles
from ..db import get_db
from ..schemas import SimulateIn
from ..services.pipeline import run_pipeline
from ..simulator.generator import DayRecord, generate_scenario
from ..simulator.scenarios import SCENARIOS

router = APIRouter(prefix="/admin", tags=["admin / demo"])
admin_only = require_roles("admin")

_USER_TABLES = (models.PlanFeedback, models.ActionPlan, models.Alert, models.Baseline,
                models.DiaryFeature, models.SleepEntry, models.Vital)


def reset_user_data(db: Session, user_id: str) -> None:
    for table in _USER_TABLES:  # ordem respeita as chaves estrangeiras
        db.execute(delete(table).where(table.user_id == user_id))
    db.commit()


def _store_day(db: Session, user_id: str, rec: DayRecord) -> None:
    db.execute(delete(models.SleepEntry).where(models.SleepEntry.user_id == user_id,
                                               models.SleepEntry.night == rec.date))
    db.add(models.SleepEntry(user_id=user_id, **rec.sleep))
    for v in rec.vitals:
        db.add(models.Vital(user_id=user_id, **v))
    d = rec.diary
    exists = db.scalar(select(models.DiaryFeature.id).where(
        models.DiaryFeature.user_id == user_id, models.DiaryFeature.text_hash == d["text_hash"]))
    if not exists:
        db.add(models.DiaryFeature(user_id=user_id, ts=d["ts"], text_hash=d["text_hash"],
                                   features=d["features"], local_model_version=d["local_model_version"],
                                   consent=True))
    db.commit()


@router.get("/scenarios")
def list_scenarios(_: models.User = Depends(admin_only)):
    return [{"name": s.name, "description": s.description, "days_after_baseline": s.days}
            for s in SCENARIOS.values()]


@router.post("/simulate")
def simulate(body: SimulateIn, _: models.User = Depends(admin_only), db: Session = Depends(get_db)):
    user = db.get(models.User, body.user_id)
    if not user or user.role != "astronaut":
        raise HTTPException(404, "Astronaut not found")
    if body.scenario not in SCENARIOS:
        raise HTTPException(422, f"Unknown scenario. Options: {sorted(SCENARIOS)}")
    if body.reset:
        reset_user_data(db, user.id)

    records = generate_scenario(body.scenario, seed=body.seed, start=body.start_date)
    events, seen = [], set()
    for rec in records:
        _store_day(db, user.id, rec)
        for a in run_pipeline(db, user.id, rec.date):
            if (a.id, a.severity) not in seen:
                seen.add((a.id, a.severity))
                events.append({"date": rec.date.isoformat(), "phase": rec.phase, "day_index": rec.index,
                               "alert_id": a.id, "severity": a.severity, "priority": a.priority,
                               "rule_ids": a.rule_ids})
    alerts = db.scalars(select(models.Alert).where(models.Alert.user_id == user.id)
                        .order_by(models.Alert.id)).all()
    return {"scenario": body.scenario, "seed": body.seed, "days_generated": len(records),
            "period": [records[0].date.isoformat(), records[-1].date.isoformat()],
            "alert_events": events,
            "alerts": [{"id": a.id, "severity": a.severity, "priority": a.priority, "status": a.status,
                        "rule_ids": a.rule_ids, "summary": a.explanation.get("summary", [])}
                       for a in alerts],
            "note": "Dados 100% sintéticos. O diário simulado contém apenas features, nunca texto."}


@router.post("/reset/{user_id}")
def reset(user_id: str, _: models.User = Depends(admin_only), db: Session = Depends(get_db)):
    reset_user_data(db, user_id)
    return {"reset": True}
