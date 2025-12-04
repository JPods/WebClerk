from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView
)

urlpatterns = [
    # API Documentation
    path('wcapi/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('wcapi/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('wcapi/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Core API endpoints
    path('', include('apps.core.urls')),
    path('api/transactions/', include('apps.transactions.urls')),

    # Admin swagger
    path('admin/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='admin-swagger'),

    path('admin/', admin.site.urls),
]

# JSON-only error handlers
handler400 = "django.views.defaults.bad_request"
handler403 = "django.views.defaults.permission_denied"
handler404 = "django.views.defaults.page_not_found"
handler500 = "django.views.defaults.server_error"