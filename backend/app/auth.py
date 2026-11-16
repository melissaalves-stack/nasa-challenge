from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .config import ACCESS_TOKEN_MINUTES, SECRET_KEY
from .db import get_db

ALGORITHM = "HS256"
_bearer = HTTPBearer(auto_error=False)


def create_token(user: models.User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    return jwt.encode({"sub": user.id, "role": user.role, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> models.User:
    if creds is None:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = db.get(models.User, payload.get("sub"))
    if user is None:
        raise HTTPException(401, "Unknown user")
    return user


def require_roles(*roles: str):
    def dep(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(403, "Insufficient role")
        return user
    return dep


def assigned_astronaut_ids(db: Session, actor: models.User) -> list[str]:
    """Admin vê todos; clínico só os astronautas atribuídos a ele."""
    if actor.role == "admin":
        return list(db.scalars(select(models.User.id).where(models.User.role == "astronaut")))
    if actor.role == "clinician":
        return list(db.scalars(select(models.Assignment.astronaut_id)
                               .where(models.Assignment.clinician_id == actor.id)))
    return []


def ensure_can_access(db: Session, actor: models.User, uid: str) -> None:
    if actor.id == uid and actor.role in ("astronaut", "admin"):
        return
    if uid in assigned_astronaut_ids(db, actor):
        return
    raise HTTPException(404, "User not found")  # 404 p/ não revelar existência
