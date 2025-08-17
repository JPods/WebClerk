# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/views/notused/action_management_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from datetime import datetime

# --- RECOMMENDED: Import your role-based access utility ---
# from common.role_access import get_role_settings, can_user_edit, can_user_view

class ManageActionsView(LoginRequiredMixin, View):
    """Manage user actions"""

    # Existing: This view lists actions linked to the current user by searching for their id or uuid in the refs field.
    # TODO: For better performance and security, consider using a utility function or cached role-based access logic
    #       (see settings table and role-based access recommendations) to filter actions by user permissions/roles,
    #       instead of string matching in refs. This will make permission checks more robust and maintainable.

    # ADD: Use get_role_settings() to filter actions by user role and allowed view fields.

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        # Existing: Get user actions using the same method as contact view
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
        
        # ADD: Optionally, filter fields in each action based on role's allowed "view" fields from settings.

        context = {
            'user': user,
            'actions': actions,
        }
        return render(request, 'core/manage_actions.html', context)

class AddActionView(LoginRequiredMixin, View):
    """Add new action"""

    # Existing: This view creates a new action and links it to the current user via the refs JSON field.
    # TODO: Consider enforcing role-based field-level permissions (from settings table) when creating actions,
    #       so only allowed fields are set per user role.

    # ADD: Use can_user_edit('actions', user.role, field) to restrict which fields can be set.

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from core.models.action import Action
            
            # Existing: Create new action
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
            
            # ADD: Only set fields allowed by role's "edit" array in settings for "actions" table.

            action.save()
            messages.success(request, 'Action added successfully!')
            
        except Exception as e:
            messages.error(request, f'Error adding action: {str(e)}')
        
        return redirect('/manage-actions/')

class EditActionView(LoginRequiredMixin, View):
    """Edit existing action"""

    # Existing: This view allows editing an action only if the current user is linked in refs.
    # TODO: For more granular control, check the user's role and allowed edit fields from the settings table,
    #       and only permit editing fields listed in the role's "edit" array for the "actions" table.

    # ADD: Use can_user_edit('actions', user.role, field) to restrict which fields can be edited.

    def get(self, request, action_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from core.models.action import Action
            action = get_object_or_404(Action, id=action_id)
            
            # Existing: Verify user owns this action
            user_id_str = str(request.user.id)
            user_uuid_str = str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            
            if not (action.refs and isinstance(action.refs, dict) and 
                   (user_id_str in str(action.refs) or 
                    (user_uuid_str and user_uuid_str in str(action.refs)))):
                messages.error(request, 'Permission denied.')
                return redirect('/manage-actions/')
            
            # ADD: Optionally, filter fields in action based on role's allowed "view" fields.

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
            
            # Existing: Verify user owns this action
            user_id_str = str(request.user.id)
            user_uuid_str = str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            
            if not (action.refs and isinstance(action.refs, dict) and 
                   (user_id_str in str(action.refs) or 
                    (user_uuid_str and user_uuid_str in str(action.refs)))):
                messages.error(request, 'Permission denied.')
                return redirect('/manage-actions/')
            
            # Existing: Update action
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
            
            # ADD: Only update fields allowed by role's "edit" array in settings for "actions" table.

            action.save()
            messages.success(request, 'Action updated successfully!')
            
        except Exception as e:
            messages.error(request, f'Error updating action: {str(e)}')
        
        return redirect('/manage-actions/')

class DeleteActionView(LoginRequiredMixin, View):
    """Delete action"""

    # Existing: This view deletes an action only if the current user is linked in refs.
    # TODO: Optionally, enforce role-based delete permissions using the settings table,
    #       so only users with the correct role can delete actions.

    # ADD: Use can_user_edit('actions', user.role, 'delete') or similar to check delete permission.

    def post(self, request, action_id):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        try:
            from core.models.action import Action
            action = get_object_or_404(Action, id=action_id)
            
            # Existing: Verify user owns this action
            user_id_str = str(request.user.id)
            user_uuid_str = str(request.user.uuid) if hasattr(request.user, 'uuid') else None
            
            if not (action.refs and isinstance(action.refs, dict) and 
                   (user_id_str in str(action.refs) or 
                    (user_uuid_str and user_uuid_str in str(action.refs)))):
                messages.error(request, 'Permission denied.')
                return redirect('/manage-actions/')
            
            # ADD: Check if user has delete permission for actions table.

            action.delete()
            messages.success(request, 'Action deleted successfully!')
            
        except Exception as e:
            messages.error(request, f'Error deleting action: {str(e)}')
        
        return redirect('/manage-actions/')
