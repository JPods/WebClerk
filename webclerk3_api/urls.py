from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from apps.core.views.auth_views import admin_dashboard

urlpatterns = [
    # Custom admin dashboard (3-column UI)
    path('admin/', admin_dashboard, name='admin_dashboard'),
    # Stock Django admin (needed for namespace 'admin' so templates using {% url 'admin:index' %} work)
    # Mount under alternate path to avoid clobbering custom dashboard while restoring reverse('admin:index').
    path('admin-django/', admin.site.urls),

    # Application routes
    path('', include('apps.core.urls')),
    # Temporarily scope transactions to invoices-only while refactoring
    path('tx/', include('apps.transactions.urls_invoices_only')),
    path('docs/', include('apps.docs.urls')),
        # path('comm/', include(('apps.communications.urls', 'communications'), namespace='communications')),
        path('comm/', include(('apps.communications.urls', 'communications'), namespace='communications')),
    path('sync/', include(('apps.sync.urls', 'sync'), namespace='sync')),
    path('products/', include(('apps.products.urls', 'products'), namespace='products')),
    # OpenAPI schema & interactive docs
    path('api/schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('api/docs/swagger/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-swagger'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='api-schema'), name='api-redoc'),
]

# Framework-level error handlers (must be module level names)
handler404 = 'common.error_views.error_404'
handler500 = 'common.error_views.error_500'