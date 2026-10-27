import logging
from apps.audit.models import AuditLog

logger = logging.getLogger(__name__)


def log_audit_event(
    actor_type: str,
    actor_id: str,
    action: str,
    target_model: str,
    target_id: str,
    details: dict = None,
    ip_address: str = None,
) -> AuditLog:
    """Create a persistent immutable audit log entry."""
    details = details or {}
    log = AuditLog.objects.create(
        actor_type=str(actor_type),
        actor_id=str(actor_id),
        action=str(action),
        target_model=str(target_model),
        target_id=str(target_id),
        details=details,
        ip_address=ip_address,
    )
    logger.info(
        "AUDIT: %s %s performed '%s' on %s (%s)",
        actor_type,
        actor_id,
        action,
        target_model,
        target_id,
    )
    return log
