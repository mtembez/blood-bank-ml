from datetime import timedelta
import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from apps.hospitals.models import Hospital
from apps.inventory.models import BloodInventory
from apps.requests.models import BloodRequest, RequestAllocation


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def hospital(db):
    return Hospital.objects.create(
        name="Aga Khan University Hospital",
        code="AKUH-001",
        tier=Hospital.TIER_LEVEL_5,
        latitude=-1.2619,
        longitude=36.8242,
        contact_email="blood@aku.edu",
        contact_phone="+254700000003",
    )


@pytest.fixture
def sample_inventory(db):
    now = timezone.now()
    u1 = BloodInventory.objects.create(
        unit_number="KE-AKU-2026-001",
        blood_group="O+",
        component_type="whole_blood",
        volume_ml=450,
        status=BloodInventory.STATUS_AVAILABLE,
        collected_at=now - timedelta(days=2),
        expires_at=now + timedelta(days=33),
    )
    u2 = BloodInventory.objects.create(
        unit_number="KE-AKU-2026-002",
        blood_group="O+",
        component_type="whole_blood",
        volume_ml=450,
        status=BloodInventory.STATUS_AVAILABLE,
        collected_at=now - timedelta(days=5),
        expires_at=now + timedelta(days=30),
    )
    u3 = BloodInventory.objects.create(
        unit_number="KE-AKU-2026-003",
        blood_group="A-",
        component_type="platelets",
        volume_ml=250,
        status=BloodInventory.STATUS_AVAILABLE,
        collected_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=4),
    )
    return u1, u2, u3


@pytest.mark.django_db
class TestInventoryManagement:
    def test_inventory_summary_endpoint(self, api_client, sample_inventory):
        url = reverse("inventory:inventory-summary")
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["total_available_units"] == 3
        assert len(data["breakdown"]) >= 2

    def test_manual_allocation_to_blood_request(self, api_client, hospital, sample_inventory):
        u1, u2, u3 = sample_inventory
        api_client.credentials(HTTP_X_HOSPITAL_API_KEY=hospital.api_key)

        # Create request for 1 unit of O+
        req = BloodRequest.objects.create(
            hospital=hospital,
            blood_group="O+",
            component_type="whole_blood",
            units_requested=1,
            urgency=BloodRequest.URGENCY_URGENT,
        )

        url = reverse("requests:request-allocate", kwargs={"pk": req.id})
        res = api_client.post(url, {"inventory_unit_id": str(u1.id)}, format="json")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()

        # Verify unit status changed to reserved
        u1.refresh_from_db()
        assert u1.status == BloodInventory.STATUS_RESERVED

        # Verify request marked allocated
        req.refresh_from_db()
        assert req.units_allocated == 1
        assert req.status == BloodRequest.STATUS_ALLOCATED

        # Attempting to allocate already reserved unit must fail
        res_fail = api_client.post(url, {"inventory_unit_id": str(u1.id)}, format="json")
        assert res_fail.status_code == status.HTTP_400_BAD_REQUEST
