from django.urls import path
from .views.contact_view import RegisterView, LoginView, ProfileView, LogoutView, ContactView, ContactDetailView, VerifyEmailView
from .views.action_view import ActionView, ActionDetailView
from .views.web_auth_views import WebSignupView, WebLoginView, WebLogoutView

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

    path('contacts/', ContactView.as_view(), name='contact-list'),
    path('contacts/<int:pk>/', ContactDetailView.as_view(), name='contact-detail'),

    path('actions/', ActionView.as_view(), name='action-list'),
    path('actions/<int:pk>/', ActionDetailView.as_view(), name='action-detail'),
]