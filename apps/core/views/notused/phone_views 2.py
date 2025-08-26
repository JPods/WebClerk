# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/views/notused/phone_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse

class ManagePhonesView(LoginRequiredMixin, View):
    """Manage user phone numbers"""
    
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        # Get user phones using the same method as contact view
        user = request.user
        user_id_str = str(user.id)
        user_uuid_str = str(user.uuid) if hasattr(user, 'uuid') else None
        
        phones = []
        try:
            from apps.communications.models.phone import Phone
            all_phones = Phone.objects.all()
            for phone in all_phones:
                if phone.refs and isinstance(phone.refs, dict):
                    if (user_id_str in str(phone.refs) or 
                        (user_uuid_str and user_uuid_str in str(phone.refs))):
                        phones.append(phone)
        except (ImportError, AttributeError):
            phones = []
        
        context = {
            'user': user,
            'phones': phones,
        }
        return render(request, 'communications/manage_phones.html', context)

class AddPhoneView(LoginRequiredMixin, View):
    """Add new phone number"""
    
    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from apps.communications.models.phone import Phone
            
            # Create new phone
            phone = Phone()
            phone.phone_type = request.POST.get('phone_type', '').strip()
            phone.phone_number = request.POST.get('phone_number', '').strip()
            phone.extension = request.POST.get('extension', '').strip()
            phone.instructions = request.POST.get('instructions', '').strip()
            phone.comment = request.POST.get('comment', '').strip()
            
            # Link to user via refs JSON field
            if not phone.refs:
                phone.refs = {}
            if 'links' not in phone.refs:
                phone.refs['links'] = []
            
            # Add user reference
            user_ref = {
                'type': 'contact',
                'id': request.user.id,
                'uuid': str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            }
            phone.refs['links'].append(user_ref)
            
            phone.save()
            messages.success(request, 'Phone number added successfully!')
            
        except Exception as e:
            messages.error(request, f'Error adding phone number: {str(e)}')
        
        return redirect('/manage-phones/')

class EditPhoneView(LoginRequiredMixin, View):
    """Edit existing phone number"""
    
    def get(self, request, phone_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from apps.communications.models.phone import Phone
            phone = get_object_or_404(Phone, id=phone_id)
            
            # Verify user owns this phone
            user_id_str = str(request.user.id)
            user_uuid_str = str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            
            if not (phone.refs and isinstance(phone.refs, dict) and 
                   (user_id_str in str(phone.refs) or 
                    (user_uuid_str and user_uuid_str in str(phone.refs)))):
                messages.error(request, 'Permission denied.')
                return redirect('/manage-phones/')
            
            context = {
                'phone': phone,
                'user': request.user,
            }
            return render(request, 'edit_phone.html', context)
            
        except Exception as e:
            messages.error(request, f'Error loading phone: {str(e)}')
            return redirect('/manage-phones/')
    
    def post(self, request, phone_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from apps.communications.models.phone import Phone
            phone = get_object_or_404(Phone, id=phone_id)
            
            # Verify user owns this phone
            user_id_str = str(request.user.id)
            user_uuid_str = str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            
            if not (phone.refs and isinstance(phone.refs, dict) and 
                   (user_id_str in str(phone.refs) or 
                    (user_uuid_str and user_uuid_str in str(phone.refs)))):
                messages.error(request, 'Permission denied.')
                return redirect('/manage-phones/')
            
            # Update phone
            phone.phone_type = request.POST.get('phone_type', '').strip()
            phone.phone_number = request.POST.get('phone_number', '').strip()
            phone.extension = request.POST.get('extension', '').strip()
            phone.instructions = request.POST.get('instructions', '').strip()
            phone.comment = request.POST.get('comment', '').strip()
            
            phone.save()
            messages.success(request, 'Phone number updated successfully!')
            
        except Exception as e:
            messages.error(request, f'Error updating phone number: {str(e)}')
        
        return redirect('/manage-phones/')

class DeletePhoneView(LoginRequiredMixin, View):
    """Delete phone number"""
    
    def post(self, request, phone_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from apps.communications.models.phone import Phone
            phone = get_object_or_404(Phone, id=phone_id)
            
            # Verify user owns this phone
            user_id_str = str(request.user.id)
            user_uuid_str = str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            
            if not (phone.refs and isinstance(phone.refs, dict) and 
                   (user_id_str in str(phone.refs) or 
                    (user_uuid_str and user_uuid_str in str(phone.refs)))):
                messages.error(request, 'Permission denied.')
                return redirect('/manage-phones/')
            
            phone.delete()
            messages.success(request, 'Phone number deleted successfully!')
            
        except Exception as e:
            messages.error(request, f'Error deleting phone number: {str(e)}')
        
        return redirect('/manage-phones/')
