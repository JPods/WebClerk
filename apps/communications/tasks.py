# path: apps/communications/tasks.py
from celery import shared_task

@shared_task
def hello():
    # Example: check roles, permissions, or custom logic
    return {'success': False, 'message': 'Only superusers can assign admin role.'}

@shared_task
def save_pre_contact(data):
    # Implement your logic to save pre-contact data
    return {'success': True, 'message': 'Pre-contact data saved successfully.'}

@shared_task
def save_post_contact(data):
    # Implement your logic to save post-contact data
    return {'success': True, 'message': 'Post-contact data saved successfully.'}    

def user_id_is_superuser(user_id):
    # Implement your logic here
    return True