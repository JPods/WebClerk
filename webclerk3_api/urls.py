from django.contrib import admin
from django.urls import path, include
from apps.core.views.auth_views import admin_dashboard

urlpatterns = [
    # Custom admin dashboard (3-column UI)
    path('admin/', admin_dashboard, name='admin_dashboard'),
    # Stock Django admin (needed for namespace 'admin' so templates using {% url 'admin:index' %} work)
    # Mount under alternate path to avoid clobbering custom dashboard while restoring reverse('admin:index').
    path('admin-django/', admin.site.urls),

    # Application routes
    path('', include('apps.core.urls')),
    path('tx/', include('apps.transactions.urls')),
    path('docs/', include('apps.docs.urls')),
        # path('comm/', include(('apps.communications.urls', 'communications'), namespace='communications')),
        path('comm/', include(('apps.communications.urls', 'communications'), namespace='communications')),
]