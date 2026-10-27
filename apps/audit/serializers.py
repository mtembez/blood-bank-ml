from rest_framework import generics, permissions, serializers
from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = (
            "id",
            "actor_type",
            "actor_id",
            "action",
            "target_model",
            "target_id",
            "details",
            "ip_address",
            "timestamp",
        )
        read_only_fields = fields


class AuditLogListView(generics.ListAPIView):
    """Query immutable audit trails with optional actor and target filters."""

    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        qs = super().get_queryset()
        action = self.request.query_params.get("action")
        target_model = self.request.query_params.get("target_model")
        target_id = self.request.query_params.get("target_id")

        if action:
            qs = qs.filter(action=action)
        if target_model:
            qs = qs.filter(target_model=target_model)
        if target_id:
            qs = qs.filter(target_id=target_id)
        return qs
