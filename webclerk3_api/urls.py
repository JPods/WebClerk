from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView
)
from apps.docs.urls import upload_urlpatterns

urlpatterns = [
    # Root redirect → Swagger docs
    path('', RedirectView.as_view(url='/wcapi/swagger/', permanent=False), name='root'),

    # API Documentation
    path('wcapi/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('wcapi/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('wcapi/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Document upload endpoints
    path('wcapi/', include(upload_urlpatterns)),

    # Core API endpoints
    path('', include('apps.core.urls')),
    path('api/orgs/', include('apps.orgs.urls')),
    path('api/docs/', include('apps.docs.urls')),
    path('api/transactions/', include('apps.transactions.urls')),
    path('api/products/', include('apps.products.urls')),

    # Admin swagger
    path('admin/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='admin-swagger'),

    path('admin/', admin.site.urls),
]

# Serve static files in development (images, etc.)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

# JSON-only error handlers
handler400 = "django.views.defaults.bad_request"
handler403 = "django.views.defaults.permission_denied"
handler404 = "django.views.defaults.page_not_found"
handler500 = "django.views.defaults.server_error"