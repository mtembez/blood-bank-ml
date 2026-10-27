from rest_framework import serializers
from apps.hospitals.models import Hospital


class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = (
            "id",
            "name",
            "code",
            "tier",
            "latitude",
            "longitude",
            "contact_email",
            "contact_phone",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class RegisterHospitalSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(read_only=True)

    class Meta:
        model = Hospital
        fields = (
            "id",
            "name",
            "code",
            "tier",
            "latitude",
            "longitude",
            "contact_email",
            "contact_phone",
            "api_key",
        )
        read_only_fields = ("id", "api_key")

    def validate_code(self, value):
        code = value.strip().upper()
        if Hospital.objects.filter(code=code).exists():
            raise serializers.ValidationError("A hospital with this code already exists.")
        return code
