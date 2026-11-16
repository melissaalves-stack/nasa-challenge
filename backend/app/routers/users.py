from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..audit import audit
from ..auth import create_token, ensure_can_access, get_current_user
from ..db import get_db
from ..passwords import verify_password
from ..responses import with_disclaimer
from ..schemas import ConsentIn, FeedbackIn, LoginIn
from ..services.timeline import build_timeline

router = APIRouter(tags=["users"])


def _public(u: models.User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role,
            "consent_diary": u.consent_diary, "consent_voice": u.consent_voice}


@router.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return {"access_token": create_token(user), "token_type": "bearer", "user": _public(user)}


@router.get("/auth/me")
def me(user: models.User = Depends(get_current_user)):
    return _public(user)


@router.post("/users/{uid}/consent")
def set_consent(uid: str, body: ConsentIn, actor: models.User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """Consentimento explícito e revogável: o próprio astronauta controla seus dados."""
    if actor.id != uid:
        raise HTTPException(403, "Only the user can change their own consent")
    if body.diary is not None:
        actor.consent_diary = body.diary
    if body.voice is not None:
        actor.consent_voice = body.voice
    audit(db, actor.id, "consent_changed", uid, f"diary={actor.consent_diary},voice={actor.consent_voice}")
    db.commit()
    return _public(actor)


@router.get("/users/{uid}/timeline")
def timeline(uid: str, days: int = 45, as_of: date | None = None,
             actor: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_can_access(db, actor, uid)
    if actor.id != uid:
        audit(db, actor.id, "read_timeline", uid, "users/timeline")
        db.commit()
    return with_disclaimer(build_timeline(db, uid, as_of or date.today(), min(max(days, 7), 180)))


@router.get("/users/{uid}/action-plan")
def action_plan(uid: str, actor: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_can_access(db, actor, uid)
    rows = db.execute(
        select(models.ActionPlan, models.Alert)
        .join(models.Alert, models.Alert.id == models.ActionPlan.alert_id)
        .where(models.ActionPlan.user_id == uid, models.ActionPlan.status != "superseded",
               models.Alert.status.in_(("open", "escalated")))
        .order_by(models.ActionPlan.id.desc())).all()
    plans = [{"id": p.id, "alert_id": a.id, "severity": p.severity, "priority": p.priority,
              "status": p.status, "actions": p.actions, "created_at": p.created_at.isoformat()}
             for p, a in rows]
    if actor.id != uid:
        audit(db, actor.id, "read_action_plan", uid, "users/action-plan")
        db.commit()
    return with_disclaimer(plans)


@router.post("/action-plans/{plan_id}/feedback", status_code=201)
def plan_feedback(plan_id: int, body: FeedbackIn, actor: models.User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """O astronauta marca cada ação como útil/não útil (calibra recomendações)."""
    plan = db.get(models.ActionPlan, plan_id)
    if not plan or plan.user_id != actor.id:
        raise HTTPException(404, "Plan not found")
    if body.action_index >= len(plan.actions):
        raise HTTPException(422, "action_index out of range")
    db.add(models.PlanFeedback(plan_id=plan_id, user_id=actor.id,
                               action_index=body.action_index, helpful=body.helpful))
    db.commit()
    return {"stored": True}
