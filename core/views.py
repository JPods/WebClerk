from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import RegisterSerializer, ContactSerializer
from rest_framework.permissions import AllowAny
from .models import Contact
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from django.contrib.auth import authenticate
import logging

logger = logging.getLogger(__name__)

class LoginView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        email = request.data.get('email', '').lower()
        password = request.data.get('password', '')
        logger.info(f"Login attempt for email: {email}")
        
        # Explicitly authenticate user
        user = authenticate(request, email=email, password=password)        
        if not user:
            raise AuthenticationFailed('No active account found with the given credentials.')
        if not user.is_active:
            raise AuthenticationFailed('Account is inactive.')
        if not user.is_email_verified:
            raise AuthenticationFailed('Email not verified. Please verify your email to log in.')
        if not user.role:
            raise AuthenticationFailed('Account has no roles assigned. Please contact an administrator.')
        
        return super().post(request, *args, **kwargs)

class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Send verification email
            subject = 'WebClerk 3.0: Verify Your Email'
            message = f'Hi {user.name_first or user.email},\n\nPlease verify your email using this code: {user.verification_code}\nThis code expires in 24 hours.\n\nThank you!'
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProfileView(APIView):
    def get(self, request):
        serializer = ContactSerializer(request.user)
        return Response(serializer.data)

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').lower()
        code = request.data.get('code')
        try:
            contact = Contact.objects.get(email=email, verification_code=code)
            if contact.verification_code_expiry and contact.verification_code_expiry > timezone.now():
                contact.is_email_verified = True
                contact.verification_code = None
                contact.verification_code_expiry = None
                contact.save()
                return Response({"message": "Email verified"}, status=status.HTTP_200_OK)
            return Response({"error": "Invalid or expired code"}, status=status.HTTP_400_BAD_REQUEST)
        except Contact.DoesNotExist:
            return Response({"error": "Invalid email or code"}, status=status.HTTP_400_BAD_REQUEST)