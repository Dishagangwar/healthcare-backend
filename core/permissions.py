from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """Object-level access limited to the user recorded in `owner_field`.

    Views opt in by setting `owner_field` (defaults to "created_by"); the
    queryset should still filter by owner so lists never leak other users'
    rows and detail lookups 404 rather than 403.
    """

    message = "You do not have permission to act on this record."

    def has_object_permission(self, request, view, obj):
        owner_field = getattr(view, "owner_field", "created_by")
        return getattr(obj, owner_field, None) == request.user
