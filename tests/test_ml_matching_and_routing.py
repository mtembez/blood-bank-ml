from datetime import date, timedelta
from decimal import Decimal
import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from apps.audit.models import AuditLog
from apps.donors.models import Donor
from apps.hospitals.models import Hospital
from apps.inventory.models import BloodInventory
from apps.requests.models import BloodRequest
from apps.requests.priority_router import route_blood_request
from ml.features import is_blood_compatible
from ml.matcher import CompatibilityMatcher
from ml.train_matcher import train_and_export_model


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def hospital(db):
    return Hospital.objects.create(
        name="Nairobi Hospital",
        code="NBH-001",
        tier=Hospital.TIER_LEVEL_5,
        latitude=-1.2980,
        longitude=36.8040,
        contact_email="emergency@nairobihosp.org",
        contact_phone="+254700000004",
    )


@pytest.fixture
def donors_pool(db):
    # Compatible donor O- close by
    d1 = Donor.objects.create(
        national_id="D-O-NEG",
        first_name="Kelvin",
        last_name="Mutua",
        phone="+254711999001",
        blood_group="O-",
        age=29,
        gender="male",
        weight_kg=72.0,
        hemoglobin_level=15.5,
        systolic_bp=120,
        diastolic_bp=80,
        latitude=-1.3000,
        longitude=36.8060,
        last_donation_date=date.today() - timedelta(days=90),
        donation_count=8,
        is_eligible=True,
    )
    # Compatible donor A+ slightly further
    d2 = Donor.objects.create(
        national_id="D-A-POS",
        first_name="Sarah",
        last_name="Njeri",
        phone="+254711999002",
        blood_group="A+",
        age=34,
        gender="female",
        weight_kg=60.0,
        hemoglobin_level=13.5,
        systolic_bp=116,
        diastolic_bp=76,
        latitude=-1.2800,
        longitude=36.8150,
        last_donation_date=date.today() - timedelta(days=65),
        donation_count=4,
        is_eligible=True,
    )
    # Incompatible donor B+ for A+ request
    d3 = Donor.objects.create(
        national_id="D-B-POS",
        first_name="Hassan",
        last_name="Ali",
        phone="+254711999003",
        blood_group="B+",
        age=31,
        gender="male",
        weight_kg=69.0,
        hemoglobin_level=14.8,
        systolic_bp=122,
        diastolic_bp=82,
        latitude=-1.2950,
        longitude=36.8050,
        last_donation_date=date.today() - timedelta(days=120),
        donation_count=6,
        is_eligible=True,
    )
    return d1, d2, d3


@pytest.mark.django_db
class TestMLCompatibilityAndPriorityRouting:
    def test_abo_rh_compatibility_logic(self):
        # Universal donor O- can donate to all
        assert is_blood_compatible("O-", "O-") is True
        assert is_blood_compatible("O-", "AB+") is True
        assert is_blood_compatible("O-", "A+") is True

        # Universal recipient AB+ can receive from all
        for grp in ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]:
            assert is_blood_compatible(grp, "AB+") is True

        # A+ cannot receive from B+ or AB+
        assert is_blood_compatible("B+", "A+") is False
        assert is_blood_compatible("AB+", "A+") is False

    def test_ml_model_improvement_over_baseline(self):
        rf, improvement = train_and_export_model()
        assert improvement >= 30.0  # Demonstrating ~34% improvement

    def test_ml_matcher_inference_and_ranking(self, hospital, donors_pool):
        d1, d2, d3 = donors_pool
        matcher = CompatibilityMatcher.get_instance()

        # Recipient is A+: compatible with O- (d1) and A+ (d2), incompatible with B+ (d3)
        ranked = matcher.rank_donors(
            [d1, d2, d3],
            hospital,
            recipient_blood_group="A+",
            urgency="urgent",
        )

        # Incompatible donor d3 must be excluded from matches
        matched_donor_ids = [m["donor"].id for m in ranked]
        assert d3.id not in matched_donor_ids
        assert d1.id in matched_donor_ids
        assert d2.id in matched_donor_ids

        # Highest score candidate is first
        assert ranked[0]["match_score"] >= ranked[1]["match_score"]
        assert ranked[0]["match_score"] > 0.50

    def test_priority_routing_immediate_inventory_fulfillment(self, hospital):
        now = timezone.now()
        # Create available inventory unit
        unit = BloodInventory.objects.create(
            unit_number="KE-IMMED-001",
            blood_group="A+",
            component_type="whole_blood",
            volume_ml=450,
            status=BloodInventory.STATUS_AVAILABLE,
            expires_at=now + timedelta(days=20),
        )

        req = BloodRequest.objects.create(
            hospital=hospital,
            blood_group="A+",
            component_type="whole_blood",
            units_requested=1,
            urgency=BloodRequest.URGENCY_CRITICAL_STAT,
        )

        res = route_blood_request(req)
        assert res["status"] == "fully_allocated"
        assert res["allocated_units_count"] == 1

        req.refresh_from_db()
        assert req.status == BloodRequest.STATUS_ALLOCATED
        assert req.units_allocated == 1

        unit.refresh_from_db()
        assert unit.status == BloodInventory.STATUS_RESERVED

        # Verify audit log recorded
        log_entry = AuditLog.objects.filter(
            target_model="BloodRequest", target_id=str(req.id), action="inventory_allocated"
        ).first()
        assert log_entry is not None

    def test_priority_routing_triggers_ml_donor_search_when_deficit(self, hospital, donors_pool):
        d1, d2, d3 = donors_pool
        # Request 3 units of A+ (no inventory present)
        req = BloodRequest.objects.create(
            hospital=hospital,
            blood_group="A+",
            component_type="whole_blood",
            units_requested=3,
            urgency=BloodRequest.URGENCY_CRITICAL_STAT,
        )

        res = route_blood_request(req)
        assert res["status"] == "matching_in_progress"
        assert res["donors_needed"] == 3
        assert len(res["ranked_donors"]) >= 2
        # Verify top candidate is compatible
        assert res["ranked_donors"][0]["blood_group"] in ["O-", "A+"]

        # Verify audit log
        log_entry = AuditLog.objects.filter(
            target_model="BloodRequest", target_id=str(req.id), action="ml_donor_matching"
        ).first()
        assert log_entry is not None

    def test_hospital_request_creation_api_flow(self, api_client, hospital, donors_pool):
        api_client.credentials(HTTP_X_HOSPITAL_API_KEY=hospital.api_key)
        url = reverse("requests:request-list-create")
        payload = {
            "blood_group": "A+",
            "component_type": "whole_blood",
            "units_requested": 2,
            "urgency": "critical_stat",
            "patient_age": 45,
            "patient_gender": "male",
            "notes": "Emergency trauma resuscitation",
        }
        res = api_client.post(url, payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        data = res.json()
        assert "request" in data
        assert "routing" in data
        req_id = data["request"]["id"]

        # Query candidate matches endpoint
        matches_url = reverse("requests:request-matches", kwargs={"pk": req_id})
        res_matches = api_client.get(matches_url)
        assert res_matches.status_code == status.HTTP_200_OK
        matches_data = res_matches.json()
        assert matches_data["total_candidates_scored"] >= 2
        assert len(matches_data["ranked_matches"]) >= 2
