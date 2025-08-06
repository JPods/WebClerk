from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.views import View
from django.contrib import messages
from django.urls import reverse
from core.serializers import RegisterSerializer
from core.models import Contact

class WebSignupView(View):
    template_name = 'auth/signup.html'  # Updated path
    
    def get(self, request):
        return render(request, self.template_name)
    
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
            return render(request, self.template_name)
        
        # Use your existing RegisterSerializer for validation
        serializer = RegisterSerializer(data=form_data)
        
        if serializer.is_valid():
            try:
                # Create user
                user = serializer.save()
                
                # Log them in
                login(request, user)
                
                messages.success(request, f'Welcome {user.get_full_name()}! Your account has been created.')
                
                # Redirect to their profile
                return redirect('/contact/')
                
            except Exception as e:
                messages.error(request, f'Account creation failed: {str(e)}')
                return render(request, self.template_name)
        else:
            # Handle validation errors
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, f'{field.title()}: {error}')
            return render(request, self.template_name)

class WebLoginView(View):
    template_name = 'auth/login.html'  # Updated path
    
    def get(self, request):
        # If already logged in, redirect to profile
        if request.user.is_authenticated:
            return redirect('/contact/')
        return render(request, self.template_name)
    
    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')
        next_url = request.GET.get('next', '/user/')
        
        if not email or not password:
            messages.error(request, 'Please provide both email and password.')
            return render(request, self.template_name)
        
        # Authenticate user
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name()}!')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password.')
            return render(request, self.template_name)

class WebLogoutView(View):
    def get(self, request):
        logout(request)
        messages.info(request, 'You have been logged out successfully.')
        return redirect('/')