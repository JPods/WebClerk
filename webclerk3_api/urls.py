# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/webclerk3_api/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Include ALL core URLs (your excellent core/urls.py)
    path('', include('core.urls')),  # This handles everything including the home page
]