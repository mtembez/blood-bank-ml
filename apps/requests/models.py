import uuid
from django.db import models
from apps.hospitals.models import Hospital
from apps.inventory.models import BloodInventory


class BloodRequest(models.Model):
    """Clinical request for blood units initiated by a partner hospital."""

    URGENCY_ROUTINE = "routine"
    URGENCY_URGENT = "urgent"
    URGENCY_CRITICAL_STAT = "critical_stat"
    URGENCY_CHOICES = (
        (URGENCY_ROUTINE, "Routine"),
        (URGENCY_URGENT, "Urgent (Within 4 hours)"),
        (URGENCY_CRITICAL_STAT, "Critical / STAT (Immediate emergency)"),
    )

    STATUS_PENDING = "pending"
    STATUS_MATCHING = "matching"
    STATUS_ALLOCATED = "allocated"
    STATUS_DISPATCHED = "dispatched"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_MATCHING, "Matching In Progress"),
        (STATUS_ALLOCATED, "Allocated"),
        (STATUS_DISPATCHED, "Dispatched"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name="blood_requests")
    blood_group = models.CharField(max_length=5, db_index=True)
    component_type = models.CharField(max_length=30, default="whole_blood")
    units_requested = models.IntegerField()
    units_allocated = models.IntegerField(default=0)
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default=URGENCY_ROUTINE, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    patient_age = models.IntegerField(null=True, blank=True)
    patient_gender = models.CharField(max_length=10, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "blood_requests"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(units_requested__gt=0),
                name="blood_request_units_positive",
            ),
            models.CheckConstraint(
                check=models.Q(units_allocated__gte=0),
                name="blood_request_units_allocated_nonnegative",
            ),
        ]

    def __str__(self):
        return f"Req {self.id} [{self.urgency.upper()}] - {self.units_requested} units of {self.blood_group} for {self.hospital.name}"


class RequestAllocation(models.Model):
    """Specific cold-chain inventory unit reserved or dispatched for a blood request."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(BloodRequest, on_delete=models.CASCADE, related_name="allocations")
    inventory_unit = models.ForeignKey(BloodInventory, on_delete=models.PROTECT, related_name="request_allocations")
    allocated_at = models.DateTimeField(auto_now_add=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "request_allocations"
        unique_together = ("request", "inventory_unit")

    def __str__(self):
        return f"Allocation: Unit {self.inventory_unit.unit_number} -> Req {self.request.id}"
