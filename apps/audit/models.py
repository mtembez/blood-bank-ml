import uuid
from django.db import models


class AuditLog(models.Model):
    """Tamper-evident audit record capturing API requests, matching runs, and allocations."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_type = models.CharField(max_length=50, db_index=True)
    actor_id = models.CharField(max_length=100, db_index=True)
    action = models.CharField(max_length=100, db_index=True)
    target_model = models.CharField(max_length=50, db_index=True)
    target_id = models.CharField(max_length=100, db_index=True)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["actor_type", "actor_id"]),
            models.Index(fields=["target_model", "target_id"]),
        ]

    def __str__(self):
        return f"[{self.timestamp.isoformat()}] {self.actor_type}:{self.actor_id} -> {self.action} on {self.target_model}:{self.target_id}"
