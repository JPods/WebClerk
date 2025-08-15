from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse

# --- RECOMMENDED: Import your role-based access utility ---
# from common.role_access import get_role_settings, can_user_edit, can_user_view

class ManageDomainsView(LoginRequiredMixin, View):
    """Manage user domains"""

    # Existing: This view lists domains linked to the current user.
    # TODO: For better performance and security, consider using a utility function or cached role-based access logic
    #       (see settings table and role-based access recommendations) to filter domains by user permissions/roles.

    # ADD: Use get_role_settings() to filter domains by user role and allowed view fields.

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        # Existing: Get user domains (customize as needed)
        user = request.user
        domains = []
        try:
            from core.models.domain import Domain
            domains = Domain.objects.all()
        except (ImportError, AttributeError):
            domains = []
        
        # ADD: Optionally, filter fields in each domain based on role's allowed "view" fields from settings.

        context = {
            'user': user,
            'domains': domains,
        }
        return render(request, 'core/manage_domains.html', context)

class AddDomainView(LoginRequiredMixin, View):
    """Add new domain"""

    # Existing: This view creates a new domain.
    # TODO: Consider enforcing role-based field-level permissions (from settings table) when creating domains,
    #       so only allowed fields are set per user role.

    # ADD: Use can_user_edit('domains', user.role, field) to restrict which fields can be set.

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from core.models.domain import Domain
            
            # Existing: Create new domain
            domain = Domain()
            domain.path = request.POST.get('path', '').strip()
            domain.type = request.POST.get('type', '').strip()
            domain.comment = request.POST.get('comment', '').strip()
            
            # ADD: Only set fields allowed by role's "edit" array in settings for "domains" table.

            domain.save()
            messages.success(request, 'Domain added successfully!')
            
        except Exception as e:
            messages.error(request, f'Error adding domain: {str(e)}')
        
        return redirect('/manage-domains/')

class EditDomainView(LoginRequiredMixin, View):
    """Edit existing domain"""

    # Existing: This view allows editing a domain.
    # TODO: For more granular control, check the user's role and allowed edit fields from the settings table,
    #       and only permit editing fields listed in the role's "edit" array for the "domains" table.

    # ADD: Use can_user_edit('domains', user.role, field) to restrict which fields can be edited.

    def get(self, request, domain_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from core.models.domain import Domain
            domain = get_object_or_404(Domain, id=domain_id)
            
            # ADD: Optionally, filter fields in domain based on role's allowed "view" fields.

            context = {
                'domain': domain,
                'user': request.user,
            }
            return render(request, 'edit_domain.html', context)
            
        except Exception as e:
            messages.error(request, f'Error loading domain: {str(e)}')
            return redirect('/manage-domains/')
    
    def post(self, request, domain_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from core.models.domain import Domain
            domain = get_object_or_404(Domain, id=domain_id)
            
            # Existing: Update domain
            domain.path = request.POST.get('path', '').strip()
            domain.type = request.POST.get('type', '').strip()
            domain.comment = request.POST.get('comment', '').strip()
            
            # ADD: Only update fields allowed by role's "edit" array in settings for "domains" table.

            domain.save()
            messages.success(request, 'Domain updated successfully!')
            
        except Exception as e:
            messages.error(request, f'Error updating domain: {str(e)}')
        
        return redirect('/manage-domains/')

class DeleteDomainView(LoginRequiredMixin, View):
    """Delete domain"""

    # Existing: This view deletes a domain.
    # TODO: Optionally, enforce role-based delete permissions using the settings table,
    #       so only users with the correct role can delete domains.

    # ADD: Use can_user_edit('domains', user.role, 'delete') or similar to check delete permission.

    def post(self, request, domain_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from core.models.domain import Domain
            domain = get_object_or_404(Domain, id=domain_id)
            
            # ADD: Check if user has delete permission for domains table.

            domain.delete()
            messages.success(request, 'Domain deleted successfully!')
            
        except Exception as e:
            messages.error(request, f'Error deleting domain: {str(e)}')
        
        return redirect('/manage-domains/')

def custom_save_function(request, data):
    # Implement your custom save logic here
    return JsonResponse({'success': True, 'message': 'Custom save executed'})
