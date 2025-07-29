from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.http import HttpResponse
from ..models import Contact

@method_decorator(csrf_exempt, name='dispatch')
class WebContactView(View):
    """User contact view that displays contact information and all related data"""
    
    def dispatch(self, request, *args, **kwargs):
        # Bypass DRF authentication by ensuring we're using Django's session auth
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        # Debug: Check authentication status
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to view your contact.')
            return redirect('web-login')
        
        user = request.user
        
        # Get related data - since this system uses JSON refs instead of ForeignKeys
        context = {
            'user': user,
            'addresses': [],
            'phones': [],
            'emails': [],
            'domains': [],
            'actions': [],
        }
        
        # Try to get related addresses - check if refs contains user reference
        try:
            from communications.models.address import Address
            # Since the system uses JSON refs, we need to search differently
            # Look for user ID in refs JSON field or try other relationship patterns
            user_id_str = str(user.id)
            user_uuid_str = str(user.uuid) if hasattr(user, 'uuid') else None
            
            addresses = Address.objects.all()
            user_addresses = []
            for address in addresses:
                if address.refs and isinstance(address.refs, dict):
                    # Check if user is referenced in the refs JSON
                    if (user_id_str in str(address.refs) or 
                        (user_uuid_str and user_uuid_str in str(address.refs))):
                        user_addresses.append(address)
            context['addresses'] = user_addresses
        except (ImportError, AttributeError) as e:
            print(f"Address model error: {e}")
            context['addresses'] = []
        
        # Try to get related phone numbers
        try:
            from communications.models.phone import Phone
            phones = Phone.objects.all()
            user_phones = []
            for phone in phones:
                if phone.refs and isinstance(phone.refs, dict):
                    if (user_id_str in str(phone.refs) or 
                        (user_uuid_str and user_uuid_str in str(phone.refs))):
                        user_phones.append(phone)
            context['phones'] = user_phones
        except (ImportError, AttributeError) as e:
            print(f"Phone model error: {e}")
            context['phones'] = []
        
        # Try to get related emails
        try:
            from communications.models.email import Email
            emails = Email.objects.all()
            user_emails = []
            for email in emails:
                if email.refs and isinstance(email.refs, dict):
                    if (user_id_str in str(email.refs) or 
                        (user_uuid_str and user_uuid_str in str(email.refs))):
                        user_emails.append(email)
            context['emails'] = user_emails
        except (ImportError, AttributeError) as e:
            print(f"Email model error: {e}")
            context['emails'] = []
        
        # Try to get related domains
        try:
            from communications.models.domain import Domain
            domains = Domain.objects.all()
            user_domains = []
            for domain in domains:
                if domain.refs and isinstance(domain.refs, dict):
                    if (user_id_str in str(domain.refs) or 
                        (user_uuid_str and user_uuid_str in str(domain.refs))):
                        user_domains.append(domain)
            context['domains'] = user_domains
        except (ImportError, AttributeError) as e:
            print(f"Domain model error: {e}")
            context['domains'] = []
        
        # Try to get related actions - this might have a more direct relationship
        try:
            from core.models.action_model import Action
            # Actions might have a direct relationship with Contact
            # Let's try different approaches
            actions = Action.objects.all()
            user_actions = []
            for action in actions:
                if hasattr(action, 'refs') and action.refs and isinstance(action.refs, dict):
                    if (user_id_str in str(action.refs) or 
                        (user_uuid_str and user_uuid_str in str(action.refs))):
                        user_actions.append(action)
            context['actions'] = user_actions[:10]  # Limit to 10 most recent
        except (ImportError, AttributeError) as e:
            print(f"Action model error: {e}")
            context['actions'] = []
        
        return render(request, 'core/contact.html', context)
