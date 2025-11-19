# Core app URLs - cleaned up to keep only essential endpoints
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.views.save_view import SaveWcapiView
from apps.core.views.auth_views import AuthLoginView, AuthLogoutView, AuthMeView
from apps.core.views.wcapi import WCAPIGetView

urlpatterns = [
    # Auth API
    path("api/auth/login/", AuthLoginView.as_view(), name="api-auth-login"),
    path("api/auth/logout/", AuthLogoutView.as_view(), name="api-auth-logout"),
    path("api/auth/me/", AuthMeView.as_view(), name="api-auth-me"),
    # Standard JWT endpoints (optional but useful)
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Core WCAPI endpoints
    path("wcapi/get/", WCAPIGetView.as_view(), name="wcapi-get"),
    path("wcapi/save/", SaveWcapiView.as_view(), name="wcapi-save"),
]
