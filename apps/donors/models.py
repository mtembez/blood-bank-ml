import uuid
from django.db import models


class Donor(models.Model):
    """Registered voluntary blood donor with clinical screening metrics and location."""

    BLOOD_GROUP_CHOICES = (
        ("A+", "A+"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B-", "B-"),
        ("AB+", "AB+"),
        ("AB-", "AB-"),
        ("O+", "O+"),
        ("O-", "O-"),
    )

    GENDER_CHOICES = (
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    national_id = models.CharField(max_length=50, unique=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, db_index=True)
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES, db_index=True)
    age = models.IntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    hemoglobin_level = models.DecimalField(max_digits=4, decimal_places=1)
    systolic_bp = models.IntegerField(default=120)
    diastolic_bp = models.IntegerField(default=80)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    last_donation_date = models.DateField(null=True, blank=True)
    donation_count = models.IntegerField(default=0)
    is_eligible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "donors"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(age__gte=16, age__lte=65),
                name="donor_age_eligibility_range",
            ),
            models.CheckConstraint(
                check=models.Q(weight_kg__gte=50.0),
                name="donor_minimum_weight_50kg",
            ),
            models.CheckConstraint(
                check=models.Q(hemoglobin_level__gte=7.0, hemoglobin_level__lte=20.0),
                name="donor_hemoglobin_clinical_range",
            ),
            models.CheckConstraint(
                check=models.Q(systolic_bp__gte=80, systolic_bp__lte=200),
                name="donor_systolic_bp_range",
            ),
            models.CheckConstraint(
                check=models.Q(diastolic_bp__gte=50, diastolic_bp__lte=130),
                name="donor_diastolic_bp_range",
            ),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.blood_group}) - ID: {self.national_id}"


class DonationHistory(models.Model):
    """Historical audit of completed blood donations by a donor."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE, related_name="donation_history")
    donation_date = models.DateField()
    volume_ml = models.IntegerField(default=450)
    screening_passed = models.BooleanField(default=True)
    adverse_reaction = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "donation_history"
        ordering = ["-donation_date"]

    def __str__(self):
        return f"Donation by {self.donor} on {self.donation_date} ({self.volume_ml}ml)"
