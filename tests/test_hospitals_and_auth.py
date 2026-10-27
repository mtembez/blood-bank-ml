import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.hospitals.models import Hospital


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def hospital(db):
    return Hospital.objects.create(
        name="Kenyatta National Hospital",
        code="KNH-001",
        tier=Hospital.TIER_LEVEL_6,
        latitude=-1.301389,
        longitude=36.807222,
        contact_email="emergency@knh.or.ke",
        contact_phone="+254700000001",
    )


@pytest.mark.django_db
class TestHospitalRegistrationAndAuth:
    def test_register_hospital_generates_api_key(self, api_client):
        url = reverse("hospitals:register")
        payload = {
            "name": "Moi Teaching & Referral Hospital",
            "code": "MTRH-ELD-01",
            "tier": "level_6",
            "latitude": 0.514277,
            "longitude": 35.269780,
            "contact_email": "bloodbank@mtrh.go.ke",
            "contact_phone": "+254711000002",
        }
        res = api_client.post(url, payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        data = res.json()
        assert "api_key" in data
        assert len(data["api_key"]) == 64
        assert data["hospital"]["code"] == "MTRH-ELD-01"

    def test_duplicate_hospital_code_rejected(self, api_client, hospital):
        url = reverse("hospitals:register")
        payload = {
            "name": "KNH Duplicate Branch",
            "code": "KNH-001",
            "tier": "level_4",
            "latitude": -1.3000,
            "longitude": 36.8000,
            "contact_email": "dup@knh.or.ke",
            "contact_phone": "+254700000002",
        }
        res = api_client.post(url, payload, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "code" in res.json()

    def test_hospital_profile_with_valid_api_key(self, api_client, hospital):
        url = reverse("hospitals:profile")
        api_client.credentials(HTTP_X_HOSPITAL_API_KEY=hospital.api_key)
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["id"] == str(hospital.id)
        assert res.json()["name"] == "Kenyatta National Hospital"

    def test_hospital_profile_unauthenticated(self, api_client):
        url = reverse("hospitals:profile")
        res = api_client.get(url)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_hospital_profile_invalid_api_key(self, api_client):
        url = reverse("hospitals:profile")
        api_client.credentials(HTTP_X_HOSPITAL_API_KEY="invalid-nonexistent-api-key")
        res = api_client.get(url)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_hospital_profile_suspended_account(self, api_client, hospital):
        hospital.is_active = False
        hospital.save(update_fields=["is_active"])

        url = reverse("hospitals:profile")
        api_client.credentials(HTTP_X_HOSPITAL_API_KEY=hospital.api_key)
        res = api_client.get(url)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED
