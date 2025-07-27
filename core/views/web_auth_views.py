from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from ..serializers import RegisterSerializer
from ..models import Contact

class WebSignupView(View):
    """Template-based signup view that extends layout.html"""
    
    def get(self, request):
        return render(request, 'signup.html')
    
    def post(self, request):
        # Extract form data
        form_data = {
            'email': request.POST.get('email'),
            'name_first': request.POST.get('name_first'),
            'name_last': request.POST.get('name_last'),
            'password': request.POST.get('password'),
        }
        
        password_confirm = request.POST.get('password_confirm')
        
        # Check if passwords match
        if form_data['password'] != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'signup.html')
        
        # Use the existing serializer for validation
        serializer = RegisterSerializer(data=form_data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                messages.success(request, 'Account created successfully! Please check your email for verification.')
                return redirect('core:web-login')
            except Exception as e:
                messages.error(request, f'Error creating account: {str(e)}')
        else:
            # Handle validation errors
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        
        return render(request, 'signup.html')

class WebLoginView(View):
    """Template-based login view that extends layout.html"""
    
    def get(self, request):
        return render(request, 'login.html')
    
    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            # Find contact by email
            contact = Contact.objects.get(email=email)
            
            # Authenticate using Django's built-in authentication
            # Since Contact extends AbstractBaseUser, we use email as username
            user = authenticate(request, username=contact.email, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, 'Successfully logged in!')
                return redirect('home')  # Redirect to home page
            else:
                messages.error(request, 'Invalid email or password.')
        except Contact.DoesNotExist:
            messages.error(request, 'No account found with this email address.')
        except Exception as e:
            messages.error(request, f'Login error: {str(e)}')
        
        return render(request, 'login.html')

class WebLogoutView(View):
    """Template-based logout view"""
    
    def post(self, request):
        logout(request)
        messages.success(request, 'You have been successfully logged out.')
        return redirect('home')
