from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.donors.models import Donor
from apps.donors.serializers import DonorSerializer, NearbyDonorSerializer
from apps.donors.spatial import find_nearby_donors


class DonorListCreateView(generics.ListCreateAPIView):
    """List donors or register a new voluntary donor."""

    queryset = Donor.objects.all().prefetch_related("donation_history")
    serializer_class = DonorSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        qs = super().get_queryset()
        blood_group = self.request.query_params.get("blood_group")
        if blood_group:
            qs = qs.filter(blood_group=blood_group.strip().upper())
        eligible_only = self.request.query_params.get("eligible_only")
        if eligible_only in ("true", "1", "True"):
            qs = qs.filter(is_eligible=True)
        return qs


class DonorDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve or update donor medical & screening records."""

    queryset = Donor.objects.all().prefetch_related("donation_history")
    serializer_class = DonorSerializer
    permission_classes = (permissions.AllowAny,)


class NearbyDonorsView(APIView):
    """Perform radius-based geospatial donor lookup using PostGIS / Haversine."""

    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        lat = request.query_params.get("latitude")
        lon = request.query_params.get("longitude")
        radius_km = request.query_params.get("radius_km", 25.0)
        blood_group = request.query_params.get("blood_group")
        eligible_only = request.query_params.get("eligible_only", "true").lower() in ("true", "1")

        if not lat or not lon:
            return Response(
                {"error": "Both 'latitude' and 'longitude' query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lat = float(lat)
            lon = float(lon)
            radius_km = float(radius_km)
        except ValueError:
            return Response(
                {"error": "Invalid coordinates or radius values."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        donors = find_nearby_donors(
            latitude=lat,
            longitude=lon,
            radius_km=radius_km,
            blood_group=blood_group.strip().upper() if blood_group else None,
            eligible_only=eligible_only,
        )

        serializer = NearbyDonorSerializer(donors, many=True)
        return Response(
            {
                "query": {
                    "latitude": lat,
                    "longitude": lon,
                    "radius_km": radius_km,
                    "blood_group": blood_group,
                },
                "count": len(donors),
                "donors": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
