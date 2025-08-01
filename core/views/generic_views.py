import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseRedirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.utils import timezone
from django.apps import apps
from django.core.exceptions import ValidationError
from django.views.generic import TemplateView

# Fallback for django-q if not installed yet
try:
    from django_q.tasks import async_task
except ImportError:
    def async_task(func_name, *args, **kwargs):
        print(f"Background task queued: {func_name} with args {args}")

from common.models import default_refs

class UniversalCRUDView(LoginRequiredMixin, View):
    """Universal CRUD operations for ALL tables across ALL apps"""
    
    # TABLE_REGISTRY - Comprehensive registry
    TABLE_REGISTRY = {
        'addresses': {
            'app': 'communications',
            'model': 'Address',
            'serializer': 'AddressSerializer',
            'list_fields': ['id', 'name', 'address1', 'city', 'state', 'postal_code', 'primary'],
            'search_fields': ['name', 'address1', 'city', 'state'],
        },
        'phones': {
            'app': 'communications',
            'model': 'Phone',
            'serializer': 'PhoneSerializer',
            'list_fields': ['id', 'name', 'number', 'phone_type', 'primary'],
            'search_fields': ['name', 'number'],
        },
        'emails': {
            'app': 'communications',
            'model': 'Email',
            'serializer': 'EmailSerializer',
            'list_fields': ['id', 'name', 'email', 'email_type', 'primary', 'verified'],
            'search_fields': ['name', 'email'],
        },
        'domains': {
            'app': 'communications',
            'model': 'Domain',
            'serializer': 'DomainSerializer',
            'list_fields': ['id', 'name', 'domain', 'domain_type', 'active'],
            'search_fields': ['name', 'domain'],
        },
        'contacts': {
            'app': 'core',
            'model': 'Contact',
            'serializer': 'ContactSerializer',
            'list_fields': ['id', 'first_name', 'last_name', 'company', 'title'],
            'search_fields': ['first_name', 'last_name', 'company'],
        },
    }
    
    def get_table_config(self, table_name):
        """Get model and configuration for table"""
        config = self.TABLE_REGISTRY.get(table_name)
        if not config:
            raise ValueError(f"Unknown table: {table_name}")
        return config
    
    def get_model_class(self, config):
        """Dynamically get model class from any app"""
        app_label = config['app']
        model_name = config['model']
        
        try:
            return apps.get_model(app_label, model_name)
        except LookupError:
            raise ValueError(f"Model {model_name} not found in app {app_label}")
    
    def get_serializer_class(self, config):
        """Get serializer - create basic one if needed"""
        from rest_framework import serializers
        
        model_class = self.get_model_class(config)
        
        class BasicSerializer(serializers.ModelSerializer):
            class Meta:
                model = model_class
                fields = '__all__'
        
        return BasicSerializer


class UniversalQueryView(UniversalCRUDView):
    """Universal query endpoint - handles any table"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            table_name = data.pop('table_name')
            
            config = self.get_table_config(table_name)
            model_class = self.get_model_class(config)
            serializer_class = self.get_serializer_class(config)
            
            queryset = model_class.objects.all()[:50]  # Limit for safety
            
            serializer = serializer_class(queryset, many=True)
            
            return JsonResponse({
                'status': 'success',
                'table_name': table_name,
                'count': queryset.count(),
                'data': serializer.data
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)


class UniversalSaveView(UniversalCRUDView):
    """Universal save endpoint"""
    
    def post(self, request):
        return JsonResponse({
            'status': 'error',
            'message': 'Save functionality coming soon'
        }, status=501)


class UniversalGetView(UniversalCRUDView):
    """Get single record"""
    
    def post(self, request):
        return JsonResponse({
            'status': 'error',
            'message': 'Get functionality coming soon'
        }, status=501)


class UniversalDeleteView(UniversalCRUDView):
    """Delete any record"""
    
    def post(self, request):
        return JsonResponse({
            'status': 'error',
            'message': 'Delete functionality coming soon'
        }, status=501)


class UniversalCloneView(UniversalCRUDView):
    """Clone any record"""
    
    def post(self, request):
        return JsonResponse({
            'status': 'error',
            'message': 'Clone functionality coming soon'
        }, status=501)


class UniversalManageView(LoginRequiredMixin, TemplateView):
    """Universal management page"""
    template_name = 'core/universal_manage.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        table_name = kwargs.get('table_name')
        
        context.update({
            'table_name': table_name,
            'message': f'Management page for {table_name} - coming soon!',
            'records': [],
        })
        
        return context
