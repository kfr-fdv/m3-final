from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.core.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/", include("apps.api.urls")),
    path("", include("apps.catalog.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.orders.urls")),
    path("", include("apps.reviews.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
