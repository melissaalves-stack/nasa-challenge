from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginIn(StrictModel):
    email: str
    password: str


class VitalIn(StrictModel):
    ts: datetime
    systolic: int | None = Field(None, ge=50, le=250)
    diastolic: int | None = Field(None, ge=30, le=150)
    spo2: float | None = Field(None, ge=50, le=100)
    fatigue_score: float | None = Field(None, ge=0, le=10)


class VitalsBatchIn(StrictModel):
    readings: list[VitalIn] = Field(min_length=1, max_length=500)


class SleepIn(StrictModel):
    night: date
    duration_h: float = Field(ge=0, le=24)
    latency_min: float | None = Field(None, ge=0, le=600)
    awakenings: int | None = Field(None, ge=0, le=50)
    efficiency: float | None = Field(None, ge=0, le=1)
    perceived_quality: int | None = Field(None, ge=1, le=10)
    muscle_density: float | None = None                 # proxy sintético (contexto)
    cognitive_rt_ms: float | None = Field(None, ge=50, le=5000)
    high_workload: bool = False
    data_quality: Literal["good", "poor", "missing_data"] = "good"


class DiaryIn(StrictModel):
    """O texto do diário NÃO existe neste contrato: só features + hash."""
    ts: datetime
    text_hash: str
    features: dict[str, Any]
    local_model_version: str = Field(min_length=1, max_length=64)
    consent: bool


class ConsentIn(StrictModel):
    diary: bool | None = None
    voice: bool | None = None


class ReviewIn(StrictModel):
    decision: Literal["confirmed", "dismissed", "needs_followup"]
    note: str = Field("", max_length=2000)


class FeedbackIn(StrictModel):
    action_index: int = Field(ge=0)
    helpful: bool


class SimulateIn(StrictModel):
    scenario: str
    user_id: str
    seed: int = 42
    reset: bool = True
    start_date: date | None = None
