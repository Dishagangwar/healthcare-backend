"""Admin classes that carry the API's ownership rules into the admin.

The API treats a record as belonging to whoever created it, and hides
rather than forbids another user's rows. The admin has no such notion on
its own, so a staff account would otherwise see everything. These two
base classes close that gap, which is what makes self-service
registration safe to offer.
"""

from django.contrib import admin


class OwnedAdmin(admin.ModelAdmin):
    """Shows each non-superuser only the records they created."""

    owner_field = "created_by"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(**{self.owner_field: request.user})

    def get_exclude(self, request, obj=None):
        exclude = tuple(super().get_exclude(request, obj) or ())
        if request.user.is_superuser:
            return exclude or None
        # Taken from the request instead. It is also a link to the user
        # table, which a workspace account has no permission to read.
        return exclude + (self.owner_field,)

    def save_model(self, request, obj, form, change):
        if getattr(obj, f"{self.owner_field}_id", None) is None:
            setattr(obj, self.owner_field, request.user)
        super().save_model(request, obj, form, change)


class SharedDirectoryAdmin(OwnedAdmin):
    """Readable by every staff user, writable only by whoever added the row.

    The doctor directory works this way in the API: shared for reading so
    a new account can assign the doctors already on file, owner-only for
    writing so it cannot edit someone else's entry.
    """

    def get_queryset(self, request):
        return admin.ModelAdmin.get_queryset(self, request)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self._owns(request, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and self._owns(request, obj)

    def _owns(self, request, obj):
        # obj is None when the changelist asks whether the button should
        # exist at all; the per-row check happens on the change page.
        if obj is None or request.user.is_superuser:
            return True
        return getattr(obj, f"{self.owner_field}_id", None) == request.user.pk
