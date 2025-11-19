from django.contrib.auth import authenticate, login, logout, get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
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
        'username': serializers.CharField(required=False, help_text='Username or email address'),
        'email': serializers.CharField(required=False, help_text='Email address (alternative to username)'),
        'password': serializers.CharField(required=True, help_text='User password'),
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

@method_decorator(csrf_exempt, name="dispatch")  # ensure Django CSRF middleware skips this view
@extend_schema(
    summary="User Authentication",
    description="Authenticate user with username/email and password. Returns JWT tokens for subsequent API requests.",
    request=LoginRequestSerializer,
    responses={
        200: LoginResponseSerializer,
        400: OpenApiExample('Bad Request', value={'ok': False, 'code': 400, 'message': 'username/email and password required'}),
        401: OpenApiExample('Unauthorized', value={'ok': False, 'code': 401, 'message': 'invalid credentials'}),
    },
    examples=[
        OpenApiExample(
            'Valid Login',
            value={
                'username': 'john@example.com',
                'password': 'securepassword'
            },
            request_only=True,
        ),
        OpenApiExample(
            'Successful Response',
            value={
                'ok': True,
                'data': {
                    'user': {'id': 1, 'email': 'john@example.com', 'username': 'john'},
                    'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                }
            },
            response_only=True,
        ),
    ]
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

        # Issue JWT tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        data = {
            "user": {"id": user.pk, "email": getattr(user, "email", None), "username": getattr(user, "username", None)},
            "access": str(access),
            "refresh": str(refresh),
        }
        return Response({"ok": True, "data": data}, status=200)


@extend_schema(
    summary="User Logout",
    description="Logout the current user and invalidate their session.",
    responses={
        200: LogoutResponseSerializer,
    },
    examples=[
        OpenApiExample(
            'Successful Logout',
            value={'ok': True},
            response_only=True,
        ),
    ]
)
class AuthLogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"ok": True})


@extend_schema(
    summary="Get Current User",
    description="Get information about the currently authenticated user.",
    responses={
        200: AuthMeResponseSerializer,
        401: OpenApiExample('Unauthorized', value={'ok': False, 'code': 401, 'message': 'unauthenticated'}),
    },
    examples=[
        OpenApiExample(
            'Authenticated User',
            value={
                'ok': True,
                'data': {
                    'user': {
                        'id': 1,
                        'email': 'john@example.com',
                        'username': 'john'
                    }
                }
            },
            response_only=True,
        ),
        OpenApiExample(
            'Unauthenticated',
            value={'ok': False, 'code': 401, 'message': 'unauthenticated'},
            response_only=True,
        ),
    ]
)
class AuthMeView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        u = getattr(request, "user", None)
        if not (u and getattr(u, "is_authenticated", False)):
            return Response({"ok": False, "code": 401, "message": "unauthenticated"}, status=401)
        # Only access u.pk after confirming authentication
        data = {
            "id": u.pk,
            "email": getattr(u, "email", None),
            "username": getattr(u, "username", None),
        }
        return Response({"ok": True, "data": {"user": data}})