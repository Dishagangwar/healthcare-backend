from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from apps.doctors.models import Doctor
from apps.doctors.serializers import DoctorSerializer
from apps.patients.models import Patient

from .models import PatientDoctorMapping


class PatientDoctorMappingSerializer(serializers.ModelSerializer):
    # Writable ids in, readable nested objects out.
    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all())
    doctor = serializers.PrimaryKeyRelatedField(queryset=Doctor.objects.all())
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    doctor_detail = DoctorSerializer(source="doctor", read_only=True)

    class Meta:
        model = PatientDoctorMapping
        fields = [
            "id",
            "patient",
            "patient_name",
            "doctor",
            "doctor_detail",
            "notes",
            "is_primary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        # Declared explicitly so the duplicate message is phrased for the
        # client; an explicit list also replaces DRF's generated validators.
        validators = [
            UniqueTogetherValidator(
                queryset=PatientDoctorMapping.objects.all(),
                fields=["patient", "doctor"],
                message="This doctor is already assigned to this patient.",
            )
        ]

    def validate_patient(self, value):
        """Only the owner of a patient record may assign doctors to it."""
        request = self.context["request"]
        if value.created_by_id != request.user.id:
            raise serializers.ValidationError(
                "No patient with this id exists in your records."
            )
        return value

    def validate(self, attrs):
        patient = attrs.get("patient") or getattr(self.instance, "patient", None)

        # Mirrors the DB constraint, so the client gets a field error instead
        # of a 409 from the database.
        if attrs.get("is_primary"):
            existing_primary = PatientDoctorMapping.objects.filter(
                patient=patient, is_primary=True
            )
            if self.instance is not None:
                existing_primary = existing_primary.exclude(pk=self.instance.pk)
            if existing_primary.exists():
                raise serializers.ValidationError(
                    {
                        "is_primary": "This patient already has a primary doctor. "
                        "Unset the current one first."
                    }
                )
        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


# ---------------------------------------------------------------------------
# Documentation-only serializers
#
# PatientMappingsView assembles its response by hand, so these describe what it
# actually returns. Nothing renders through them.
# ---------------------------------------------------------------------------


class PatientSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()


class PatientDoctorsPayloadSerializer(serializers.Serializer):
    patient = PatientSummarySerializer()
    count = serializers.IntegerField(help_text="Number of doctors assigned to this patient.")
    doctors = PatientDoctorMappingSerializer(many=True)


class PatientDoctorsResponseSerializer(serializers.Serializer):
    """Shape of GET /api/mappings/<patient_id>/."""

    success = serializers.BooleanField(default=True)
    data = PatientDoctorsPayloadSerializer()


class MappingDeletedSerializer(serializers.Serializer):
    """Shape of DELETE /api/mappings/<id>/."""

    success = serializers.BooleanField(default=True)
    message = serializers.CharField(default="Doctor removed from patient successfully.")
