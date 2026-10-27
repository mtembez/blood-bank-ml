from django.urls import path
from apps.donors.views import DonorDetailView, DonorListCreateView, NearbyDonorsView

app_name = "donors"

urlpatterns = [
    path("", DonorListCreateView.as_view(), name="donor-list-create"),
    path("nearby", NearbyDonorsView.as_view(), name="nearby-donors"),
    path("<uuid:pk>", DonorDetailView.as_view(), name="donor-detail"),
]
