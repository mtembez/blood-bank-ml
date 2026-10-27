from rest_framework import generics, permissions, status
from rest_framework.response import Response
from apps.hospitals.authentication import IsAuthenticatedHospital
from apps.hospitals.models import Hospital
from apps.hospitals.serializers import HospitalSerializer, RegisterHospitalSerializer


class RegisterHospitalView(generics.CreateAPIView):
    """Register a new partner hospital and issue an API key."""

    queryset = Hospital.objects.all()
    serializer_class = RegisterHospitalSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hospital = serializer.save()

        return Response(
            {
                "message": "Hospital registered successfully.",
                "hospital": HospitalSerializer(hospital).data,
                "api_key": hospital.api_key,
                "instructions": "Store this API key securely and provide it in the 'X-Hospital-API-Key' header.",
            },
            status=status.HTTP_201_CREATED,
        )


class HospitalProfileView(generics.RetrieveAPIView):
    """Retrieve profile of the authenticated hospital."""

    serializer_class = HospitalSerializer
    permission_classes = (IsAuthenticatedHospital,)

    def get_object(self):
        return self.request.user
