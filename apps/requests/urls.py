from django.urls import path
from apps.requests.views import (
    BloodRequestAllocateView,
    BloodRequestDetailView,
    BloodRequestListCreateView,
    BloodRequestMatchesView,
)

app_name = "requests"

urlpatterns = [
    path("", BloodRequestListCreateView.as_view(), name="request-list-create"),
    path("<uuid:pk>", BloodRequestDetailView.as_view(), name="request-detail"),
    path("<uuid:pk>/matches", BloodRequestMatchesView.as_view(), name="request-matches"),
    path("<uuid:pk>/allocate", BloodRequestAllocateView.as_view(), name="request-allocate"),
]
