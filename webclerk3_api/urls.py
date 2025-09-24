from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('', include('apps.core.wcapi.urls')),
    path('admin/', admin.site.urls),
]

# JSON-only error handlers
handler400 = "apps.core.wcapi.error_handlers.json_bad_request"
handler403 = "apps.core.wcapi.error_handlers.json_permission_denied"
handler404 = "apps.core.wcapi.error_handlers.json_not_found"
handler500 = "apps.core.wcapi.error_handlers.json_server_error"