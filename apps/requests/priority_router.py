import logging
from django.db import transaction
from django.utils import timezone
from apps.audit.service import log_audit_event
from apps.donors.spatial import find_nearby_donors
from apps.inventory.models import BloodInventory
from apps.requests.models import BloodRequest, RequestAllocation
from ml.features import ABO_RH_COMPATIBILITY
from ml.matcher import CompatibilityMatcher

logger = logging.getLogger(__name__)


def route_blood_request(blood_request: BloodRequest) -> dict:
    """Execute priority request routing workflow.

    1. Checks immediately available inventory (FEFO ordering).
    2. If sufficient, performs atomic inventory allocation.
    3. If insufficient, triggers ML matching on nearby eligible donors.
    """
    compatible_groups = ABO_RH_COMPATIBILITY.get(blood_request.blood_group, [blood_request.blood_group])
    needed_units = blood_request.units_requested - blood_request.units_allocated

    # 1. Search available cold-chain inventory (FEFO: First Expired, First Out)
    available_units = list(
        BloodInventory.objects.filter(
            blood_group__in=compatible_groups,
            component_type=blood_request.component_type,
            status=BloodInventory.STATUS_AVAILABLE,
            expires_at__gt=timezone.now(),
        ).order_by("expires_at")[:needed_units]
    )

    allocated_units_data = []

    if available_units:
        with transaction.atomic():
            for unit in available_units:
                unit.status = BloodInventory.STATUS_RESERVED
                unit.save(update_fields=["status", "updated_at"])

                RequestAllocation.objects.create(
                    request=blood_request,
                    inventory_unit=unit,
                )
                allocated_units_data.append({
                    "id": str(unit.id),
                    "unit_number": unit.unit_number,
                    "blood_group": unit.blood_group,
                    "expires_at": unit.expires_at.isoformat(),
                })

            blood_request.units_allocated += len(available_units)
            if blood_request.units_allocated >= blood_request.units_requested:
                blood_request.status = BloodRequest.STATUS_ALLOCATED
            else:
                blood_request.status = BloodRequest.STATUS_MATCHING
            blood_request.save(update_fields=["units_allocated", "status", "updated_at"])

        log_audit_event(
            actor_type="hospital_api",
            actor_id=str(blood_request.hospital.id),
            action="inventory_allocated",
            target_model="BloodRequest",
            target_id=str(blood_request.id),
            details={
                "allocated_count": len(available_units),
                "total_allocated": blood_request.units_allocated,
                "units_requested": blood_request.units_requested,
                "urgency": blood_request.urgency,
            },
        )

    # 2. If deficit remains, run ML donor matching
    remaining_deficit = blood_request.units_requested - blood_request.units_allocated

    if remaining_deficit <= 0:
        return {
            "status": "fully_allocated",
            "allocated_units_count": len(allocated_units_data),
            "allocated_units": allocated_units_data,
            "donors_needed": 0,
            "ranked_donors": [],
        }

    # Urgency-based search radius
    radius_km = 15.0 if blood_request.urgency == BloodRequest.URGENCY_CRITICAL_STAT else 35.0

    # Query nearby eligible donors
    candidate_donors = find_nearby_donors(
        latitude=float(blood_request.hospital.latitude),
        longitude=float(blood_request.hospital.longitude),
        radius_km=radius_km,
        eligible_only=True,
    )

    # Score and rank using Random Forest model
    matcher = CompatibilityMatcher.get_instance()
    ranked_candidates = matcher.rank_donors(
        candidate_donors,
        blood_request.hospital,
        recipient_blood_group=blood_request.blood_group,
        urgency=blood_request.urgency,
    )

    log_audit_event(
        actor_type="priority_router",
        actor_id="system",
        action="ml_donor_matching",
        target_model="BloodRequest",
        target_id=str(blood_request.id),
        details={
            "deficit": remaining_deficit,
            "urgency": blood_request.urgency,
            "candidates_found": len(ranked_candidates),
            "radius_km": radius_km,
        },
    )

    formatted_matches = [
        {
            "donor_id": str(match["donor"].id),
            "name": f"{match['donor'].first_name} {match['donor'].last_name}",
            "blood_group": match["donor"].blood_group,
            "phone": match["donor"].phone,
            "distance_km": match["distance_km"],
            "match_score": match["match_score"],
            "tier": match["tier"],
        }
        for match in ranked_candidates[:10]  # Top 10 matches
    ]

    return {
        "status": "partially_allocated" if allocated_units_data else "matching_in_progress",
        "allocated_units_count": len(allocated_units_data),
        "allocated_units": allocated_units_data,
        "donors_needed": remaining_deficit,
        "ranked_donors": formatted_matches,
    }
