"""Root URL configuration for Employee Directory."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("dashboard.urls")),
    path("accounts/", include("accounts.urls")),
    path("employees/", include("employees.urls")),
    path("departments/", include("departments.urls")),
    path("positions/", include("positions.urls")),
    path("attendance/", include("attendance.urls")),
    path("chat/", include("chat.urls")),
    path("notifications/", include("notifications.urls")),
    path("portal/", include("portal.urls")),
    path("performance/", include("performance.urls")),
    path(
        "calendar/",
        include(("company_calendar.urls", "company_calendar")),
    ),
    path("api/", include("api.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler403 = "accounts.views_employee_accounts.permission_denied_view"
