"""Modelo de dados. Tipos portáveis (SQLite p/ demo, PostgreSQL em produção).

NOTA DE PRIVACIDADE: não existe coluna de texto do diário. Só features + hash.
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))  # astronaut | clinician | admin
    password_hash: Mapped[str] = mapped_column(String(255))
    mission_phase: Mapped[str] = mapped_column(String(20), default="mid")
    consent_diary: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_voice: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Assignment(Base):
    """Quais astronautas cada clínico pode ver."""
    __tablename__ = "assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinician_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    astronaut_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    __table_args__ = (UniqueConstraint("clinician_id", "astronaut_id"),)


class Vital(Base):  # pulseira
    __tablename__ = "vitals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    systolic: Mapped[int | None] = mapped_column(Integer)
    diastolic: Mapped[int | None] = mapped_column(Integer)
    spo2: Mapped[float | None] = mapped_column(Float)
    fatigue_score: Mapped[float | None] = mapped_column(Float)
    data_quality: Mapped[str] = mapped_column(String(20), default="good")
    __table_args__ = (Index("ix_vitals_user_ts", "user_id", "ts"),)


class SleepEntry(Base):
    __tablename__ = "sleep_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    night: Mapped[date] = mapped_column(Date)
    duration_h: Mapped[float | None] = mapped_column(Float)
    latency_min: Mapped[float | None] = mapped_column(Float)
    awakenings: Mapped[int | None] = mapped_column(Integer)
    efficiency: Mapped[float | None] = mapped_column(Float)
    perceived_quality: Mapped[int | None] = mapped_column(Integer)
    muscle_density: Mapped[float | None] = mapped_column(Float)  # proxy sintético, só contexto
    cognitive_rt_ms: Mapped[float | None] = mapped_column(Float)  # tempo de reação (desempenho cognitivo)
    high_workload: Mapped[bool] = mapped_column(Boolean, default=False)
    data_quality: Mapped[str] = mapped_column(String(20), default="good")
    __table_args__ = (UniqueConstraint("user_id", "night"),)


class DiaryFeature(Base):
    __tablename__ = "diary_features"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    text_hash: Mapped[str] = mapped_column(String(64))
    features: Mapped[dict] = mapped_column(JSON)
    local_model_version: Mapped[str] = mapped_column(String(64))
    consent: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("user_id", "text_hash"), Index("ix_diary_user_ts", "user_id", "ts"))


class Baseline(Base):
    """Histórico de baselines: cada atualização é uma nova linha (a mais recente vale)."""
    __tablename__ = "baselines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    indicator: Mapped[str] = mapped_column(String(50))
    window_start: Mapped[date | None] = mapped_column(Date)
    window_end: Mapped[date | None] = mapped_column(Date)
    mean: Mapped[float] = mapped_column(Float)
    stddev: Mapped[float] = mapped_column(Float)
    n_samples: Mapped[int] = mapped_column(Integer)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    severity: Mapped[str] = mapped_column(String(20))   # info | watch | review_required
    priority: Mapped[str] = mapped_column(String(10), default="normal")  # normal | critical
    # open | reviewed | dismissed | escalated | auto_resolved
    status: Mapped[str] = mapped_column(String(20), default="open")
    rule_ids: Mapped[list] = mapped_column(JSON)
    explanation: Mapped[dict] = mapped_column(JSON)
    auto_action: Mapped[bool] = mapped_column(Boolean, default=False)  # sempre False
    last_hit_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    reviewed_by: Mapped[str | None] = mapped_column(String(36))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_decision: Mapped[str | None] = mapped_column(String(20))
    review_note: Mapped[str | None] = mapped_column(Text)
    escalated_by: Mapped[str | None] = mapped_column(String(36))
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ActionPlan(Base):
    __tablename__ = "action_plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    severity: Mapped[str] = mapped_column(String(20))
    priority: Mapped[str] = mapped_column(String(10), default="normal")
    actions: Mapped[list] = mapped_column(JSON)
    # suggested | pending_human_review | superseded
    status: Mapped[str] = mapped_column(String(25), default="suggested")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PlanFeedback(Base):
    __tablename__ = "plan_feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("action_plans.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    action_index: Mapped[int] = mapped_column(Integer)
    helpful: Mapped[bool] = mapped_column(Boolean)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[str | None] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(60))
    target_user: Mapped[str | None] = mapped_column(String(36), index=True)
    resource: Mapped[str | None] = mapped_column(String(120))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
