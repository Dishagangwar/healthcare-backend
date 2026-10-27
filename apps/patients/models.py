from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel
from core.validators import PHONE_VALIDATOR


class Patient(TimeStampedModel):
    """A patient record, owned by the user who created it."""

    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"
        UNDISCLOSED = "UNDISCLOSED", "Prefer not to say"

    class BloodGroup(models.TextChoices):
        A_POS = "A+", "A+"
        A_NEG = "A-", "A-"
        B_POS = "B+", "B+"
        B_NEG = "B-", "B-"
        AB_POS = "AB+", "AB+"
        AB_NEG = "AB-", "AB-"
        O_POS = "O+", "O+"
        O_NEG = "O-", "O-"
        UNKNOWN = "UNKNOWN", "Unknown"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patients",
        help_text="The user who registered this patient.",
    )
    full_name = models.CharField(max_length=150, validators=[MinLengthValidator(2)])
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=11, choices=Gender.choices)
    blood_group = models.CharField(
        max_length=7, choices=BloodGroup.choices, default=BloodGroup.UNKNOWN
    )
    phone = models.CharField(max_length=16, validators=[PHONE_VALIDATOR])
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    medical_history = models.TextField(
        blank=True, help_text="Known conditions, allergies and prior treatment."
    )
    is_active = models.BooleanField(
        default=True, help_text="Set to false to archive without deleting history."
    )

    class Meta(TimeStampedModel.Meta):
        constraints = [
            # One user cannot register the same person twice on the same phone.
            models.UniqueConstraint(
                fields=["created_by", "phone"], name="unique_patient_phone_per_user"
            ),
        ]
        indexes = [models.Index(fields=["created_by", "full_name"])]

    def __str__(self):
        return f"{self.full_name} ({self.phone})"

    @property
    def age(self):
        """Age in whole years as of today."""
        today = timezone.localdate()
        had_birthday = (today.month, today.day) >= (
            self.date_of_birth.month,
            self.date_of_birth.day,
        )
        return today.year - self.date_of_birth.year - (0 if had_birthday else 1)
