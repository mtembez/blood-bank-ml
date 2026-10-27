from rest_framework import serializers
from apps.donors.models import DonationHistory, Donor


class DonationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationHistory
        fields = (
            "id",
            "donation_date",
            "volume_ml",
            "screening_passed",
            "adverse_reaction",
            "notes",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class DonorSerializer(serializers.ModelSerializer):
    donation_history = DonationHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Donor
        fields = (
            "id",
            "national_id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "blood_group",
            "age",
            "gender",
            "weight_kg",
            "hemoglobin_level",
            "systolic_bp",
            "diastolic_bp",
            "latitude",
            "longitude",
            "last_donation_date",
            "donation_count",
            "is_eligible",
            "created_at",
            "donation_history",
        )
        read_only_fields = ("id", "created_at", "donation_history")


class NearbyDonorSerializer(serializers.ModelSerializer):
    distance_km = serializers.FloatField(read_only=True)

    class Meta:
        model = Donor
        fields = (
            "id",
            "national_id",
            "first_name",
            "last_name",
            "phone",
            "blood_group",
            "age",
            "gender",
            "weight_kg",
            "hemoglobin_level",
            "latitude",
            "longitude",
            "distance_km",
            "is_eligible",
            "donation_count",
        )
