from django.urls import path
from .views.contact_view import RegisterView, LoginView, ProfileView, LogoutView, ContactView, ContactDetailView, VerifyEmailView
from .views.action_view import ActionView, ActionDetailView
from .views.web_auth_views import WebSignupView, WebLoginView, WebLogoutView
from .views.profile_view import WebProfileView
from .views.edit_views import EditProfileView, ManageAddressesView, AddAddressView, EditAddressView, DeleteAddressView

app_name = 'core'

urlpatterns = [
    # API endpoints
    path('signup/', RegisterView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),

    # Web-based authentication pages
    path('web-signup/', WebSignupView.as_view(), name='web-signup'),
    path('web-login/', WebLoginView.as_view(), name='web-login'),
    path('web-logout/', WebLogoutView.as_view(), name='logout'),
    path('web-profile/', WebProfileView.as_view(), name='web-profile'),
    
    # Profile editing pages
    path('edit-profile/', EditProfileView.as_view(), name='edit-profile'),
    path('manage-addresses/', ManageAddressesView.as_view(), name='manage-addresses'),
    path('add-address/', AddAddressView.as_view(), name='add-address'),
    path('edit-address/<int:address_id>/', EditAddressView.as_view(), name='edit-address'),
    path('delete-address/<int:address_id>/', DeleteAddressView.as_view(), name='delete-address'),

    path('contacts/', ContactView.as_view(), name='contact-list'),
    path('contacts/<int:pk>/', ContactDetailView.as_view(), name='contact-detail'),

    path('actions/', ActionView.as_view(), name='action-list'),
    path('actions/<int:pk>/', ActionDetailView.as_view(), name='action-detail'),
]