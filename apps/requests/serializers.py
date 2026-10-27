from rest_framework import serializers
from apps.hospitals.serializers import HospitalSerializer
from apps.inventory.serializers import BloodInventorySerializer
from apps.requests.models import BloodRequest, RequestAllocation


class RequestAllocationSerializer(serializers.ModelSerializer):
    inventory_unit = BloodInventorySerializer(read_only=True)

    class Meta:
        model = RequestAllocation
        fields = ("id", "inventory_unit", "allocated_at", "dispatched_at")
        read_only_fields = fields


class BloodRequestSerializer(serializers.ModelSerializer):
    hospital = HospitalSerializer(read_only=True)
    allocations = RequestAllocationSerializer(many=True, read_only=True)

    class Meta:
        model = BloodRequest
        fields = (
            "id",
            "hospital",
            "blood_group",
            "component_type",
            "units_requested",
            "units_allocated",
            "urgency",
            "status",
            "patient_age",
            "patient_gender",
            "notes",
            "created_at",
            "updated_at",
            "allocations",
        )
        read_only_fields = ("id", "units_allocated", "status", "created_at", "updated_at", "allocations")


class CreateBloodRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BloodRequest
        fields = (
            "blood_group",
            "component_type",
            "units_requested",
            "urgency",
            "patient_age",
            "patient_gender",
            "notes",
        )

    def validate_units_requested(self, value):
        if value <= 0:
            raise serializers.ValidationError("Requested units must be at least 1.")
        return value
