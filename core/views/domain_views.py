from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse

class ManageDomainsView(LoginRequiredMixin, View):
    """Manage user domains"""
    
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        # Get user domains using the same method as contact view
        user = request.user
        user_id_str = str(user.id)
        user_uuid_str = str(user.uuid) if hasattr(user, 'uuid') else None
        
        domains = []
        try:
            from communications.models.domain import Domain
            all_domains = Domain.objects.all()
            for domain in all_domains:
                if domain.refs and isinstance(domain.refs, dict):
                    if (user_id_str in str(domain.refs) or 
                        (user_uuid_str and user_uuid_str in str(domain.refs))):
                        domains.append(domain)
        except (ImportError, AttributeError):
            domains = []
        
        context = {
            'user': user,
            'domains': domains,
        }
        return render(request, 'communications/manage_domains.html', context)

class AddDomainView(LoginRequiredMixin, View):
    """Add new domain"""
    
    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from communications.models.domain import Domain
            
            # Create new domain
            domain = Domain()
            domain.domain_name = request.POST.get('domain_name', '').strip().lower()
            domain.domain_type = request.POST.get('domain_type', '').strip()
            domain.description = request.POST.get('description', '').strip()
            domain.instructions = request.POST.get('instructions', '').strip()
            domain.comment = request.POST.get('comment', '').strip()
            
            # Link to user via refs JSON field
            if not domain.refs:
                domain.refs = {}
            if 'links' not in domain.refs:
                domain.refs['links'] = []
            
            # Add user reference
            user_ref = {
                'type': 'contact',
                'id': request.user.id,
                'uuid': str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            }
            domain.refs['links'].append(user_ref)
            
            domain.save()
            messages.success(request, 'Domain added successfully!')
            
        except Exception as e:
            messages.error(request, f'Error adding domain: {str(e)}')
        
        return redirect('/manage-domains/')

class EditDomainView(LoginRequiredMixin, View):
    """Edit existing domain"""
    
    def get(self, request, domain_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from communications.models.domain import Domain
            domain = get_object_or_404(Domain, id=domain_id)
            
            # Verify user owns this domain
            user_id_str = str(request.user.id)
            user_uuid_str = str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            
            if not (domain.refs and isinstance(domain.refs, dict) and 
                   (user_id_str in str(domain.refs) or 
                    (user_uuid_str and user_uuid_str in str(domain.refs)))):
                messages.error(request, 'Permission denied.')
                return redirect('/manage-domains/')
            
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
            from communications.models.domain import Domain
            domain = get_object_or_404(Domain, id=domain_id)
            
            # Verify user owns this domain
            user_id_str = str(request.user.id)
            user_uuid_str = str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            
            if not (domain.refs and isinstance(domain.refs, dict) and 
                   (user_id_str in str(domain.refs) or 
                    (user_uuid_str and user_uuid_str in str(domain.refs)))):
                messages.error(request, 'Permission denied.')
                return redirect('/manage-domains/')
            
            # Update domain
            domain.domain_name = request.POST.get('domain_name', '').strip().lower()
            domain.domain_type = request.POST.get('domain_type', '').strip()
            domain.description = request.POST.get('description', '').strip()
            domain.instructions = request.POST.get('instructions', '').strip()
            domain.comment = request.POST.get('comment', '').strip()
            
            domain.save()
            messages.success(request, 'Domain updated successfully!')
            
        except Exception as e:
            messages.error(request, f'Error updating domain: {str(e)}')
        
        return redirect('/manage-domains/')

class DeleteDomainView(LoginRequiredMixin, View):
    """Delete domain"""
    
    def post(self, request, domain_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from communications.models.domain import Domain
            domain = get_object_or_404(Domain, id=domain_id)
            
            # Verify user owns this domain
            user_id_str = str(request.user.id)
            user_uuid_str = str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            
            if not (domain.refs and isinstance(domain.refs, dict) and 
                   (user_id_str in str(domain.refs) or 
                    (user_uuid_str and user_uuid_str in str(domain.refs)))):
                messages.error(request, 'Permission denied.')
                return redirect('/manage-domains/')
            
            domain.delete()
            messages.success(request, 'Domain deleted successfully!')
            
        except Exception as e:
            messages.error(request, f'Error deleting domain: {str(e)}')
        
        return redirect('/manage-domains/')
