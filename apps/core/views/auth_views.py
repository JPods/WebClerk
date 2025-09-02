# path: apps/core/views/auth_views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.views import View
from django.contrib import messages
from django.urls import reverse
from apps.core.serializers import RegisterSerializer
from apps.core.models import Contact
from django.apps import apps

class SignupView(View):
    template_name = 'signup.html'  # Updated path
    
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
                
                # If serializer.save() returns a list, get the first user
                if isinstance(user, list):
                    user = user[0] if user else None

                # Log them in if user is valid
                if user is not None:
                    login(request, user)
                    messages.success(request, f'Welcome {user.get_full_name()}! Your account has been created.')
                    # Redirect to their profile
                    return redirect('/contact/')
                else:
                    messages.error(request, 'Account creation failed: No user returned.')
                    return render(request, self.template_name)
                
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
    template_name = 'login.html'  # Updated path
    
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

def admin_dashboard(request):
    # Example context, adjust as needed
    app_list = []
    for app_config in apps.get_app_configs():
        models = []
        for model in app_config.get_models():
            models.append({
                "name": model._meta.verbose_name_plural.title(),
                "object_name": model._meta.model_name,
            })
        if models:
            app_list.append({
                "name": app_config.verbose_name.title(),
                "models": models,
            })
    selected_model = request.GET.get("model")
    model_class = None
    if selected_model:
        try:
            model_class = apps.get_model("core", selected_model)
        except LookupError:
            messages.error(request, "Selected model not found.")
    
    # Fetching the records for the selected model
    model_list = []
    selected_record = None
    if model_class:
        model_list = model_class.objects.all()
        # If a specific record is selected, fetch it
        record_id = request.GET.get("id")
        if record_id:
            try:
                selected_record = model_list.get(id=record_id)
            except model_class.DoesNotExist:
                messages.error(request, "Selected record not found.")
    
    # Prepare fields for the selected record
    fields = []
    if selected_record and hasattr(selected_record, "metadata"):
        fields = [
            {"label": k, "value": v}
            for k, v in selected_record.metadata.items()
        ]
    context = {
        "app_list": app_list,
        "model_list": model_list,
        "selected_model": selected_model,
        "selected_record": selected_record,
        "fields": fields,
    }
    return render(request, "admin/admin3.html", context)