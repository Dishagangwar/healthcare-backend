from django.contrib import admin

from .models import Doctor


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("full_name", "specialization", "license_number",
                    "years_of_experience", "is_available")
    list_filter = ("specialization", "is_available")
    search_fields = ("full_name", "license_number", "email")
    autocomplete_fields = ("created_by",)
    readonly_fields = ("created_at", "updated_at")
