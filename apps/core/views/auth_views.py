from django.contrib.auth import authenticate, login, logout, get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status, serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.authentication import BaseAuthentication  # NEW
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiExample

from common.api_responses import api_response
from apps.core.views.token_cookie import set_refresh_cookie, clear_refresh_cookie

User = get_user_model()

# Request/Response schemas
LoginRequestSerializer = inline_serializer(
    name='LoginRequest',
    fields={
        'email': serializers.CharField(help_text='Email address', default='2@2.com'),
        'password': serializers.CharField(help_text='User password', default='1111pass'),
    }
)

LoginResponseSerializer = inline_serializer(
    name='LoginResponse',
    fields={
        'ok': serializers.BooleanField(),
        'data': serializers.DictField(child=serializers.CharField()),
    }
)

LogoutResponseSerializer = inline_serializer(
    name='LogoutResponse',
    fields={
        'ok': serializers.BooleanField(),
    }
)

AuthMeResponseSerializer = inline_serializer(
    name='AuthMeResponse',
    fields={
        'ok': serializers.BooleanField(),
        'data': serializers.DictField(child=serializers.CharField()),
    }
)

RegisterRequestSerializer = inline_serializer(
    name='RegisterRequest',
    fields={
        'email': serializers.EmailField(help_text='Email address for registration'),
        'password': serializers.CharField(help_text='Password for the new account'),
        'name_first': serializers.CharField(help_text='First name', required=False),
        'name_last': serializers.CharField(help_text='Last name', required=False),
        'company': serializers.CharField(help_text='Company name', required=False),
        'title': serializers.CharField(help_text='Job title', required=False),
    }
)

RegisterResponseSerializer = inline_serializer(
    name='RegisterResponse',
    fields={
        'ok': serializers.BooleanField(),
        'data': serializers.DictField(child=serializers.CharField()),
    }
)

@method_decorator(csrf_exempt, name="dispatch")  # ensure Django CSRF middleware skips this view
@extend_schema(
    summary="User Authentication",
    description="Authenticate user with username/email and password. Returns JWT tokens for subsequent API requests.",
    request=LoginRequestSerializer,
    responses={
        200: LoginResponseSerializer,
        400: LoginResponseSerializer,
        401: LoginResponseSerializer,
    }
)
class AuthLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes: tuple[type[BaseAuthentication], ...] = ()  # disable SessionAuthentication (no CSRF)

    def post(self, request):
        body = request.data if isinstance(request.data, dict) else {}
        username = (body.get("username") or body.get("email") or "").strip()
        password = (body.get("password") or "").strip()
        if not username or not password:
            return api_response(data=None, message="username/email and password required", status_code=400)

        user = authenticate(request, username=username, password=password)
        if user is None:
            try:
                u = User.objects.filter(email__iexact=username).first()
                if u:
                    user = authenticate(request, username=getattr(u, "username", None) or getattr(u, "email", None), password=password)
            except Exception:
                pass

        if user is None or not getattr(user, "is_active", True):
            return api_response(
                data=None, message="invalid credentials", status_code=401,
                error={"code": "invalid_credentials", "details": None},
            )

        # Optional: create a session for browser clients; ignore errors in API contexts
        try:
            login(request, user)
        except Exception:
            pass

        # Issue JWT tokens with role claim
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        # Add role to token claims
        access["role"] = getattr(user, "role", "user")
        refresh["role"] = getattr(user, "role", "user")
        data = {
            "user": {
                "id": user.pk,
                "email": getattr(user, "email", None),
                "username": getattr(user, "username", None),
                "role": getattr(user, "role", None),
            },
            "access": str(access),
        }
        resp = api_response(data=data, message="login successful")
        set_refresh_cookie(resp, str(refresh))
        return resp


@extend_schema(
    summary="User Logout",
    description="Logout the current user and invalidate their session.",
    responses={
        200: LogoutResponseSerializer,
    }
)
class AuthLogoutView(APIView):
    # Allow logout even if the client has no valid auth; this keeps the endpoint
    # idempotent for SPA logout flows where tokens may already be cleared client-side.
    permission_classes = [permissions.AllowAny]
    authentication_classes: tuple[type[BaseAuthentication], ...] = ()
    serializer_class = LogoutResponseSerializer

    def post(self, request):
        try:
            logout(request)
        except Exception:
            # Ignore backend/session logout errors to keep response deterministic
            pass
        resp = api_response(data=None, message="logged out")
        clear_refresh_cookie(resp)
        return resp


@extend_schema(
    summary="Get Current User",
    description="Get information about the currently authenticated user.",
    responses={
        200: AuthMeResponseSerializer,
        401: AuthMeResponseSerializer,
    }
)
class AuthMeView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return api_response(data=None, message="unauthenticated", status_code=401)
        
        # Get user data with proper error handling
        user = request.user
        data = {
            "id": user.pk,
            "email": getattr(user, "email", None),
            "name_first": getattr(user, "name_first", None),
            "name_last": getattr(user, "name_last", None),
            "company": getattr(user, "company", None),
            "title": getattr(user, "title", None),
            "role": getattr(user, "role", None),
            "is_active": getattr(user, "is_active", False),
            "date_joined": getattr(user, "date_joined", None),
            "prefs": getattr(user, "prefs", None) or {},
        }
        return api_response(data={"user": data}, message="authenticated")


@method_decorator(csrf_exempt, name="dispatch")
@extend_schema(
    summary="User Registration",
    description="Register a new user account with email and password. Returns JWT tokens for subsequent API requests.",
    request=RegisterRequestSerializer,
    responses={
        201: RegisterResponseSerializer,
        400: RegisterResponseSerializer,
        409: RegisterResponseSerializer,
    }
)
class AuthRegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes: tuple[type[BaseAuthentication], ...] = ()

    def post(self, request):
        body = request.data if isinstance(request.data, dict) else {}
        email = (body.get("email") or "").strip().lower()
        password = (body.get("password") or "").strip()
        name_first = (body.get("name_first") or "").strip()
        name_last = (body.get("name_last") or "").strip()
        company = (body.get("company") or "").strip()
        title = (body.get("title") or "").strip()

        # Validate required fields
        if not email or not password:
            return api_response(data=None, message="email and password are required", status_code=400)

        # Check if email already exists
        if User.objects.filter(email__iexact=email).exists():
            return api_response(data=None, message="email already registered", status_code=409)

        # Validate password strength
        try:
            validate_password(password)
        except ValidationError as e:
            return api_response(
                data=None, message="invalid password", status_code=400,
                error={"code": "validation_error", "details": list(e.messages)},
            )

        # Create user
        try:
            user = User.objects.create_user(
                email=email,
                password=password,
                name_first=name_first or "User",
                name_last=name_last or "Account",
                company=company,
                title=title,
                role='user'  # Default role is user; admin/employee must be set by admin
            )
        except Exception as e:
            return api_response(
                data=None, message="failed to create user", status_code=400,
                error={"code": "create_failed", "details": str(e)},
            )

        # Auto-login user and issue JWT tokens
        try:
            user = authenticate(request, username=email, password=password)
            if user and getattr(user, "is_active", True):
                # Issue JWT tokens with role claim
                refresh = RefreshToken.for_user(user)
                access = refresh.access_token
                access["role"] = getattr(user, "role", "user")
                refresh["role"] = getattr(user, "role", "user")
                data = {
                    "user": {
                        "id": user.pk, 
                        "email": getattr(user, "email", None), 
                        "name_first": getattr(user, "name_first", None),
                        "name_last": getattr(user, "name_last", None),
                        "company": getattr(user, "company", None),
                        "title": getattr(user, "title", None),
                        "role": getattr(user, "role", None),
                    },
                    "access": str(access),
                }
                resp = api_response(data=data, message="registration successful", status_code=201)
                set_refresh_cookie(resp, str(refresh))
                return resp
        except Exception as e:
            return api_response(
                data=None, message="authentication failed after registration", status_code=500,
                error={"code": "post_register_auth_failed", "details": str(e)},
            )

        return api_response(
            data=None, message="registration completed but login failed", status_code=500,
            error={"code": "post_register_login_failed", "details": None},
        )