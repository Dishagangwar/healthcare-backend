from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from core.mixins import StandardResponseMixin
from core.permissions import IsOwner
from core.schema import is_schema_generation

from .models import Patient
from .serializers import PatientSerializer


class PatientBaseView(StandardResponseMixin, generics.GenericAPIView):
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    resource_name = "Patient"
    owner_field = "created_by"

    def get_queryset(self):
        """Scoped to the caller: a user never sees another user's patients."""
        if is_schema_generation(self):
            return Patient.objects.none()
        return (
            Patient.objects.filter(created_by=self.request.user)
            .select_related("created_by")
            .prefetch_related("doctor_mappings__doctor")
        )


class PatientListCreateView(PatientBaseView, generics.ListCreateAPIView):
    """GET /api/patients/ - the caller's patients.
    POST /api/patients/ - register a new patient."""

    filterset_fields = ["gender", "blood_group", "is_active"]
    search_fields = ["full_name", "phone", "email"]
    ordering_fields = ["created_at", "full_name", "date_of_birth"]


class PatientDetailView(PatientBaseView, generics.RetrieveUpdateDestroyAPIView):
    """GET / PUT / PATCH / DELETE /api/patients/<id>/"""
