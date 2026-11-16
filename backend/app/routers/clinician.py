from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models
from ..audit import audit
from ..auth import assigned_astronaut_ids, ensure_can_access, require_roles
from ..db import get_db
from ..responses import with_disclaimer
from ..schemas import ReviewIn
from ..services.rules import SEVERITY_RANK
from ..services.timeline import build_timeline

router = APIRouter(prefix="/clinician", tags=["clinician"])
clin = require_roles("clinician", "admin")


def _alert_dict(a: models.Alert, name: str | None = None, full: bool = False) -> dict:
    d = {"id": a.id, "user_id": a.user_id, "user_name": name, "severity": a.severity,
         "priority": a.priority, "status": a.status, "rule_ids": a.rule_ids,
         "auto_action": a.auto_action, "created_at": a.created_at.isoformat(),
         "last_hit_date": a.last_hit_date.isoformat() if a.last_hit_date else None,
         "summary": (a.explanation or {}).get("summary", []),
         "conditions_cleared": (a.explanation or {}).get("conditions_cleared", False)}
    if full:
        d.update(explanation=a.explanation, review_decision=a.review_decision,
                 review_note=a.review_note,
                 reviewed_at=a.reviewed_at.isoformat() if a.reviewed_at else None)
    return d


def _alert_or_404(db: Session, actor: models.User, alert_id: int) -> models.Alert:
    a = db.get(models.Alert, alert_id)
    if not a or a.user_id not in assigned_astronaut_ids(db, actor):
        raise HTTPException(404, "Alert not found")
    return a


@router.get("/overview")
def overview(actor: models.User = Depends(clin), db: Session = Depends(get_db)):
    ids = assigned_astronaut_ids(db, actor)
    users = db.scalars(select(models.User).where(models.User.id.in_(ids))).all()
    open_alerts = db.scalars(select(models.Alert).where(
        models.Alert.user_id.in_(ids), models.Alert.status.in_(("open", "escalated")))).all()
    last_sleep = dict(db.execute(select(models.SleepEntry.user_id, func.max(models.SleepEntry.night))
                                 .where(models.SleepEntry.user_id.in_(ids))
                                 .group_by(models.SleepEntry.user_id)).all())
    out = []
    for u in users:
        mine = [a for a in open_alerts if a.user_id == u.id]
        top = max((a.severity for a in mine), key=SEVERITY_RANK.__getitem__, default="ok")
        last = last_sleep.get(u.id)
        out.append({"user_id": u.id, "name": u.name, "status": top,
                    "has_critical": any(a.priority == "critical" for a in mine),
                    "open_alerts": len(mine),
                    "last_sleep_night": last.isoformat() if last else None})
    out.sort(key=lambda x: (not x["has_critical"], -SEVERITY_RANK.get(x["status"], -1)))
    audit(db, actor.id, "read_overview", None, "clinician/overview")
    db.commit()
    return with_disclaimer(out)


@router.get("/review-queue")
def review_queue(actor: models.User = Depends(clin), db: Session = Depends(get_db)):
    ids = assigned_astronaut_ids(db, actor)
    names = dict(db.execute(select(models.User.id, models.User.name).where(models.User.id.in_(ids))).all())
    alerts = db.scalars(select(models.Alert).where(
        models.Alert.user_id.in_(ids), models.Alert.severity == "review_required",
        models.Alert.status.in_(("open", "escalated")))).all()
    alerts.sort(key=lambda a: (a.priority != "critical", -a.created_at.timestamp()))  # críticos primeiro
    audit(db, actor.id, "read_review_queue", None, "clinician/review-queue")
    db.commit()
    return with_disclaimer([_alert_dict(a, names.get(a.user_id)) for a in alerts])


@router.get("/users/{uid}/timeline")
def user_timeline(uid: str, days: int = 45, as_of: date | None = None,
                  actor: models.User = Depends(clin), db: Session = Depends(get_db)):
    ensure_can_access(db, actor, uid)
    audit(db, actor.id, "read_timeline", uid, "clinician/timeline")
    db.commit()
    return with_disclaimer(build_timeline(db, uid, as_of or date.today(), min(max(days, 7), 180)))


@router.get("/alerts/{alert_id}")
def alert_detail(alert_id: int, actor: models.User = Depends(clin), db: Session = Depends(get_db)):
    a = _alert_or_404(db, actor, alert_id)
    plans = db.scalars(select(models.ActionPlan).where(models.ActionPlan.alert_id == a.id)
                       .order_by(models.ActionPlan.id.desc())).all()
    name = db.scalar(select(models.User.name).where(models.User.id == a.user_id))
    audit(db, actor.id, "read_alert", a.user_id, f"alert:{a.id}")
    db.commit()
    data = _alert_dict(a, name, full=True)
    data["action_plans"] = [{"id": p.id, "status": p.status, "severity": p.severity,
                             "actions": p.actions} for p in plans]
    return with_disclaimer(data)


@router.post("/alerts/{alert_id}/review")
def review_alert(alert_id: int, body: ReviewIn, actor: models.User = Depends(clin),
                 db: Session = Depends(get_db)):
    """Human-in-the-loop: só o clínico fecha/valida um alerta."""
    a = _alert_or_404(db, actor, alert_id)
    a.review_decision = body.decision
    a.review_note = body.note
    a.reviewed_by = actor.id
    a.reviewed_at = datetime.now(timezone.utc)
    a.status = {"confirmed": "reviewed", "dismissed": "dismissed", "needs_followup": "open"}[body.decision]
    audit(db, actor.id, f"review_{body.decision}", a.user_id, f"alert:{a.id}")
    db.commit()
    return with_disclaimer(_alert_dict(a, full=True))


@router.post("/alerts/{alert_id}/escalate")
def escalate_alert(alert_id: int, actor: models.User = Depends(clin), db: Session = Depends(get_db)):
    """Escalonamento SEMPRE decidido por humano; fica registrado no audit log."""
    a = _alert_or_404(db, actor, alert_id)
    if a.status not in ("open", "escalated"):
        raise HTTPException(409, f"Alert is {a.status}")
    a.status = "escalated"
    a.escalated_by = actor.id
    a.escalated_at = datetime.now(timezone.utc)
    audit(db, actor.id, "escalate", a.user_id, f"alert:{a.id}")
    db.commit()
    return with_disclaimer(_alert_dict(a, full=True))


@router.get("/rule-feedback")
def rule_feedback(actor: models.User = Depends(clin), db: Session = Depends(get_db)):
    """Falsos positivos viram feedback para calibrar as regras."""
    ids = assigned_astronaut_ids(db, actor)
    alerts = db.scalars(select(models.Alert).where(
        models.Alert.user_id.in_(ids), models.Alert.review_decision.is_not(None))).all()
    stats: dict[str, dict] = {}
    for a in alerts:
        for rid in a.rule_ids:
            s = stats.setdefault(rid, {"confirmed": 0, "dismissed": 0, "needs_followup": 0})
            s[a.review_decision] += 1
    for s in stats.values():
        total = sum(s.values())
        s["total"] = total
        s["false_positive_rate"] = round(s["dismissed"] / total, 3) if total else None
    return with_disclaimer(stats)


@router.get("/audit-log")
def audit_log(limit: int = 100, actor: models.User = Depends(clin), db: Session = Depends(get_db)):
    q = select(models.AuditLog).order_by(models.AuditLog.id.desc()).limit(min(max(limit, 1), 500))
    if actor.role != "admin":
        ids = assigned_astronaut_ids(db, actor)
        q = q.where((models.AuditLog.target_user.in_(ids)) | (models.AuditLog.actor_id == actor.id))
    rows = db.scalars(q).all()
    return with_disclaimer([{"id": r.id, "actor_id": r.actor_id, "action": r.action,
                             "target_user": r.target_user, "resource": r.resource,
                             "ts": r.ts.isoformat()} for r in rows])
