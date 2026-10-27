import secrets
import uuid
from django.db import models


class Hospital(models.Model):
    """Registered partner hospital or emergency medical center."""

    TIER_LEVEL_4 = "level_4"
    TIER_LEVEL_5 = "level_5"
    TIER_LEVEL_6 = "level_6"
    TIER_CHOICES = (
        (TIER_LEVEL_4, "County / District Hospital"),
        (TIER_LEVEL_5, "Regional Referral Hospital"),
        (TIER_LEVEL_6, "National Teaching & Referral Hospital"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    api_key = models.CharField(max_length=64, unique=True, db_index=True, blank=True)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default=TIER_LEVEL_4)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    contact_email = models.EmailField(max_length=255)
    contact_phone = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hospitals"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} [{self.code}]"

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = secrets.token_hex(32)
        super().save(*args, **kwargs)
