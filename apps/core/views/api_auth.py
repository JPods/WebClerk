from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from apps.core.serializers.api_auth_serializers import ApiLoginSerializer, ApiSignupSerializer
from django.utils.module_loading import import_string


class ApiLoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ApiLoginSerializer


class ApiSignupView(APIView):
    permission_classes = [permissions.AllowAny]

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

