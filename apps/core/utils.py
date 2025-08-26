from django.contrib import admin
from django.apps import apps

def get_list_display_fields(model):
    # Find the registered admin class for the model
    model_admin = admin.site._registry.get(model)
    if model_admin and hasattr(model_admin, 'list_display'):
        return model_admin.list_display
    # Fallback: show all fields
    return [field.name for field in model._meta.fields]