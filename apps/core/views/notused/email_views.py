from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse

class ManageEmailsView(LoginRequiredMixin, View):
    """Manage user email addresses"""
    
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        # Get user emails using the same method as contact view
        user = request.user
        user_id_str = str(user.id)
        user_uuid_str = str(user.uuid) if hasattr(user, 'uuid') else None
        
        emails = []
        try:
            from apps.communications.models.email import Email
            all_emails = Email.objects.all()
            for email in all_emails:
                if email.refs and isinstance(email.refs, dict):
                    if (user_id_str in str(email.refs) or 
                        (user_uuid_str and user_uuid_str in str(email.refs))):
                        emails.append(email)
        except (ImportError, AttributeError):
            emails = []
        
        context = {
            'user': user,
            'emails': emails,
        }
        return render(request, 'communications/manage_emails.html', context)

class AddEmailView(LoginRequiredMixin, View):
    """Add new email address"""
    
    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from apps.communications.models.email import Email
            
            # Create new email
            email = Email()
            email.email = request.POST.get('email', '').strip()
            email.name = request.POST.get('name', '').strip()
            email.attention = request.POST.get('attention', '').strip()
            email.opt_out = request.POST.get('opt_out', '').strip()
            email.comment = request.POST.get('comment', '').strip()
            email.is_primary = request.POST.get('is_primary') == 'true'
            email.is_verified = request.POST.get('is_verified') == 'true'
            
            # Set verified_at if marked as verified
            if email.is_verified:
                from django.utils import timezone
                email.dt_verified = timezone.now()
            
            # Link to user via refs JSON field
            if not email.refs:
                email.refs = {}
            if 'links' not in email.refs:
                email.refs['links'] = []
            
            # Add user reference
            user_ref = {
                'type': 'contact',
                'id': request.user.id,
                'uuid': str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            }
            email.refs['links'].append(user_ref)
            
            email.save()
            messages.success(request, 'Email address added successfully!')
            
        except Exception as e:
            messages.error(request, f'Error adding email address: {str(e)}')
        
        return redirect('/manage-emails/')

class EditEmailView(LoginRequiredMixin, View):
    """Edit existing email address"""
    
    def get(self, request, email_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from apps.communications.models.email import Email
            email = get_object_or_404(Email, id=email_id)
            
            # Verify user owns this email
            user_id_str = str(request.user.id)
            user_uuid_str = str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            
            if not (email.refs and isinstance(email.refs, dict) and 
                   (user_id_str in str(email.refs) or 
                    (user_uuid_str and user_uuid_str in str(email.refs)))):
                messages.error(request, 'Permission denied.')
                return redirect('/manage-emails/')
            
            context = {
                'email': email,
                'user': request.user,
            }
            return render(request, 'communications/edit_email.html', context)
            
        except Exception as e:
            messages.error(request, f'Error loading email: {str(e)}')
            return redirect('/manage-emails/')
    
    def post(self, request, email_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from apps.communications.models.email import Email
            email = get_object_or_404(Email, id=email_id)
            
            # Verify user owns this email
            user_id_str = str(request.user.id)
            user_uuid_str = str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            
            if not (email.refs and isinstance(email.refs, dict) and 
                   (user_id_str in str(email.refs) or 
                    (user_uuid_str and user_uuid_str in str(email.refs)))):
                messages.error(request, 'Permission denied.')
                return redirect('/manage-emails/')
            
            # Update email
            email.email = request.POST.get('email', '').strip()
            email.name = request.POST.get('name', '').strip()
            email.attention = request.POST.get('attention', '').strip()
            email.opt_out = request.POST.get('opt_out', '').strip()
            email.comment = request.POST.get('comment', '').strip()
            
            # Handle new boolean fields
            email.is_primary = request.POST.get('is_primary') == 'true'
            was_verified = email.is_verified
            email.is_verified = request.POST.get('is_verified') == 'true'
            
            # Set verified_at if newly verified
            if email.is_verified and not was_verified:
                from django.utils import timezone
                email.dt_verified = timezone.now()
            elif not email.is_verified:
                email.dt_verified = None
            
            email.save()
            messages.success(request, 'Email address updated successfully!')
            
        except Exception as e:
            messages.error(request, f'Error updating email address: {str(e)}')
        
        return redirect('/manage-emails/')

class DeleteEmailView(LoginRequiredMixin, View):
    """Delete email address"""
    
    def post(self, request, email_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from apps.communications.models.email import Email
            email = get_object_or_404(Email, id=email_id)
            
            # Verify user owns this email
            user_id_str = str(request.user.id)
            user_uuid_str = str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            
            if not (email.refs and isinstance(email.refs, dict) and 
                   (user_id_str in str(email.refs) or 
                    (user_uuid_str and user_uuid_str in str(email.refs)))):
                messages.error(request, 'Permission denied.')
                return redirect('/manage-emails/')
            
            email.delete()
            messages.success(request, 'Email address deleted successfully!')
            
        except Exception as e:
            messages.error(request, f'Error deleting email address: {str(e)}')
        
        return redirect('/manage-emails/')
