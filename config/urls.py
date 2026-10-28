from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic.base import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def health_check(_request):
    """Liveness probe for deployment tooling."""
    return JsonResponse({"success": True, "status": "healthy"})


urlpatterns = [
    # A JSON API has no front page, so the bare domain goes to the admin
    # login rather than returning 404. Deliberately a temporary redirect:
    # browsers cache a permanent one indefinitely, which would be awkward
    # to undo if the root ever serves something of its own.
    path("", RedirectView.as_view(pattern_name="admin:index", permanent=False)),
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health-check"),
    # API
    path("api/auth/", include("apps.accounts.urls")),
    path("api/patients/", include("apps.patients.urls")),
    path("api/doctors/", include("apps.doctors.urls")),
    path("api/mappings/", include("apps.mappings.urls")),
    # Interactive documentation, generated from the code itself.
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
