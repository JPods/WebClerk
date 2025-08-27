# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/common/sandbox/tasks.py
from celery import shared_task

@shared_task
def hello():
    # Example: check roles, permissions, or custom logic
    return {'success': False, 'message': 'Only superusers can assign admin role.'}


def user_id_is_superuser(user_id):
    # Implement your logic here
    return True