# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/webclerk3_api/urls.py
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
    path('admin-django/', admin.site.urls),                          # Original Django admin
    path('', include('core.urls')),  # This handles everything including the home page
]