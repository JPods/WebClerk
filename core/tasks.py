from celery import shared_task

@shared_task
def contact_save_before(data, user_id=None):
    # Example: check roles, permissions, or custom logic
    if data.get('role') == 'admin' and not user_id_is_superuser(user_id):
        return {'success': False, 'message': 'Only superusers can assign admin role.'}
    return {'success': True}

@shared_task
def contact_save_after(data, user_id=None):
    # Example: send notification, log, etc.
    return {'success': True}

def user_id_is_superuser(user_id):
    # Implement your logic here
    return True