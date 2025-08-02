# 
# PURPOSE: Universal CRUD views that handle ANY table across ALL apps
# UNIVERSAL API: Core implementation of query, save, get, delete, clone operations
# REPLACES: Individual hardcoded views for each table type (addresses, phones, emails, etc.)
# TEAM NOTE: This is the heart of the Universal API - one set of views handles all tables
# ARCHITECTURE: Recreates 30-year-old 4D database universal table access in modern Django
# TABLES: Works with any table registered in TABLE_REGISTRY (addresses, phones, emails, domains, contacts)
# PATTERN: Uses dynamic model loading and serialization for any Django model
# SECURITY: Requires login authentication for all operations
# FEATURES: 
#   - Dynamic model class loading from any app
#   - Automatic serializer generation
#   - Table registry for configuration
#   - Universal CRUD operations
#   - Background task support (django-q)

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
    
    # TABLE_REGISTRY - Comprehensive registry for all Universal API tables
    # TEAM NOTE: Add new tables here to make them available via Universal API
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
    
    def get(self, request, table_name):
        """Universal management interface for any table"""
        if table_name not in self.TABLE_REGISTRY:
            return JsonResponse({'error': f'Table {table_name} not found in registry'}, status=404)
        
        table_config = self.TABLE_REGISTRY[table_name]
        
        # Get the model class dynamically
        try:
            model_class = apps.get_model(table_config['app'], table_config['model'])
        except LookupError:
            return JsonResponse({'error': f'Model {table_config["model"]} not found'}, status=404)
        
        # Get contact_id filter if provided
        contact_id = request.GET.get('contact_id')
        
        # Query the data
        queryset = model_class.objects.all()
        if contact_id and hasattr(model_class, 'contact'):
            queryset = queryset.filter(contact_id=contact_id)
        
        # Serialize the data
        data = []
        for obj in queryset:
            item = {'id': obj.pk}
            for field in table_config['list_fields']:
                if hasattr(obj, field):
                    value = getattr(obj, field)
                    if hasattr(value, 'isoformat'):  # DateTime objects
                        value = value.isoformat()
                    item[field] = value
            data.append(item)
        
        # Return JSON for API calls or template for web
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({'status': 'success', 'data': data})
        
        # Render template for web interface
        context = {
            'table_name': table_name,
            'data': data,
            'table_config': table_config,
            'contact_id': contact_id,
        }
        
        template_name = f'communications/manage_{table_name}.html'
        try:
            return render(request, template_name, context)
        except:
            # Fallback to generic template
            return render(request, 'core/universal_manage.html', context)


class UniversalQueryView(LoginRequiredMixin, View):
    """Universal query endpoint for any table"""
    
    def post(self, request):
        """Handle Universal API query requests"""
        try:
            data = json.loads(request.body)
            table_name = data.get('table_name')
            
            if table_name not in UniversalCRUDView.TABLE_REGISTRY:
                return JsonResponse({'status': 'error', 'message': f'Table {table_name} not found'}, status=404)
            
            table_config = UniversalCRUDView.TABLE_REGISTRY[table_name]
            model_class = apps.get_model(table_config['app'], table_config['model'])
            
            # Build query
            queryset = model_class.objects.all()
            
            # Apply filters from request
            filters = data.get('filters', {})
            for field, value in filters.items():
                if hasattr(model_class, field):
                    queryset = queryset.filter(**{field: value})
            
            # Apply search
            search = data.get('search', '')
            if search and 'search_fields' in table_config:
                q_objects = Q()
                for field in table_config['search_fields']:
                    q_objects |= Q(**{f'{field}__icontains': search})
                queryset = queryset.filter(q_objects)
            
            # Serialize results
            results = []
            for obj in queryset:
                item = {'id': obj.pk}
                for field in table_config['list_fields']:
                    if hasattr(obj, field):
                        value = getattr(obj, field)
                        if hasattr(value, 'isoformat'):
                            value = value.isoformat()
                        item[field] = value
                results.append(item)
            
            return JsonResponse({
                'status': 'success',
                'data': results,
                'count': len(results)
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


class UniversalSaveView(LoginRequiredMixin, View):
    """Universal save endpoint for any table"""
    
    def post(self, request):
        """Handle Universal API save requests"""
        try:
            data = json.loads(request.body)
            table_name = data.get('table_name')
            
            if table_name not in UniversalCRUDView.TABLE_REGISTRY:
                return JsonResponse({'status': 'error', 'message': f'Table {table_name} not found'}, status=404)
            
            table_config = UniversalCRUDView.TABLE_REGISTRY[table_name]
            model_class = apps.get_model(table_config['app'], table_config['model'])
            
            # Get or create object
            obj_id = data.get('id')
            if obj_id:
                obj = get_object_or_404(model_class, pk=obj_id)
            else:
                obj = model_class()
            
            # Update fields
            for field, value in data.items():
                if field not in ['table_name', 'id'] and hasattr(obj, field):
                    setattr(obj, field, value)
            
            # Save object
            obj.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Record saved successfully',
                'id': obj.pk
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


class UniversalGetView(LoginRequiredMixin, View):
    """Universal get endpoint for any table"""
    
    def post(self, request):
        """Handle Universal API get requests"""
        try:
            data = json.loads(request.body)
            table_name = data.get('table_name')
            obj_id = data.get('id')
            
            if table_name not in UniversalCRUDView.TABLE_REGISTRY:
                return JsonResponse({'status': 'error', 'message': f'Table {table_name} not found'}, status=404)
            
            table_config = UniversalCRUDView.TABLE_REGISTRY[table_name]
            model_class = apps.get_model(table_config['app'], table_config['model'])
            
            obj = get_object_or_404(model_class, pk=obj_id)
            
            # Serialize object
            result = {'id': obj.pk}
            for field in obj._meta.fields:
                value = getattr(obj, field.name)
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                result[field.name] = value
            
            return JsonResponse({
                'status': 'success',
                'data': result
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


class UniversalDeleteView(LoginRequiredMixin, View):
    """Universal delete endpoint for any table"""
    
    def post(self, request):
        """Handle Universal API delete requests"""
        try:
            data = json.loads(request.body)
            table_name = data.get('table_name')
            obj_id = data.get('id')
            
            if table_name not in UniversalCRUDView.TABLE_REGISTRY:
                return JsonResponse({'status': 'error', 'message': f'Table {table_name} not found'}, status=404)
            
            table_config = UniversalCRUDView.TABLE_REGISTRY[table_name]
            model_class = apps.get_model(table_config['app'], table_config['model'])
            
            obj = get_object_or_404(model_class, pk=obj_id)
            obj.delete()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Record deleted successfully'
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


class UniversalCloneView(LoginRequiredMixin, View):
    """Universal clone endpoint for any table"""
    
    def post(self, request):
        """Handle Universal API clone requests"""
        try:
            data = json.loads(request.body)
            table_name = data.get('table_name')
            obj_id = data.get('id')
            
            if table_name not in UniversalCRUDView.TABLE_REGISTRY:
                return JsonResponse({'status': 'error', 'message': f'Table {table_name} not found'}, status=404)
            
            table_config = UniversalCRUDView.TABLE_REGISTRY[table_name]
            model_class = apps.get_model(table_config['app'], table_config['model'])
            
            original = get_object_or_404(model_class, pk=obj_id)
            
            # Clone the object
            clone = model_class()
            for field in original._meta.fields:
                if field.name != 'id' and not field.primary_key:
                    setattr(clone, field.name, getattr(original, field.name))
            
            clone.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Record cloned successfully',
                'id': clone.pk
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
