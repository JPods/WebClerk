# Core app URLs - cleaned up to keep only essential endpoints
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.views.save_view import SaveWcapiView
from apps.core.views.auth_views import AuthLoginView, AuthLogoutView, AuthMeView, AuthRegisterView
from apps.core.views.wcapi import WCAPIGetView

urlpatterns = [
    # Auth API
    path("wcapi/register/", AuthRegisterView.as_view(), name="api-auth-register"),
    path("wcapi/login/", AuthLoginView.as_view(), name="api-auth-login"),
    path("wcapi/logout/", AuthLogoutView.as_view(), name="api-auth-logout"),
    path("wcapi/me/", AuthMeView.as_view(), name="api-auth-me"),
    # Standard JWT endpoints (optional but useful)
    path("wcapi/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("wcapi/token_refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Core WCAPI endpoints
    path("wcapi/get/", WCAPIGetView.as_view(), name="wcapi-get"),
    path("wcapi/save/", SaveWcapiView.as_view(), name="wcapi-save"),
]
