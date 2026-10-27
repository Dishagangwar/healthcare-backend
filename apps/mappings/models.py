from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class PatientDoctorMapping(TimeStampedModel):
    """Assignment of a doctor to a patient.

    A patient may have several doctors and a doctor many patients, so this is
    a through-table with its own metadata rather than a plain M2M.
    """

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="doctor_mappings"
    )
    doctor = models.ForeignKey(
        "doctors.Doctor", on_delete=models.CASCADE, related_name="patient_mappings"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mappings",
        help_text="The user who made this assignment.",
    )
    notes = models.TextField(blank=True, help_text="Reason for referral or care notes.")
    is_primary = models.BooleanField(
        default=False, help_text="Marks the patient's primary physician."
    )

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "doctor"], name="unique_patient_doctor_assignment"
            ),
            # At most one primary doctor per patient. The condition means rows
            # with is_primary=False are exempt from the uniqueness check.
            models.UniqueConstraint(
                fields=["patient"],
                condition=models.Q(is_primary=True),
                name="unique_primary_doctor_per_patient",
            ),
        ]
        indexes = [models.Index(fields=["patient", "doctor"])]
        verbose_name = "patient-doctor mapping"
        verbose_name_plural = "patient-doctor mappings"

    def __str__(self):
        return f"{self.patient.full_name} -> Dr. {self.doctor.full_name}"
