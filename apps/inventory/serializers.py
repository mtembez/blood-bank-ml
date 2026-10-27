from rest_framework import serializers
from apps.donors.serializers import DonorSerializer
from apps.inventory.models import BloodInventory


class BloodInventorySerializer(serializers.ModelSerializer):
    donor_details = DonorSerializer(source="donor", read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = BloodInventory
        fields = (
            "id",
            "unit_number",
            "blood_group",
            "component_type",
            "volume_ml",
            "status",
            "donor",
            "donor_details",
            "collected_at",
            "expires_at",
            "storage_location",
            "is_expired",
            "created_at",
        )
        read_only_fields = ("id", "created_at", "is_expired")
