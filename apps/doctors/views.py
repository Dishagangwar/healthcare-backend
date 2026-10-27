from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from core.mixins import StandardResponseMixin
from core.permissions import IsOwner

from .models import Doctor
from .serializers import DoctorSerializer


class DoctorBaseView(StandardResponseMixin, generics.GenericAPIView):
    serializer_class = DoctorSerializer
    resource_name = "Doctor"
    owner_field = "created_by"

    def get_queryset(self):
        """The directory is shared: every authenticated user reads all doctors."""
        return Doctor.objects.all().select_related("created_by")


class DoctorListCreateView(DoctorBaseView, generics.ListCreateAPIView):
    """GET /api/doctors/ - every doctor in the directory.
    POST /api/doctors/ - add a doctor."""

    permission_classes = [IsAuthenticated]
    filterset_fields = ["specialization", "is_available"]
    search_fields = ["full_name", "specialization", "license_number", "email"]
    ordering_fields = ["created_at", "full_name", "years_of_experience", "consultation_fee"]


class DoctorDetailView(DoctorBaseView, generics.RetrieveUpdateDestroyAPIView):
    """GET / PUT / PATCH / DELETE /api/doctors/<id>/

    Reads are open to any authenticated user; writes are limited to the user
    who added the record.
    """

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAuthenticated(), IsOwner()]
        return [IsAuthenticated()]
