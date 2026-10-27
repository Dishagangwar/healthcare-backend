from django.urls import path

from .views import MappingAssignmentView, MappingListCreateView, PatientMappingsView

app_name = "mappings"

urlpatterns = [
    path("", MappingListCreateView.as_view(), name="mapping-list-create"),
    # Unambiguous aliases, registered before the overloaded route below.
    path("by-patient/<int:pk>/", PatientMappingsView.as_view(), name="mappings-by-patient"),
    path("assignment/<int:pk>/", MappingAssignmentView.as_view(), name="mapping-assignment"),
    # Assignment spec: GET reads <patient_id>, DELETE reads <mapping id>.
    path("<int:pk>/", PatientMappingsView.as_view(), name="mapping-detail"),
]
