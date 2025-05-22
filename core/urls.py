from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import SignupView, ProfileView, VerifyEmailView, LoginView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh-token/', TokenRefreshView.as_view(), name='refresh_token'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify_email'),
]