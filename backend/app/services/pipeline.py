"""Cola entre banco e motor puro: carrega dados, analisa, persiste alertas e planos."""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from .. import models
from ..audit import audit
from . import actions, baseline as bl, engine, rules as rl

RULES = rl.load_rules()
LOOKBACK_DAYS = 60
CLEAR_AFTER_DAYS = 3                 # dias sem hit para encerrar/limpar um alerta
ACTIVE_STATUSES = ("open", "escalated")


def load_baselines(db: Session, user_id: str) -> dict[str, bl.BaselineStat]:
    rows = db.scalars(select(models.Baseline).where(models.Baseline.user_id == user_id)
                      .order_by(models.Baseline.id)).all()
    return {r.indicator: bl.BaselineStat(r.mean, r.stddev, r.n_samples, r.window_start, r.window_end)
            for r in rows}  # a linha mais recente de cada indicador prevalece


def fetch_rows(db: Session, user_id: str, as_of: date, lookback: int = LOOKBACK_DAYS):
    start = as_of - timedelta(days=lookback)
    lo = datetime.combine(start, time.min, tzinfo=timezone.utc)
    hi = datetime.combine(as_of + timedelta(days=1), time.min, tzinfo=timezone.utc)
    sleep = db.scalars(select(models.SleepEntry).where(
        models.SleepEntry.user_id == user_id, models.SleepEntry.night >= start,
        models.SleepEntry.night <= as_of)).all()
    vitals = db.scalars(select(models.Vital).where(
        models.Vital.user_id == user_id, models.Vital.ts >= lo, models.Vital.ts < hi)).all()
    diary = db.scalars(select(models.DiaryFeature).where(
        models.DiaryFeature.user_id == user_id, models.DiaryFeature.consent.is_(True),
        models.DiaryFeature.ts >= lo, models.DiaryFeature.ts < hi)).all()
    return sleep, vitals, diary


def _baseline_blocked(db: Session, user_id: str, as_of: date) -> bool:
    """Há alerta ativo ou hit recente? Então o baseline NÃO pode se adaptar."""
    n = db.scalar(select(func.count(models.Alert.id)).where(
        models.Alert.user_id == user_id,
        or_(models.Alert.status.in_(ACTIVE_STATUSES),
            models.Alert.last_hit_date >= as_of - timedelta(days=bl.SUSTAIN_DAYS))))
    return bool(n)


def _notify_clinicians(db: Session, alert: models.Alert) -> None:
    """Ponto de integração: troque por push/e-mail/webhook. Aqui só enfileira no audit."""
    ids = db.scalars(select(models.Assignment.clinician_id)
                     .where(models.Assignment.astronaut_id == alert.user_id)).all()
    for cid in ids:
        audit(db, None, "notification_queued", alert.user_id, f"alert:{alert.id}->clinician:{cid}")


def _new_plan(db: Session, alert: models.Alert, topics: list[str]) -> None:
    db.execute(update(models.ActionPlan)
               .where(models.ActionPlan.alert_id == alert.id, models.ActionPlan.status != "superseded")
               .values(status="superseded"))
    plan = actions.generate_action_plan(alert.severity, alert.priority, topics)
    db.add(models.ActionPlan(alert_id=alert.id, user_id=alert.user_id, severity=plan["severity"],
                             priority=plan["priority"], actions=plan["actions"], status=plan["status"]))


def _explanation(hits, as_of, topics, context) -> dict:
    return {
        "as_of": as_of.isoformat(),
        "summary": [h.explanation for h in hits],
        "rules": [{"id": h.rule_id, "severity": h.severity, "explanation": h.explanation,
                   "window": [h.window_start.isoformat(), h.window_end.isoformat()],
                   "evidence": h.evidence} for h in hits],
        "topics": topics,
        "context": context,
        "conditions_cleared": False,
    }


def _event_ts(hits) -> str | None:
    for h in hits:
        for e in h.evidence:
            if "event_ts" in e:
                return e["event_ts"]
    return None


def _upsert_alert(db: Session, user_id: str, as_of: date, priority: str, hits, topics, context):
    rank = rl.SEVERITY_RANK
    severity = max((h.severity for h in hits), key=rank.__getitem__)
    rule_ids = sorted({h.rule_id for h in hits})
    expl = _explanation(hits, as_of, topics, context)

    if priority == "critical":
        ev_ts = _event_ts(hits)
        expl["event_ts"] = ev_ts
        # o mesmo registro de diário nunca gera dois alertas críticos
        for a in db.scalars(select(models.Alert).where(
                models.Alert.user_id == user_id, models.Alert.priority == "critical")):
            if (a.explanation or {}).get("event_ts") == ev_ts:
                return None

    existing = db.scalars(select(models.Alert).where(
        models.Alert.user_id == user_id, models.Alert.priority == priority,
        models.Alert.status.in_(ACTIVE_STATUSES)).order_by(models.Alert.id.desc())).first()

    if existing and priority != "critical":
        upgraded = rank[severity] > rank[existing.severity]
        existing.last_hit_date = as_of
        existing.severity = severity if upgraded else existing.severity
        existing.rule_ids = sorted(set(existing.rule_ids) | set(rule_ids))
        expl["first_seen"] = (existing.explanation or {}).get("first_seen", existing.created_at.date().isoformat())
        existing.explanation = expl
        if upgraded:
            _new_plan(db, existing, topics)
            if existing.severity == "review_required":
                _notify_clinicians(db, existing)
        return existing

    alert = models.Alert(user_id=user_id, severity=severity, priority=priority, status="open",
                         rule_ids=rule_ids, explanation=expl, auto_action=False, last_hit_date=as_of)
    db.add(alert)
    db.flush()
    expl["first_seen"] = as_of.isoformat()
    alert.explanation = dict(expl)
    _new_plan(db, alert, topics)
    if severity == "review_required":
        _notify_clinicians(db, alert)
    audit(db, None, "alert_created", user_id, f"alert:{alert.id}:{severity}:{priority}")
    return alert


def _clear_stale(db: Session, user_id: str, as_of: date, touched_ids: set[int]) -> None:
    open_alerts = db.scalars(select(models.Alert).where(
        models.Alert.user_id == user_id, models.Alert.status == "open",
        models.Alert.priority == "normal")).all()
    for a in open_alerts:
        if a.id in touched_ids or a.last_hit_date is None:
            continue
        if (as_of - a.last_hit_date).days < CLEAR_AFTER_DAYS:
            continue
        if a.severity == "review_required":
            # condições normalizaram, mas só um humano fecha um review_required
            if not (a.explanation or {}).get("conditions_cleared"):
                a.explanation = {**a.explanation, "conditions_cleared": True,
                                 "cleared_on": as_of.isoformat()}
        else:
            a.status = "auto_resolved"
            a.explanation = {**a.explanation, "cleared_on": as_of.isoformat()}


def run_pipeline(db: Session, user_id: str, as_of: date) -> list[models.Alert]:
    sleep, vitals, diary = fetch_rows(db, user_id, as_of)
    current = load_baselines(db, user_id)
    res = engine.analyze(sleep, vitals, diary, current, as_of,
                         block_baseline_updates=_baseline_blocked(db, user_id, as_of), rules=RULES)

    for metric, stat in res.updated_baselines.items():
        db.add(models.Baseline(user_id=user_id, indicator=metric, window_start=stat.window_start,
                               window_end=stat.window_end, mean=stat.mean, stddev=stat.std,
                               n_samples=stat.n))

    week = {as_of - timedelta(days=i) for i in range(7)}
    topics_counter = Counter(t for e in res.events if e["date"] in week
                             for t in e["features"].get("topic_tags", []))
    topics = [t for t, _ in topics_counter.most_common()]
    context = {"high_workload_recent": bool(res.workload_days & week)}

    touched: list[models.Alert] = []
    for priority in ("critical", "normal"):
        group = [h for h in res.hits if h.priority == priority]
        if group:
            alert = _upsert_alert(db, user_id, as_of, priority, group, topics, context)
            if alert is not None:
                touched.append(alert)

    _clear_stale(db, user_id, as_of, {a.id for a in touched})
    db.commit()
    return touched
