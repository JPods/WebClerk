from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from datetime import datetime

class ManageActionsView(LoginRequiredMixin, View):
    """Manage user actions"""
    
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        # Get user actions using the same method as contact view
        user = request.user
        user_id_str = str(user.id)
        user_uuid_str = str(user.uuid) if hasattr(user, 'uuid') else None
        
        actions = []
        try:
            from core.models.action import Action
            all_actions = Action.objects.all()
            for action in all_actions:
                if action.refs and isinstance(action.refs, dict):
                    if (user_id_str in str(action.refs) or 
                        (user_uuid_str and user_uuid_str in str(action.refs))):
                        actions.append(action)
        except (ImportError, AttributeError):
            actions = []
        
        context = {
            'user': user,
            'actions': actions,
        }
        return render(request, 'core/manage_actions.html', context)

class AddActionView(LoginRequiredMixin, View):
    """Add new action"""
    
    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from core.models.action import Action
            
            # Create new action
            action = Action()
            action.action_title = request.POST.get('action_title', '').strip()
            action.action_type = request.POST.get('action_type', '').strip()
            action.description = request.POST.get('description', '').strip()
            action.status = request.POST.get('status', 'pending').strip()
            action.priority = request.POST.get('priority', '').strip()
            action.assigned_to = request.POST.get('assigned_to', '').strip()
            action.comment = request.POST.get('comment', '').strip()
            
            # Handle due date
            due_date_str = request.POST.get('due_date', '').strip()
            if due_date_str:
                try:
                    action.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    action.due_date = None
            
            # Link to user via refs JSON field
            if not action.refs:
                action.refs = {}
            if 'links' not in action.refs:
                action.refs['links'] = []
            
            # Add user reference
            user_ref = {
                'type': 'contact',
                'id': request.user.id,
                'uuid': str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            }
            action.refs['links'].append(user_ref)
            
            action.save()
            messages.success(request, 'Action added successfully!')
            
        except Exception as e:
            messages.error(request, f'Error adding action: {str(e)}')
        
        return redirect('/manage-actions/')

class EditActionView(LoginRequiredMixin, View):
    """Edit existing action"""
    
    def get(self, request, action_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from core.models.action import Action
            action = get_object_or_404(Action, id=action_id)
            
            # Verify user owns this action
            user_id_str = str(request.user.id)
            user_uuid_str = str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            
            if not (action.refs and isinstance(action.refs, dict) and 
                   (user_id_str in str(action.refs) or 
                    (user_uuid_str and user_uuid_str in str(action.refs)))):
                messages.error(request, 'Permission denied.')
                return redirect('/manage-actions/')
            
            context = {
                'action': action,
                'user': request.user,
            }
            return render(request, 'edit_action.html', context)
            
        except Exception as e:
            messages.error(request, f'Error loading action: {str(e)}')
            return redirect('/manage-actions/')
    
    def post(self, request, action_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from core.models.action import Action
            action = get_object_or_404(Action, id=action_id)
            
            # Verify user owns this action
            user_id_str = str(request.user.id)
            user_uuid_str = str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            
            if not (action.refs and isinstance(action.refs, dict) and 
                   (user_id_str in str(action.refs) or 
                    (user_uuid_str and user_uuid_str in str(action.refs)))):
                messages.error(request, 'Permission denied.')
                return redirect('/manage-actions/')
            
            # Update action
            action.action_title = request.POST.get('action_title', '').strip()
            action.action_type = request.POST.get('action_type', '').strip()
            action.description = request.POST.get('description', '').strip()
            action.status = request.POST.get('status', 'pending').strip()
            action.priority = request.POST.get('priority', '').strip()
            action.assigned_to = request.POST.get('assigned_to', '').strip()
            action.comment = request.POST.get('comment', '').strip()
            
            # Handle due date
            due_date_str = request.POST.get('due_date', '').strip()
            if due_date_str:
                try:
                    action.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    action.due_date = None
            else:
                action.due_date = None
            
            action.save()
            messages.success(request, 'Action updated successfully!')
            
        except Exception as e:
            messages.error(request, f'Error updating action: {str(e)}')
        
        return redirect('/manage-actions/')

class DeleteActionView(LoginRequiredMixin, View):
    """Delete action"""
    
    def post(self, request, action_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from core.models.action import Action
            action = get_object_or_404(Action, id=action_id)
            
            # Verify user owns this action
            user_id_str = str(request.user.id)
            user_uuid_str = str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            
            if not (action.refs and isinstance(action.refs, dict) and 
                   (user_id_str in str(action.refs) or 
                    (user_uuid_str and user_uuid_str in str(action.refs)))):
                messages.error(request, 'Permission denied.')
                return redirect('/manage-actions/')
            
            action.delete()
            messages.success(request, 'Action deleted successfully!')
            
        except Exception as e:
            messages.error(request, f'Error deleting action: {str(e)}')
        
        return redirect('/manage-actions/')
