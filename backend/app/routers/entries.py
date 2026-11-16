import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..auth import require_roles
from ..db import get_db
from ..schemas import DiaryIn, SleepIn, VitalsBatchIn
from ..services import privacy
from ..services.pipeline import run_pipeline

router = APIRouter(prefix="/entries", tags=["entries"])
log = logging.getLogger("astrokatu.entries")
astronaut_only = require_roles("astronaut")


def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


@router.post("/vitals", status_code=201)
def post_vitals(body: VitalsBatchIn, user: models.User = Depends(astronaut_only),
                db: Session = Depends(get_db)):
    """Pulseira: pressão, SpO2 e fadiga (lote a cada ~5 min)."""
    for r in body.readings:
        data = r.model_dump()
        data["ts"] = _utc(data["ts"])
        db.add(models.Vital(user_id=user.id, **data))
    db.commit()
    return {"stored": len(body.readings)}


@router.post("/sleep", status_code=201)
def post_sleep(body: SleepIn, user: models.User = Depends(astronaut_only),
               db: Session = Depends(get_db)):
    """Telemetria diária (ao acordar). Reenviar a mesma noite atualiza o registro."""
    data = body.model_dump()
    existing = db.scalar(select(models.SleepEntry).where(
        models.SleepEntry.user_id == user.id, models.SleepEntry.night == body.night))
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
    else:
        db.add(models.SleepEntry(user_id=user.id, **data))
    db.commit()
    run_pipeline(db, user.id, body.night)
    return {"stored": True, "analysis_ran": True}


@router.post("/diary", status_code=201)
def post_diary(body: DiaryIn, user: models.User = Depends(astronaut_only),
               db: Session = Depends(get_db)):
    """Diário privacy-preserving: SÓ features + hash. Texto cru => 422."""
    if not user.consent_diary:
        raise HTTPException(403, "Diary consent revoked")
    try:
        text_hash = privacy.validate_text_hash(body.text_hash)
        features = privacy.validate_diary_features(body.features, consent=body.consent)
    except privacy.PrivacyViolation as e:
        raise HTTPException(e.status, str(e))

    if db.scalar(select(models.DiaryFeature.id).where(
            models.DiaryFeature.user_id == user.id, models.DiaryFeature.text_hash == text_hash)):
        raise HTTPException(409, "Duplicate entry (text_hash already stored)")

    ts = _utc(body.ts)
    db.add(models.DiaryFeature(user_id=user.id, ts=ts, text_hash=text_hash, features=features,
                               local_model_version=body.local_model_version, consent=True))
    db.commit()
    # NUNCA logar o payload; só hash + versão do modelo
    log.info("diary stored %s", privacy.safe_log_ref(text_hash, body.local_model_version))
    run_pipeline(db, user.id, ts.date())
    return {"stored": True, "analysis_ran": True}
