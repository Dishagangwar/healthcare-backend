"""Permissions for a self-service workspace account.

Anyone may register, so these accounts get staff access to the admin but
only over the records this project is about. The user table is absent on
purpose: an account handed out to whoever asks must not be able to read
or create other accounts. `core.admin.OwnedAdmin` then narrows what each
one sees to its own rows.
"""

from django.contrib.auth.models import Permission
from django.db.models import Q

WORKSPACE_MODELS = [
    ("patients", "patient"),
    ("doctors", "doctor"),
    ("mappings", "patientdoctormapping"),
]

WORKSPACE_ACTIONS = ("add", "change", "view")


def grant_workspace_access(user, *, allow_delete=False):
    """Make `user` staff with exactly the workspace permissions.

    Permissions are assigned rather than added to, so narrowing the lists
    above and re-running actually takes the extra rights away.

    `allow_delete` is off for the shared demo account, whose records every
    visitor sees, and on for a registered account, which can only reach
    its own.
    """
    actions = WORKSPACE_ACTIONS + (("delete",) if allow_delete else ())
    query = Q()
    for app_label, model in WORKSPACE_MODELS:
        query |= Q(
            content_type__app_label=app_label,
            content_type__model=model,
            codename__in=[f"{action}_{model}" for action in actions],
        )
    user.user_permissions.set(Permission.objects.filter(query))
    if not user.is_staff:
        user.is_staff = True
        user.save(update_fields=["is_staff"])
