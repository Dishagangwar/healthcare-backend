from django.utils import timezone
from rest_framework import serializers

from core.fields import PhoneNumberField
from core.validators import PHONE_VALIDATOR

from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    phone = PhoneNumberField(max_length=16, validators=[PHONE_VALIDATOR])
    age = serializers.IntegerField(read_only=True)
    gender_display = serializers.CharField(source="get_gender_display", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id",
            "full_name",
            "date_of_birth",
            "age",
            "gender",
            "gender_display",
            "blood_group",
            "phone",
            "email",
            "address",
            "medical_history",
            "is_active",
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

    def validate_date_of_birth(self, value):
        today = timezone.localdate()
        if value > today:
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        if value.year < today.year - 120:
            raise serializers.ValidationError("Date of birth is not plausible (over 120 years ago).")
        return value

    def validate_phone(self, value):
        """`value` arrives already normalised by PhoneNumberField."""
        phone = value
        request = self.context.get("request")
        if request is not None:
            clash = Patient.objects.filter(created_by=request.user, phone=phone)
            if self.instance is not None:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError(
                    "You already have a patient registered with this phone number."
                )
        return phone

    def validate_email(self, value):
        return value.lower().strip()

    def create(self, validated_data):
       
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)
