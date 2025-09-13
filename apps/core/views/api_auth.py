from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, serializers
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from apps.core.serializers.api_auth_serializers import ApiLoginSerializer, ApiSignupSerializer
from django.utils.module_loading import import_string
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiExample


class ApiLoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ApiLoginSerializer

    @extend_schema(
        operation_id="auth_login_create",
        request=inline_serializer(
            name="LoginRequest",
            fields={
                'email': serializers.EmailField(),
                'password': serializers.CharField(),
                'role': serializers.CharField(required=False),
            }
        ),
        responses={
            200: inline_serializer(
                name="LoginEnvelope",
                fields={
                    'status': serializers.CharField(),
                    'error': serializers.JSONField(required=False, allow_null=True),
                    'code': serializers.IntegerField(),
                    'message': serializers.CharField(allow_blank=True),
                    'data': inline_serializer(
                        name="LoginResponse",
                        fields={
                            'refresh': serializers.CharField(),
                            'access': serializers.CharField(),
                            'email': serializers.EmailField(),
                            'role': serializers.CharField(),
                            'name_first': serializers.CharField(),
                            'name_last': serializers.CharField(),
                        }
                    )
                }
            )
        },
        examples=[
            OpenApiExample(
                "LoginSuccess",
                value={
                    "status": "success",
                    "error": None,
                    "code": 200,
                    "message": "",
                    "data": {
                        "refresh": "...",
                        "access": "...",
                        "email": "1@1.com",
                        "role": "admin",
                        "name_first": "first_1",
                        "name_last": "last_1"
                    }
                },
                request_only=False,
                response_only=True
            )
        ],
        description="Login and receive JWT pair plus basic user claims in the envelope data.",
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ApiSignupView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        operation_id="auth_signup_create",
        request=ApiSignupSerializer,
        responses={
            201: inline_serializer(
                name="SignupResponse",
                fields={
                    'refresh': serializers.CharField(),
                    'access': serializers.CharField(),
                    'user': inline_serializer(
                        name="SignupUser",
                        fields={
                            'id': serializers.IntegerField(),
                            'email': serializers.EmailField(),
                            'name_first': serializers.CharField(allow_blank=True),
                            'name_last': serializers.CharField(allow_blank=True),
                            'role': serializers.CharField(allow_blank=True),
                        }
                    ),
                }
            )
        },
        examples=[
            OpenApiExample(
                "SignupSuccess",
                value={
                    'refresh': '...jwt...',
                    'access': '...jwt...',
                    'user': {
                        'id': 1,
                        'email': 'user@example.com',
                        'name_first': 'Ada',
                        'name_last': 'Lovelace',
                        'role': 'user'
                    }
                },
                response_only=True,
            )
        ],
        description="Create a new user and return JWT tokens plus basic user profile.",
    )
    def post(self, request, *args, **kwargs):
        serializer = ApiSignupSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        saved = serializer.save()
        # serializer.save() should return a single user instance; handle accidental list return gracefully
        user = saved[0] if isinstance(saved, list) else saved
        refresh = RefreshToken.for_user(user)
        # Inject custom claims into access token (RefreshToken.for_user already sets user_id)
        access_token = refresh.access_token
        access_token['email'] = user.email
        access_token['role'] = user.role
        access_token['name_first'] = user.name_first
        access_token['name_last'] = user.name_last
        payload = {
            'refresh': str(refresh),
            'access': str(access_token),
            'user': {
                'id': user.id,
                'email': user.email,
                'name_first': user.name_first,
                'name_last': user.name_last,
                'role': user.role,
            }
        }
        return Response(payload, status=status.HTTP_201_CREATED)

