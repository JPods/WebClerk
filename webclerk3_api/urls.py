from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path, include
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from core.views.web_auth_views import WebSignupView, WebLoginView, WebLogoutView
from core.views.profile_view import WebProfileView
from core.views.edit_views import EditProfileView, ManageAddressesView, AddAddressView, EditAddressView, DeleteAddressView
from core.views.phone_views import ManagePhonesView, AddPhoneView, EditPhoneView, DeletePhoneView
from core.views.email_views import ManageEmailsView, AddEmailView, EditEmailView, DeleteEmailView
from core.views.domain_views import ManageDomainsView, AddDomainView, EditDomainView, DeleteDomainView
from core.views.action_management_views import ManageActionsView, AddActionView, EditActionView, DeleteActionView

urlpatterns = [
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
    
    # Web-based authentication pages (outside API namespace)
    path('signup/', WebSignupView.as_view(), name='web-signup'),
    path('login/', WebLoginView.as_view(), name='web-login'),
    path('logout/', WebLogoutView.as_view(), name='web-logout'),
    path('profile/', WebProfileView.as_view(), name='profile'),
    
    # Profile editing pages
    path('edit-profile/', EditProfileView.as_view(), name='edit-profile'),
    path('manage-addresses/', ManageAddressesView.as_view(), name='manage-addresses'),
    path('add-address/', AddAddressView.as_view(), name='add-address'),
    path('edit-address/<int:address_id>/', EditAddressView.as_view(), name='edit-address'),
    path('delete-address/<int:address_id>/', DeleteAddressView.as_view(), name='delete-address'),
    
    # Phone management pages
    path('manage-phones/', ManagePhonesView.as_view(), name='manage-phones'),
    path('add-phone/', AddPhoneView.as_view(), name='add-phone'),
    path('edit-phone/<int:phone_id>/', EditPhoneView.as_view(), name='edit-phone'),
    path('delete-phone/<int:phone_id>/', DeletePhoneView.as_view(), name='delete-phone'),
    
    # Email management pages
    path('manage-emails/', ManageEmailsView.as_view(), name='manage-emails'),
    path('add-email/', AddEmailView.as_view(), name='add-email'),
    path('edit-email/<int:email_id>/', EditEmailView.as_view(), name='edit-email'),
    path('delete-email/<int:email_id>/', DeleteEmailView.as_view(), name='delete-email'),
    
    # Domain management pages
    path('manage-domains/', ManageDomainsView.as_view(), name='manage-domains'),
    path('add-domain/', AddDomainView.as_view(), name='add-domain'),
    path('edit-domain/<int:domain_id>/', EditDomainView.as_view(), name='edit-domain'),
    path('delete-domain/<int:domain_id>/', DeleteDomainView.as_view(), name='delete-domain'),
    
    # Action management pages
    path('manage-actions/', ManageActionsView.as_view(), name='manage-actions'),
    path('add-action/', AddActionView.as_view(), name='add-action'),
    path('edit-action/<int:action_id>/', EditActionView.as_view(), name='edit-action'),
    path('delete-action/<int:action_id>/', DeleteActionView.as_view(), name='delete-action'),
    
    path('admin/', admin.site.urls),
    path('WCapi/', include('core.urls')),
    path('WCapi/communications/', include('communications.urls')),

    path('WCapi/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('WCapi/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('WCapi/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]