from sqlalchemy.orm import Session

from . import models


def audit(db: Session, actor_id, action: str, target_user=None, resource: str | None = None) -> None:
    """Registra no audit_log (o commit fica com o chamador)."""
    db.add(models.AuditLog(actor_id=actor_id, action=action, target_user=target_user, resource=resource))
