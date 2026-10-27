from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(_request):
    """Liveness probe for deployment tooling."""
    return JsonResponse({"success": True, "status": "healthy"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health-check"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/patients/", include("apps.patients.urls")),
    path("api/doctors/", include("apps.doctors.urls")),
    path("api/mappings/", include("apps.mappings.urls")),
]
