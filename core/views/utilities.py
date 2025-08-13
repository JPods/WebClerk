from django.http import JsonResponse
from django.views import View

# Example: role-based access utility
def get_field_access(field_name, user_role, settings_record):
    """
    Returns access permissions for a field based on user role and settings.
    """
    access = settings_record.get(field_name, {}).get('access', {})
    can_view = user_role in access.get('view', [])
    can_edit = user_role in access.get('edit', [])
    return {'can_view': can_view, 'can_edit': can_edit}

class FieldAccessView(View):
    def get(self, request):
        field_name = request.GET.get('field')
        user_role = request.GET.get('role')
        # You would load settings_record from your DB or config
        # For demo, use a static example:
        settings_record = {
            "email": {"access": {"view": ["admin", "user"], "edit": ["admin"]}},
            "phone": {"access": {"view": ["admin", "user"], "edit": ["admin", "user"]}},
        }
        if not field_name or not user_role:
            return JsonResponse({'success': False, 'error': 'field and role required'}, status=400)
        access = get_field_access(field_name, user_role, settings_record)
        return JsonResponse({'success': True, 'access': access})