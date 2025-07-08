from rest_framework.views import APIView
from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..serializers import ContactSerializer, RegisterSerializer, LoginSerializer, VerifyEmailSerializer
from ..models import Contact
from core.utils import get_accessible_fields
from django.core.mail import send_mail
from django.conf import settings

class LoginView(TokenObtainPairView):
    """Handles user login and JWT token generation."""
    serializer_class = LoginSerializer

    @extend_schema(
        summary="User Login",
        description="Authenticate a user with email and password, returning JWT access and refresh tokens.",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="JWT tokens generated successfully"),
            401: OpenApiResponse(description="Invalid credentials"),
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

class RegisterView(APIView):
    """Handles user registration and sends verification email."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="User Registration",
        description="Register a new user with required fields (email, password, name_first, name_last) and optional fields. Sends a verification email.",
        request=RegisterSerializer,
        responses={
            201: ContactSerializer,
            400: OpenApiResponse(description="Invalid data"),
            409: OpenApiResponse(description="Email already exists"),
        }
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Send verification email
            subject = 'WebClerk3.0: Verify Your Email Address'
            message = (
                f"Hi {user.name_first or 'User'},\n\n"
                f"Please verify your email address by using the following code:\n\n"
                f"Verification Code: {user.verification_code}\n\n"
                f"This code is valid for 24 hours.\n\n"
                f"Thank you,\nWebClerk3 Team"
            )
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            except Exception as e:
                # Log error but don't fail registration
                print(f"Failed to send email: {str(e)}")
            return Response(ContactSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProfileView(APIView):
    """Handles user profile retrieval and updates."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get User Profile",
        description="Retrieve the authenticated user's profile details.",
        responses={
            200: ContactSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def get(self, request):
        serializer = ContactSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update User Profile",
        description="Update the authenticated user's profile fields (partial update).",
        request=ContactSerializer,
        responses={
            200: ContactSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def patch(self, request):
        serializer = ContactSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    """Handles user logout by blacklisting refresh token."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="User Logout",
        description="Blacklist the provided refresh token to log out the user.",
        request={
            "type": "object",
            "properties": {
                "refresh": {"type": "string", "description": "JWT refresh token"}
            },
            "required": ["refresh"]
        },
        responses={
            205: OpenApiResponse(description="Successfully logged out"),
            400: OpenApiResponse(description="Invalid token"),
            401: OpenApiResponse(description="Unauthorized"),
        }
    )
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ContactView(generics.ListCreateAPIView):
    """Handles listing and creating contacts with role-based field access."""
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on user roles and viewable fields."""
        accessible_fields = get_accessible_fields('contacts', 'view', self.request.user)
        if not accessible_fields:
            return Contact.objects.none()
        return Contact.objects.all()

    @extend_schema(
        summary="List Contacts",
        description="Retrieve a list of contacts, filtered by user role permissions from settings.",
        responses={
            200: ContactSerializer(many=True),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create Contact",
        description="Create a new contact, restricted by role-based editable fields.",
        request=ContactSerializer,
        responses={
            201: ContactSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def post(self, request, *args, **kwargs):
        accessible_fields = get_accessible_fields('contacts', 'edit', request.user)
        if not accessible_fields:
            return Response(
                {"detail": "No editable fields allowed for your role"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().post(request, *args, **kwargs)

class ContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Handles retrieving, updating, and deleting a contact with role-based field access."""
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on user roles and viewable fields."""
        accessible_fields = get_accessible_fields('contacts', 'view', self.request.user)
        if not accessible_fields:
            return Contact.objects.none()
        return Contact.objects.all()

    @extend_schema(
        summary="Get Contact",
        description="Retrieve a specific contact by ID, filtered by user role permissions from settings.",
        responses={
            200: ContactSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update Contact",
        description="Update a contact (partial update), restricted by role-based editable fields or owner status.",
        request=ContactSerializer,
        responses={
            200: ContactSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def patch(self, request, *args, **kwargs):
        contact = self.get_object()
        is_owner = request.user.id == contact.id
        accessible_fields = get_accessible_fields('contacts', 'edit', request.user)
        if not (is_owner or accessible_fields):
            return Response(
                {"detail": "No editable fields allowed for your role and you are not the owner"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete Contact",
        description="Delete a contact, restricted by role-based permissions or owner status.",
        responses={
            204: OpenApiResponse(description="Successfully deleted"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def delete(self, request, *args, **kwargs):
        contact = self.get_object()
        is_owner = request.user.id == contact.id
        accessible_fields = get_accessible_fields('contacts', 'edit', request.user)
        if not (is_owner or accessible_fields):
            return Response(
                {"detail": "No editable fields allowed for your role and you are not the owner"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().delete(request, *args, **kwargs)

class VerifyEmailView(APIView):
    """Handles email verification using a code."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Verify Email",
        description="Verify a user's email address using the provided verification code.",
        request=VerifyEmailSerializer,
        responses={
            200: OpenApiResponse(description="Email verified successfully"),
            400: OpenApiResponse(description="Invalid or expired code, or email already verified"),
        }
    )
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email'].lower()
            user = Contact.objects.get(email=email)
            user.is_email_verified = True
            user.verification_code = None
            user.verification_code_expiry = None
            user.save()
            return Response({"msg": "Email verified successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)