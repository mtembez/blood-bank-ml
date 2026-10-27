from django.urls import path
from apps.audit.serializers import AuditLogListView

app_name = "audit"

urlpatterns = [
    path("logs", AuditLogListView.as_view(), name="audit-logs"),
]
