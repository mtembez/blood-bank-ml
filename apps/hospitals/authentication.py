from rest_framework import authentication, exceptions, permissions
from apps.hospitals.models import Hospital


class HospitalAPIKeyAuthentication(authentication.BaseAuthentication):
    """Hospital API Key authentication scheme.

    Expects header 'X-Hospital-API-Key: <key>' or 'Authorization: ApiKey <key>'.
    """

    def authenticate_header(self, request):
        return 'ApiKey realm="hospital-api"'

    def authenticate(self, request):
        api_key = request.headers.get("X-Hospital-API-Key")

        if not api_key:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("ApiKey "):
                api_key = auth_header[7:].strip()

        if not api_key:
            return None

        try:
            hospital = Hospital.objects.get(api_key=api_key)
        except Hospital.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid hospital API key.")

        if not hospital.is_active:
            raise exceptions.AuthenticationFailed("Hospital account is suspended or inactive.")

        # In DRF, request.user is set to hospital and request.auth to api_key
        return (hospital, api_key)


class IsAuthenticatedHospital(permissions.BasePermission):
    """Permission class requiring a valid Hospital instance as request.user."""

    def has_permission(self, request, view):
        return bool(
            request.user and isinstance(request.user, Hospital) and request.user.is_active
        )
