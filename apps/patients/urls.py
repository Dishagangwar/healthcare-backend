from django.urls import path

from .views import PatientDetailView, PatientListCreateView

app_name = "patients"

urlpatterns = [
    path("", PatientListCreateView.as_view(), name="patient-list-create"),
    path("<int:pk>/", PatientDetailView.as_view(), name="patient-detail"),
]
