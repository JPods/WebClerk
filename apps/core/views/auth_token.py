from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from apps.core.serializers import LoginSerializer


class LoginTokenObtainPairView(TokenObtainPairView):
    """Custom token obtain endpoint using LoginSerializer with role/email/name claims."""
    serializer_class = LoginSerializer


class LoginTokenRefreshView(TokenRefreshView):  # keep for symmetry / future customisation
    pass
