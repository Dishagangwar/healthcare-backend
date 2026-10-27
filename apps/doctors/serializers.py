from rest_framework import serializers

from core.fields import PhoneNumberField
from core.validators import PHONE_VALIDATOR

from .models import Doctor


class DoctorSerializer(serializers.ModelSerializer):
    phone = PhoneNumberField(max_length=16, validators=[PHONE_VALIDATOR])
    specialization_display = serializers.CharField(
        source="get_specialization_display", read_only=True
    )
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = Doctor
        fields = [
            "id",
            "full_name",
            "specialization",
            "specialization_display",
            "license_number",
            "email",
            "phone",
            "years_of_experience",
            "consultation_fee",
            "is_available",
            "created_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by_email", "created_at", "updated_at"]

    def validate_full_name(self, value):
        name = " ".join(value.split())
        if len(name) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters long.")
        return name

    def validate_license_number(self, value):
        license_number = value.strip().upper()
        clash = Doctor.objects.filter(license_number=license_number)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError(
                "A doctor with this license number is already registered."
            )
        return license_number

    def validate_email(self, value):
        email = value.lower().strip()
        clash = Doctor.objects.filter(email=email)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("A doctor with this email is already registered.")
        return email

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)
