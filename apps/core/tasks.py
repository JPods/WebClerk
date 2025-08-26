# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/tasks.py
from celery import shared_task
from apps.core.services import view_edit_access

@shared_task
def celery_startup_task():
    view_edit_access.reload_access_data()
    print("Access rules loaded in Celery worker.")

@shared_task
def save_pre(table_name, data):
    # Dynamically call a table-specific pre-save task if it exists
    func_name = f"{table_name.rstrip('s')}_save_pre"
    if func_name in globals():
        return globals()[func_name](data)
    # Default: do nothing
    return {'success': True}

@shared_task
def save_post(table_name, data):
    # Dynamically call a table-specific post-save task if it exists
    print("Post-save for:", table_name)
    func_name = f"{table_name.rstrip('s')}_save_post"
    if func_name in globals():
        return globals()[func_name](data)
    # Default: do nothing
    return {'success': True}

# Example table-specific pre/post tasks
def contact_save_pre(data):
    # Custom logic for contacts before save
    print("Pre-save for contact:", data)
    return {'success': True}

def contact_save_post(data):
    # Custom logic for contacts after save
    print("Post-save for contact:", data)
    return {'success': True}