from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.patients.models import Patient
from core.mixins import StandardResponseMixin
from core.schema import error_response, is_schema_generation

from .models import PatientDoctorMapping
from .serializers import (
    MappingDeletedSerializer,
    PatientDoctorMappingSerializer,
    PatientDoctorsResponseSerializer,
)


class MappingBaseView(generics.GenericAPIView):
    serializer_class = PatientDoctorMappingSerializer
    permission_classes = [IsAuthenticated]
    owner_field = "created_by"

    def get_queryset(self):
        """Mappings are scoped to the patients the caller owns."""
        if is_schema_generation(self):
            return PatientDoctorMapping.objects.none()
        return (
            PatientDoctorMapping.objects.filter(patient__created_by=self.request.user)
            .select_related("patient", "doctor", "created_by")
        )


@extend_schema_view(
    get=extend_schema(
        tags=["mappings"],
        summary="List every assignment for the caller's patients",
    ),
    post=extend_schema(
        tags=["mappings"],
        summary="Assign a doctor to a patient",
        description=(
            "A patient may have several doctors and a doctor many patients. The "
            "same doctor cannot be assigned to the same patient twice, and a "
            "patient may have at most one `is_primary` doctor.\n\n"
            "Assigning to a patient the caller does not own is rejected."
        ),
    ),
)
class MappingListCreateView(StandardResponseMixin, MappingBaseView, generics.ListCreateAPIView):
    """GET /api/mappings/ - every mapping across the caller's patients.
    POST /api/mappings/ - assign a doctor to a patient."""

    resource_name = "Doctor assignment"
    filterset_fields = ["patient", "doctor", "is_primary"]
    ordering_fields = ["created_at"]


@extend_schema_view(
    get=extend_schema(
        tags=["mappings"],
        summary="List the doctors assigned to one patient",
        description=(
            "**The path parameter here is a patient id.** The assignment spec puts "
            "this operation and the delete below on the same path, so the id is "
            "read as a patient on `GET` and as an assignment on `DELETE`. "
            "`/api/mappings/by-patient/{id}/` is the unambiguous equivalent."
        ),
        parameters=[
            OpenApiParameter(
                "id", int, OpenApiParameter.PATH,
                description="Patient id (not an assignment id).",
            )
        ],
        responses={
            200: OpenApiResponse(PatientDoctorsResponseSerializer,
                                 description="The patient and their assigned doctors."),
            401: error_response("401"),
            404: error_response("404"),
        },
    ),
    delete=extend_schema(
        tags=["mappings"],
        summary="Remove a doctor from a patient",
        description=(
            "**The path parameter here is an assignment id**, as returned by "
            "`POST /api/mappings/`. `/api/mappings/assignment/{id}/` is the "
            "unambiguous equivalent."
        ),
        parameters=[
            OpenApiParameter(
                "id", int, OpenApiParameter.PATH,
                description="Assignment (mapping) id, not a patient id.",
            )
        ],
        responses={
            200: OpenApiResponse(MappingDeletedSerializer, description="Assignment removed."),
            401: error_response("401"),
            404: error_response("404"),
        },
    ),
)
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


@extend_schema(tags=["mappings"])
class MappingAssignmentView(StandardResponseMixin, MappingBaseView,
                            generics.RetrieveUpdateDestroyAPIView):
    """GET / PUT / PATCH / DELETE /api/mappings/assignment/<id>/ - one assignment."""

    resource_name = "Doctor assignment"
