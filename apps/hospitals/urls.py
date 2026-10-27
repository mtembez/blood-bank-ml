from django.urls import path
from apps.hospitals.views import HospitalProfileView, RegisterHospitalView

app_name = "hospitals"

urlpatterns = [
    path("register", RegisterHospitalView.as_view(), name="register"),
    path("profile", HospitalProfileView.as_view(), name="profile"),
]
