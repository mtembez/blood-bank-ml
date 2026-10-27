from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.audit.service import log_audit_event
from apps.donors.spatial import find_nearby_donors
from apps.hospitals.authentication import IsAuthenticatedHospital
from apps.inventory.models import BloodInventory
from apps.requests.models import BloodRequest, RequestAllocation
from apps.requests.priority_router import route_blood_request
from apps.requests.serializers import BloodRequestSerializer, CreateBloodRequestSerializer
from ml.matcher import CompatibilityMatcher


class BloodRequestListCreateView(generics.ListCreateAPIView):
    """List requests initiated by hospital or submit a new blood unit request."""

    permission_classes = (IsAuthenticatedHospital,)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateBloodRequestSerializer
        return BloodRequestSerializer

    def get_queryset(self):
        return BloodRequest.objects.filter(hospital=self.request.user).prefetch_related("allocations")

    def perform_create(self, serializer):
        return serializer.save(hospital=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        blood_request = self.perform_create(serializer)

        # Log audit entry
        log_audit_event(
            actor_type="hospital_api",
            actor_id=str(request.user.id),
            action="request_created",
            target_model="BloodRequest",
            target_id=str(blood_request.id),
            details={
                "blood_group": blood_request.blood_group,
                "component_type": blood_request.component_type,
                "units_requested": blood_request.units_requested,
                "urgency": blood_request.urgency,
            },
        )

        # Automatically execute priority request routing
        routing_result = route_blood_request(blood_request)

        return Response(
            {
                "request": BloodRequestSerializer(blood_request).data,
                "routing": routing_result,
            },
            status=status.HTTP_201_CREATED,
        )


class BloodRequestDetailView(generics.RetrieveAPIView):
    """Retrieve full request details and current allocation state."""

    permission_classes = (IsAuthenticatedHospital,)
    serializer_class = BloodRequestSerializer

    def get_queryset(self):
        return BloodRequest.objects.filter(hospital=self.request.user).prefetch_related("allocations")


class BloodRequestMatchesView(APIView):
    """Execute ML donor compatibility matching for a specific request."""

    permission_classes = (IsAuthenticatedHospital,)

    def get(self, request, pk):
        blood_request = get_object_or_404(BloodRequest, pk=pk, hospital=request.user)

        radius_km = float(request.query_params.get("radius_km", 30.0))

        candidates = find_nearby_donors(
            latitude=float(blood_request.hospital.latitude),
            longitude=float(blood_request.hospital.longitude),
            radius_km=radius_km,
            eligible_only=True,
        )

        matcher = CompatibilityMatcher.get_instance()
        ranked = matcher.rank_donors(
            candidates,
            blood_request.hospital,
            recipient_blood_group=blood_request.blood_group,
            urgency=blood_request.urgency,
        )

        matches_data = [
            {
                "donor_id": str(m["donor"].id),
                "name": f"{m['donor'].first_name} {m['donor'].last_name}",
                "blood_group": m["donor"].blood_group,
                "phone": m["donor"].phone,
                "distance_km": m["distance_km"],
                "match_score": m["match_score"],
                "tier": m["tier"],
                "clinical_features": m["eval_details"]["clinical_features"],
            }
            for m in ranked
        ]

        return Response(
            {
                "request_id": str(blood_request.id),
                "recipient_blood_group": blood_request.blood_group,
                "urgency": blood_request.urgency,
                "radius_km": radius_km,
                "total_candidates_scored": len(ranked),
                "ranked_matches": matches_data,
            },
            status=status.HTTP_200_OK,
        )


class BloodRequestAllocateView(APIView):
    """Manually allocate a specific inventory unit to a blood request."""

    permission_classes = (IsAuthenticatedHospital,)

    def post(self, request, pk):
        blood_request = get_object_or_404(BloodRequest, pk=pk, hospital=request.user)
        unit_id = request.data.get("inventory_unit_id")

        if not unit_id:
            return Response(
                {"error": "Field 'inventory_unit_id' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        unit = get_object_or_404(BloodInventory, pk=unit_id)

        if unit.status != BloodInventory.STATUS_AVAILABLE:
            return Response(
                {"error": f"Unit {unit.unit_number} is not available (status: {unit.status})."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Allocate
        unit.status = BloodInventory.STATUS_RESERVED
        unit.save(update_fields=["status", "updated_at"])

        allocation, _ = RequestAllocation.objects.get_or_create(
            request=blood_request,
            inventory_unit=unit,
        )

        blood_request.units_allocated += 1
        if blood_request.units_allocated >= blood_request.units_requested:
            blood_request.status = BloodRequest.STATUS_ALLOCATED
        blood_request.save(update_fields=["units_allocated", "status", "updated_at"])

        log_audit_event(
            actor_type="hospital_api",
            actor_id=str(request.user.id),
            action="manual_inventory_allocated",
            target_model="BloodRequest",
            target_id=str(blood_request.id),
            details={"unit_id": str(unit.id), "unit_number": unit.unit_number},
        )

        return Response(
            {
                "message": f"Unit {unit.unit_number} allocated successfully.",
                "request": BloodRequestSerializer(blood_request).data,
            },
            status=status.HTTP_200_OK,
        )
