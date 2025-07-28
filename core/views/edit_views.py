from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from ..models import Contact
from ..models.contact_model import Contact
import json

class EditProfileView(LoginRequiredMixin, View):
    """Edit contact profile information"""
    
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        # Get role choices for the form
        role_choices = Contact.ROLE_CHOICES
        
        context = {
            'user': request.user,
            'role_choices': role_choices,
        }
        return render(request, 'edit_profile.html', context)
    
    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        user = request.user
        
        try:
            # Update basic fields
            user.prefix = request.POST.get('prefix', '').strip()
            user.name_first = request.POST.get('name_first', '').strip()
            user.name_middle = request.POST.get('name_middle', '').strip()
            user.name_last = request.POST.get('name_last', '').strip()
            user.suffix = request.POST.get('suffix', '').strip()
            user.email = request.POST.get('email', '').strip()
            user.salutation = request.POST.get('salutation', '').strip()
            user.company = request.POST.get('company', '').strip()
            user.attention = request.POST.get('attention', '').strip()
            user.rank = request.POST.get('rank', '').strip()
            user.comment = request.POST.get('comment', '').strip()
            user.comment_alert = request.POST.get('comment_alert', '').strip()
            
            # Handle publish level
            publish_str = request.POST.get('publish', '').strip()
            user.publish = int(publish_str) if publish_str else None
            
            # Handle roles (multiple selection)
            selected_roles = request.POST.getlist('role')
            user.role = selected_roles if selected_roles else []
            
            # Handle default role
            user.role_default = request.POST.get('role_default', '').strip() or None
            
            # Handle checkboxes
            user.is_active = 'is_active' in request.POST
            user.is_staff = 'is_staff' in request.POST
            
            # Validate required fields
            if not user.name_first or not user.name_last or not user.email:
                messages.error(request, 'First name, last name, and email are required.')
                return render(request, 'edit_profile.html', {
                    'user': user,
                    'role_choices': Contact.ROLE_CHOICES,
                })
            
            user.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('/profile/')
            
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
            return render(request, 'edit_profile.html', {
                'user': user,
                'role_choices': Contact.ROLE_CHOICES,
            })

class ManageAddressesView(LoginRequiredMixin, View):
    """Manage user addresses"""
    
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        # Get user addresses using the same method as profile view
        user = request.user
        user_id_str = str(user.id)
        user_uuid_str = str(user.uuid) if hasattr(user, 'uuid') else None
        
        addresses = []
        try:
            from communications.models.address import Address
            all_addresses = Address.objects.all()
            for address in all_addresses:
                if address.refs and isinstance(address.refs, dict):
                    if (user_id_str in str(address.refs) or 
                        (user_uuid_str and user_uuid_str in str(address.refs))):
                        addresses.append(address)
        except (ImportError, AttributeError):
            addresses = []
        
        context = {
            'user': user,
            'addresses': addresses,
        }
        return render(request, 'manage_addresses.html', context)

class AddAddressView(LoginRequiredMixin, View):
    """Add new address"""
    
    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from communications.models.address import Address
            
            # Create new address
            address = Address()
            address.address_type = request.POST.get('address_type', '').strip()
            address.address1 = request.POST.get('address1', '').strip()
            address.address2 = request.POST.get('address2', '').strip()
            address.city = request.POST.get('city', '').strip()
            address.state = request.POST.get('state', '').strip()
            address.zip = request.POST.get('zip', '').strip()
            address.country = request.POST.get('country', '').strip()
            address.instructions = request.POST.get('instructions', '').strip()
            address.comment = request.POST.get('comment', '').strip()
            
            # Link to user via refs JSON field
            if not address.refs:
                address.refs = {}
            if 'links' not in address.refs:
                address.refs['links'] = []
            
            # Add user reference
            user_ref = {
                'type': 'contact',
                'id': request.user.id,
                'uuid': str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            }
            address.refs['links'].append(user_ref)
            
            address.save()
            messages.success(request, 'Address added successfully!')
            
        except Exception as e:
            messages.error(request, f'Error adding address: {str(e)}')
        
        return redirect('/manage-addresses/')

class EditAddressView(LoginRequiredMixin, View):
    """Edit existing address"""
    
    def post(self, request, address_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from communications.models.address import Address
            address = get_object_or_404(Address, id=address_id)
            
            # Verify user owns this address
            user_id_str = str(request.user.id)
            user_uuid_str = str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            
            if not (address.refs and isinstance(address.refs, dict) and 
                   (user_id_str in str(address.refs) or 
                    (user_uuid_str and user_uuid_str in str(address.refs)))):
                messages.error(request, 'Permission denied.')
                return redirect('/manage-addresses/')
            
            # Update address
            address.address_type = request.POST.get('address_type', '').strip()
            address.address1 = request.POST.get('address1', '').strip()
            address.address2 = request.POST.get('address2', '').strip()
            address.city = request.POST.get('city', '').strip()
            address.state = request.POST.get('state', '').strip()
            address.zip = request.POST.get('zip', '').strip()
            address.country = request.POST.get('country', '').strip()
            address.instructions = request.POST.get('instructions', '').strip()
            address.comment = request.POST.get('comment', '').strip()
            
            address.save()
            messages.success(request, 'Address updated successfully!')
            
        except Exception as e:
            messages.error(request, f'Error updating address: {str(e)}')
        
        return redirect('/manage-addresses/')

class DeleteAddressView(LoginRequiredMixin, View):
    """Delete address"""
    
    def post(self, request, address_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from communications.models.address import Address
            address = get_object_or_404(Address, id=address_id)
            
            # Verify user owns this address
            user_id_str = str(request.user.id)
            user_uuid_str = str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            
            if not (address.refs and isinstance(address.refs, dict) and 
                   (user_id_str in str(address.refs) or 
                    (user_uuid_str and user_uuid_str in str(address.refs)))):
                messages.error(request, 'Permission denied.')
                return redirect('/manage-addresses/')
            
            address.delete()
            messages.success(request, 'Address deleted successfully!')
            
        except Exception as e:
            messages.error(request, f'Error deleting address: {str(e)}')
        
        return redirect('/manage-addresses/')
