from datetime import date
from decimal import Decimal
import pytest
from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.donors.models import DonationHistory, Donor
from apps.donors.spatial import find_nearby_donors, haversine_distance_km


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def sample_donors(db):
    # Nairobi coordinates: -1.2921, 36.8219
    # Donor 1: Upper Hill (~2 km)
    d1 = Donor.objects.create(
        national_id="ID-1001",
        first_name="John",
        last_name="Kamau",
        phone="+254711111111",
        blood_group="O-",
        age=28,
        gender="male",
        weight_kg=68.5,
        hemoglobin_level=15.2,
        systolic_bp=120,
        diastolic_bp=80,
        latitude=-1.2990,
        longitude=36.8160,
        is_eligible=True,
        donation_count=5,
    )
    # Donor 2: Westlands (~5 km)
    d2 = Donor.objects.create(
        national_id="ID-1002",
        first_name="Faith",
        last_name="Wanjiku",
        phone="+254722222222",
        blood_group="A+",
        age=32,
        gender="female",
        weight_kg=58.0,
        hemoglobin_level=13.8,
        systolic_bp=118,
        diastolic_bp=78,
        latitude=-1.2650,
        longitude=36.8040,
        is_eligible=True,
        donation_count=3,
    )
    # Donor 3: Thika Town (~45 km away)
    d3 = Donor.objects.create(
        national_id="ID-1003",
        first_name="Peter",
        last_name="Otieno",
        phone="+254733333333",
        blood_group="O+",
        age=40,
        gender="male",
        weight_kg=75.0,
        hemoglobin_level=14.5,
        systolic_bp=125,
        diastolic_bp=82,
        latitude=-1.0333,
        longitude=37.0694,
        is_eligible=True,
        donation_count=1,
    )
    return d1, d2, d3


@pytest.mark.django_db
class TestDonorConstraintsAndSpatial:
    def test_donor_underweight_rejected_by_db_constraint(self):
        with pytest.raises(IntegrityError):
            Donor.objects.create(
                national_id="ID-FAIL-1",
                first_name="Under",
                last_name="Weight",
                phone="+254700000099",
                blood_group="B+",
                age=25,
                gender="female",
                weight_kg=45.0,  # Below 50.0kg constraint
                hemoglobin_level=14.0,
                latitude=-1.2921,
                longitude=36.8219,
            )

    def test_donor_age_eligibility_constraint(self):
        with pytest.raises(IntegrityError):
            Donor.objects.create(
                national_id="ID-FAIL-2",
                first_name="Too",
                last_name="Young",
                phone="+254700000098",
                blood_group="B+",
                age=15,  # Below 16
                gender="male",
                weight_kg=55.0,
                hemoglobin_level=14.0,
                latitude=-1.2921,
                longitude=36.8219,
            )

    def test_haversine_distance_calculation(self):
        # Distance from Nairobi (-1.2921, 36.8219) to Upper Hill (-1.2990, 36.8160)
        dist = haversine_distance_km(-1.2921, 36.8219, -1.2990, 36.8160)
        assert 0.5 < dist < 2.0

    def test_find_nearby_donors_radius_filter(self, sample_donors):
        d1, d2, d3 = sample_donors
        nairobi_lat = -1.2921
        nairobi_lon = 36.8219

        # Search within 10 km: should find d1 (Upper Hill) and d2 (Westlands), but NOT d3 (Thika 45km)
        close_donors = find_nearby_donors(nairobi_lat, nairobi_lon, radius_km=10.0)
        ids = [str(d.id) for d in close_donors]
        assert str(d1.id) in ids
        assert str(d2.id) in ids
        assert str(d3.id) not in ids

        # Order must be strictly closest first
        assert close_donors[0].distance_km <= close_donors[1].distance_km

        # Search within 60 km: should include d3
        all_nearby = find_nearby_donors(nairobi_lat, nairobi_lon, radius_km=60.0)
        all_ids = [str(d.id) for d in all_nearby]
        assert str(d3.id) in all_ids

    def test_nearby_donors_api_endpoint(self, api_client, sample_donors):
        url = reverse("donors:nearby-donors")
        res = api_client.get(
            url,
            {"latitude": "-1.2921", "longitude": "36.8219", "radius_km": "10.0"},
        )
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["count"] == 2
        assert "donors" in data
        assert all("distance_km" in d for d in data["donors"])
