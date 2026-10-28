from django.contrib import admin

from core.admin import OwnedAdmin

from .models import PatientDoctorMapping


@admin.register(PatientDoctorMapping)
class PatientDoctorMappingAdmin(OwnedAdmin):
    """Private to its creator; the patient picker is narrowed to theirs
    automatically, because autocomplete runs through PatientAdmin."""

    list_display = ("patient", "doctor", "is_primary", "created_by", "created_at")
    list_filter = ("is_primary",)
    search_fields = ("patient__full_name", "doctor__full_name")
    autocomplete_fields = ("patient", "doctor", "created_by")
    readonly_fields = ("created_at", "updated_at")
