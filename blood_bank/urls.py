"""Root URL configuration for blood_bank."""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({
        "status": "healthy",
        "service": "blood-bank-ml",
        "version": "1.0.0",
    })

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health", health_check, name="health-check"),
    path("api/v1/hospitals/", include("apps.hospitals.urls")),
    path("api/v1/donors/", include("apps.donors.urls")),
    path("api/v1/inventory/", include("apps.inventory.urls")),
    path("api/v1/requests/", include("apps.requests.urls")),
    path("api/v1/audit/", include("apps.audit.urls")),
]
