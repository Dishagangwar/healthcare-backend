from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group

from .models import User

# Groups are a Django built-in this project does not use: access is decided by
# record ownership, not by group membership. Unregistering keeps the admin to
# what the system actually models. The model itself still exists, since
# PermissionsMixin depends on it.
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "name", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("email", "name")
    ordering = ("-date_joined",)
    filter_horizontal = ("user_permissions",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("name",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser",
                                    "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "password1", "password2"),
        }),
    )
