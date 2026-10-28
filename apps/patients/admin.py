from django.contrib import admin

from core.admin import OwnedAdmin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(OwnedAdmin):
    """Private to its creator, exactly as the patients API is."""

    list_display = ("full_name", "phone", "gender", "blood_group", "created_by", "created_at")
    list_filter = ("gender", "blood_group", "is_active")
    search_fields = ("full_name", "phone", "email")
    autocomplete_fields = ("created_by",)
    readonly_fields = ("created_at", "updated_at")
