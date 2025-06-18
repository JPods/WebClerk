from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('WCapi/', include('core.urls')),
    path('WCapi/communications/', include('communications.urls')),

    path('WCapi/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('WCapi/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('WCapi/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]