from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinLengthValidator, MinValueValidator
from django.db import models

from core.models import TimeStampedModel
from core.validators import PHONE_VALIDATOR


class Doctor(TimeStampedModel):
    """A doctor on staff. Visible to every authenticated user."""

    class Specialization(models.TextChoices):
        GENERAL = "GENERAL_PRACTICE", "General Practice"
        CARDIOLOGY = "CARDIOLOGY", "Cardiology"
        DERMATOLOGY = "DERMATOLOGY", "Dermatology"
        ENDOCRINOLOGY = "ENDOCRINOLOGY", "Endocrinology"
        GASTROENTEROLOGY = "GASTROENTEROLOGY", "Gastroenterology"
        NEUROLOGY = "NEUROLOGY", "Neurology"
        ONCOLOGY = "ONCOLOGY", "Oncology"
        ORTHOPAEDICS = "ORTHOPAEDICS", "Orthopaedics"
        PAEDIATRICS = "PAEDIATRICS", "Paediatrics"
        PSYCHIATRY = "PSYCHIATRY", "Psychiatry"
        PULMONOLOGY = "PULMONOLOGY", "Pulmonology"
        RADIOLOGY = "RADIOLOGY", "Radiology"
        SURGERY = "SURGERY", "Surgery"
        UROLOGY = "UROLOGY", "Urology"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctors",
        help_text="The user who added this doctor to the directory.",
    )
    full_name = models.CharField(max_length=150, validators=[MinLengthValidator(2)])
    specialization = models.CharField(max_length=32, choices=Specialization.choices)
    license_number = models.CharField(
        max_length=32,
        unique=True,
        help_text="Medical council registration number; unique across the directory.",
    )
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=16, validators=[PHONE_VALIDATOR])
    years_of_experience = models.PositiveIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(70)]
    )
    consultation_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    is_available = models.BooleanField(
        default=True, help_text="Whether the doctor is currently accepting patients."
    )

    class Meta(TimeStampedModel.Meta):
        indexes = [models.Index(fields=["specialization", "is_available"])]

    def __str__(self):
        return f"Dr. {self.full_name} - {self.get_specialization_display()}"
