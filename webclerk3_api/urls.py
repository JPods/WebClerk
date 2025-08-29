from django.contrib import admin
from django.urls import path, include
from apps.core.views.auth_views import admin_dashboard

urlpatterns = [
    # Admin
    #path('admin/', admin.site.urls),
    # Replace this:
    # path('admin/', admin.site.urls),

    # With this:
    path('admin/', admin_dashboard, name='admin_dashboard'),         # Your custom 3-column admin
    path('', include('apps.core.urls')),  # Core pages
    path('tx/', include('apps.transactions.urls')),  # Transaction endpoints
    path('', include('apps.core.urls')),  # This handles everything including the home page
]