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
# SystemDispatchView registered in apps.core.urls (after specific _ routes)

urlpatterns = [
    # Root redirect → Swagger docs
    path('', RedirectView.as_view(url='/wcapi/swagger/', permanent=False), name='root'),

    # API Documentation
    path('wcapi/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('wcapi/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('wcapi/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Document upload endpoints
    path('wcapi/', include(upload_urlpatterns)),

    # Settings bootstrap — available before full auth (database may be empty)
    path('wcapi/_settings_health/', __import__('apps.core.views.settings_bootstrap_view', fromlist=['SettingsHealthView']).SettingsHealthView.as_view(), name='settings-health'),
    path('wcapi/_settings_bootstrap/', __import__('apps.core.views.settings_bootstrap_view', fromlist=['SettingsBootstrapView']).SettingsBootstrapView.as_view(), name='settings-bootstrap'),
    path('wcapi/_settings_fetch_hq/', __import__('apps.core.views.settings_bootstrap_view', fromlist=['SettingsFetchHqView']).SettingsFetchHqView.as_view(), name='settings-fetch-hq'),

    # Core API endpoints (includes _ prefixed system plumbing)
    path('', include('apps.core.urls')),
    path('wcapi/ai/', include('apps.ai_assistant.urls')),
    path('wcapi/jpods/', include('apps.jpods.urls')),
    path('wcapi/reports/', include('apps.accounts.urls')),
    path('wcapi/orgs/', include('apps.orgs.urls')),
    path('wcapi/docs/', include('apps.docs.urls')),
    path('wcapi/transactions/', include('apps.transactions.urls')),
    path('wcapi/products/', include('apps.products.urls')),
    path('wcapi/sync/', include('apps.sync.urls')),

    # Admin swagger
    path('admin/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='admin-swagger'),

    *([] if getattr(settings, 'READ_ONLY_MODE', False) else [path('admin/', admin.site.urls)]),
    # path('explorer/', include('explorer.urls')),  # TODO: install django-sql-explorer in lib/python3.13
]

# Serve static and media files in development (images, logos, etc.)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# JSON-only error handlers
handler400 = "django.views.defaults.bad_request"
handler403 = "django.views.defaults.permission_denied"
handler404 = "django.views.defaults.page_not_found"
handler500 = "django.views.defaults.server_error"