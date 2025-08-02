from django.conf import settings
from django.urls import path, include
from django.contrib import admin
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# Import web views
from core.views.web_auth_views import WebSignupView, WebLoginView, WebLogoutView
from core.views.contact_view import WebContactView
from core.views.edit_views import EditContactView

# 🎯 Import Universal API views (now that the file exists)
from core.views.generic_views import (
    UniversalQueryView, 
    UniversalSaveView, 
    UniversalGetView, 
    UniversalDeleteView, 
    UniversalCloneView,
    UniversalCRUDView  # Changed from UniversalManageView
)

urlpatterns = [
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
    
    # Web authentication pages
    path('signup/', WebSignupView.as_view(), name='web-signup'),
    path('login/', WebLoginView.as_view(), name='web-login'),
    path('logout/', WebLogoutView.as_view(), name='web-logout'),
    path('contact/', WebContactView.as_view(), name='contact'),
    path('edit-contact/', EditContactView.as_view(), name='edit-contact'),


    path('WCapi/mypage/', WebContactView.as_view(), name='contact'),
    #path('edit-contact/', EditContactView.as_view(), name='edit-contact'),

    
    # 🎯 UNIVERSAL API ENDPOINTS - Now Active!
    path('WCapi/query/', UniversalQueryView.as_view(), name='universal-query'),
    path('WCapi/save/', UniversalSaveView.as_view(), name='universal-save'),
    path('WCapi/get/', UniversalGetView.as_view(), name='universal-get'),
    path('WCapi/delete/', UniversalDeleteView.as_view(), name='universal-delete'),
    path('WCapi/clone/', UniversalCloneView.as_view(), name='universal-clone'),
    
    # Universal management pages for ANY table
    path('WCapi/<str:table_name>/manage/', UniversalCRUDView.as_view(), name='universal-manage'),
    
    path('admin/', admin.site.urls),
    path('WCapi/', include('core.urls')),
    path('WCapi/communications/', include('communications.urls')),

    path('WCapi/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('WCapi/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('WCapi/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns