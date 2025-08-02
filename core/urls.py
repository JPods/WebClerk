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

# 🎯 Import Universal API views
from core.views.generic_views import (
    UniversalQueryView, 
    UniversalSaveView, 
    UniversalGetView, 
    UniversalDeleteView, 
    UniversalCloneView,
    UniversalCRUDView
)

urlpatterns = [
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
    
    # Web authentication pages
    path('signup/', WebSignupView.as_view(), name='web-signup'),
    path('login/', WebLoginView.as_view(), name='web-login'),
    path('logout/', WebLogoutView.as_view(), name='web-logout'),
    
    # 🎯 CONTACT VIEWS - Universal API compliant using 'id_contact' convention
    path('contact/', WebContactView.as_view(), name='contact-profile'),  # Current user
    path('contact/<int:id_contact>/', WebContactView.as_view(), name='contact-detail'),  # Specific contact
    path('edit-contact/', EditContactView.as_view(), name='edit-contact'),  # Edit current user
    path('edit-contact/<int:id_contact>/', EditContactView.as_view(), name='edit-contact-detail'),  # Edit contact

    # Legacy compatibility
    path('WCapi/mypage/', lambda request: HttpResponseRedirect('/contact/'), name='legacy-mypage'),
    
    # 🎯 UNIVERSAL API ENDPOINTS - Core Universal API
    path('WCapi/query/', UniversalQueryView.as_view(), name='universal-query'),
    path('WCapi/save/', UniversalSaveView.as_view(), name='universal-save'),
    path('WCapi/get/', UniversalGetView.as_view(), name='universal-get'),  # ?table_name=contacts&id=123
    path('WCapi/delete/', UniversalDeleteView.as_view(), name='universal-delete'),
    path('WCapi/clone/', UniversalCloneView.as_view(), name='universal-clone'),
    
    # Universal management pages - using id_contact for related data
    path('WCapi/<str:table_name>/manage/', UniversalCRUDView.as_view(), name='universal-manage'),
    path('WCapi/<str:table_name>/<int:id>/', UniversalGetView.as_view(), name='universal-detail'),  # RESTful API
    
    path('admin/', admin.site.urls),
    path('WCapi/', include('core.urls')),
    path('WCapi/communications/', include('communications.urls')),

    # API Documentation
    path('WCapi/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('WCapi/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('WCapi/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns