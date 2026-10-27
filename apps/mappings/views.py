from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.patients.models import Patient
from core.mixins import StandardResponseMixin

from .models import PatientDoctorMapping
from .serializers import PatientDoctorMappingSerializer


class MappingBaseView(generics.GenericAPIView):
    serializer_class = PatientDoctorMappingSerializer
    permission_classes = [IsAuthenticated]
    owner_field = "created_by"

    def get_queryset(self):
        """Mappings are scoped to the patients the caller owns."""
        return (
            PatientDoctorMapping.objects.filter(patient__created_by=self.request.user)
            .select_related("patient", "doctor", "created_by")
        )


class MappingListCreateView(StandardResponseMixin, MappingBaseView, generics.ListCreateAPIView):
    """GET /api/mappings/ - every mapping across the caller's patients.
    POST /api/mappings/ - assign a doctor to a patient."""

    resource_name = "Doctor assignment"
    filterset_fields = ["patient", "doctor", "is_primary"]
    ordering_fields = ["created_at"]


class PatientMappingsView(MappingBaseView):
    """GET /api/mappings/<patient_id>/ - doctors assigned to one patient.
    DELETE /api/mappings/<id>/ - remove one assignment.

    The assignment specifies these two operations on the same path, so the
    path parameter is read as a patient id on GET and as a mapping id on
    DELETE. `/api/mappings/by-patient/<patient_id>/` and
    `/api/mappings/assignment/<id>/` address each one unambiguously.
    """

    def get(self, request, pk):
        patient = get_object_or_404(
            Patient.objects.filter(created_by=request.user), pk=pk
        )
        mappings = self.get_queryset().filter(patient=patient)
        return Response(
            {
                "success": True,
                "data": {
                    "patient": {"id": patient.id, "full_name": patient.full_name},
                    "count": mappings.count(),
                    "doctors": self.get_serializer(mappings, many=True).data,
                },
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        mapping = get_object_or_404(self.get_queryset(), pk=pk)
        mapping.delete()
        return Response(
            {"success": True, "message": "Doctor removed from patient successfully."},
            status=status.HTTP_200_OK,
        )


class MappingAssignmentView(StandardResponseMixin, MappingBaseView,
                            generics.RetrieveUpdateDestroyAPIView):
    """GET / PUT / PATCH / DELETE /api/mappings/assignment/<id>/ - one assignment."""

    resource_name = "Doctor assignment"
