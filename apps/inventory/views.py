from django.db.models import Count
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.inventory.models import BloodInventory
from apps.inventory.serializers import BloodInventorySerializer


class InventoryListCreateView(generics.ListCreateAPIView):
    """List blood units or record incoming collected inventory."""

    queryset = BloodInventory.objects.all().select_related("donor")
    serializer_class = BloodInventorySerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get("status")
        blood_group = self.request.query_params.get("blood_group")
        component = self.request.query_params.get("component_type")

        if status_param:
            qs = qs.filter(status=status_param)
        if blood_group:
            qs = qs.filter(blood_group=blood_group.strip().upper())
        if component:
            qs = qs.filter(component_type=component)
        return qs


class InventorySummaryView(APIView):
    """Aggregate stock levels broken down by blood group and component type."""

    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        aggregates = (
            BloodInventory.objects.filter(status=BloodInventory.STATUS_AVAILABLE)
            .values("blood_group", "component_type")
            .annotate(total_units=Count("id"))
            .order_by("blood_group", "component_type")
        )

        total_available = BloodInventory.objects.filter(status=BloodInventory.STATUS_AVAILABLE).count()

        return Response(
            {
                "total_available_units": total_available,
                "breakdown": list(aggregates),
            },
            status=status.HTTP_200_OK,
        )
