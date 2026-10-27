import uuid
from django.db import models
from django.utils import timezone
from apps.donors.models import Donor


class BloodInventory(models.Model):
    """Cold-chain blood component inventory unit."""

    STATUS_AVAILABLE = "available"
    STATUS_RESERVED = "reserved"
    STATUS_TRANSFUSED = "transfused"
    STATUS_EXPIRED = "expired"
    STATUS_DISCARDED = "discarded"
    STATUS_CHOICES = (
        (STATUS_AVAILABLE, "Available"),
        (STATUS_RESERVED, "Reserved"),
        (STATUS_TRANSFUSED, "Transfused"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_DISCARDED, "Discarded"),
    )

    COMPONENT_WHOLE_BLOOD = "whole_blood"
    COMPONENT_RBC = "rbc"
    COMPONENT_PLATELETS = "platelets"
    COMPONENT_PLASMA = "plasma"
    COMPONENT_CHOICES = (
        (COMPONENT_WHOLE_BLOOD, "Whole Blood"),
        (COMPONENT_RBC, "Packed Red Blood Cells (PRBC)"),
        (COMPONENT_PLATELETS, "Platelet Concentrate"),
        (COMPONENT_PLASMA, "Fresh Frozen Plasma (FFP)"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit_number = models.CharField(max_length=50, unique=True, db_index=True)
    blood_group = models.CharField(max_length=5, db_index=True)
    component_type = models.CharField(max_length=30, choices=COMPONENT_CHOICES, default=COMPONENT_WHOLE_BLOOD)
    volume_ml = models.IntegerField(default=450)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AVAILABLE, db_index=True)
    donor = models.ForeignKey(Donor, on_delete=models.SET_NULL, null=True, blank=True, related_name="donated_units")
    collected_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(db_index=True)
    storage_location = models.CharField(max_length=100, default="Central Cold Storage - Vault 1")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "blood_inventory"
        ordering = ["expires_at"]
        indexes = [
            models.Index(fields=["blood_group", "component_type", "status"]),
            models.Index(fields=["status", "expires_at"]),
        ]

    def __str__(self):
        return f"{self.unit_number} ({self.blood_group} - {self.component_type}) [{self.status}]"

    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at
