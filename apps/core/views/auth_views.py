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
            return Response({"ok": False, "code": 400, "message": "username/email and password required"}, status=400)

        user = authenticate(request, username=username, password=password)
        if user is None:
            try:
                u = User.objects.filter(email__iexact=username).first()
                if u:
                    user = authenticate(request, username=getattr(u, "username", None) or getattr(u, "email", None), password=password)
            except Exception:
                pass

        if user is None or not getattr(user, "is_active", True):
            return Response({"ok": False, "code": 401, "message": "invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

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
            "refresh": str(refresh),
        }
        return Response({"ok": True, "data": data}, status=200)


@extend_schema(
    summary="User Logout",
    description="Logout the current user and invalidate their session.",
    responses={
        200: LogoutResponseSerializer,
    }
)
class AuthLogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LogoutResponseSerializer

    def post(self, request):
        logout(request)
        return Response({"ok": True})


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
            return Response({"ok": False, "code": 401, "message": "unauthenticated"}, status=401)
        
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
        }
        return Response({"ok": True, "data": {"user": data}})


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
            return Response({"ok": False, "code": 400, "message": "email and password are required"}, status=400)

        # Check if email already exists
        if User.objects.filter(email__iexact=email).exists():
            return Response({"ok": False, "code": 409, "message": "email already registered"}, status=409)

        # Validate password strength
        try:
            validate_password(password)
        except ValidationError as e:
            return Response({"ok": False, "code": 400, "message": "invalid password", "errors": list(e.messages)}, status=400)

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
            return Response({"ok": False, "code": 400, "message": "failed to create user", "error": str(e)}, status=400)

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
                    "refresh": str(refresh),
                }
                return Response({"ok": True, "data": data}, status=201)
        except Exception as e:
            return Response({"ok": False, "code": 500, "message": "authentication failed after registration", "error": str(e)}, status=500)

        return Response({"ok": False, "code": 500, "message": "registration completed but login failed"}, status=500)