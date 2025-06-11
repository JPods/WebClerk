from django.urls import path
from .views.contact_view import RegisterView, LoginView, ProfileView, LogoutView, ContactView, ContactDetailView, VerifyEmailView
from .views.action_view import ActionView, ActionDetailView

app_name = 'core'

urlpatterns = [
    path('signup/', RegisterView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),

    path('contacts/', ContactView.as_view(), name='contact-list'),
    path('contacts/<int:pk>/', ContactDetailView.as_view(), name='contact-detail'),

    path('actions/', ActionView.as_view(), name='action-list'),
    path('actions/<int:pk>/', ActionDetailView.as_view(), name='action-detail'),
]