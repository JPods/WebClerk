from django.shortcuts import render
from django.apps import apps
from core.view_config import VIEW_CONFIG
from core.utils import get_list_display_fields

def admin_dashboard(request):
    app_list = []
    app_configs = list(apps.get_app_configs())
    for app_config in app_configs:
        models = []
        for model in app_config.get_models():
            models.append({
                "name": model._meta.verbose_name_plural.title(),
                "object_name": model._meta.model_name,
                "app_label": app_config.label,  # Add app_label for later use
            })
        if models:
            app_list.append({
                "name": app_config.verbose_name.title(),
                "models": models,
            })

    selected_model = request.GET.get("model")
    model_list = []
    selected_record = None
    fields = []
    record_id = request.GET.get("record_id")
    if selected_model:
        # Find the correct app_label for the selected model
        model_class = None
        for app_config in app_configs:
            try:
                model_class = apps.get_model(app_config.label, selected_model)
                if model_class:
                    model_list = model_class.objects.all()
                    if record_id:
                        try:
                            selected_record = model_class.objects.get(id=record_id)
                        except model_class.DoesNotExist:
                            selected_record = None
                    break
            except LookupError:
                continue
        if selected_record:
            fields = [
                {'label': field.verbose_name, 'value': getattr(selected_record, field.name)}
                for field in model_class._meta.fields
            ]
    context = {
        "app_list": app_list,
        "model_list": model_list,
        "selected_model": selected_model,
        "selected_record": selected_record,
        "fields": fields,
    }
    return render(request, "admin/admin3.html", context)

def admin3_view(request):
    model_name = request.GET.get('model')
    record_id = request.GET.get('record_id')
    selected_record = None
    fields = []
    list_fields = []
    all_fields = []

    model = None
    if model_name:
        for app_config in apps.get_app_configs():
            try:
                model = apps.get_model(app_config.label, model_name)
                if model:
                    break
            except LookupError:
                continue

    model_list = model.objects.all() if model else []

    if model:
        list_fields = get_list_display_fields(model)
        all_fields = [field for field in model._meta.fields]

    role = getattr(request.user, 'role', 'user')
    detail_fields = get_fields_for_role(role, model_name, 'detail')

    if model and record_id:
        try:
            selected_record = model.objects.get(id=record_id)
            fields = [
                {'label': field.verbose_name, 'value': getattr(selected_record, field.name)}
                for field in model._meta.fields if field.name in detail_fields
            ]
        except model.DoesNotExist:
            selected_record = None
            fields = []

    # Build app_list similar to admin_dashboard
    app_list = []
    for app_config in apps.get_app_configs():
        models = []
        for model_obj in app_config.get_models():
            models.append({
                "name": model_obj._meta.verbose_name_plural.title(),
                "object_name": model_obj._meta.model_name,
            })
        if models:
            app_list.append({
                "name": app_config.verbose_name.title(),
                "models": models,
            })

    context = {
        'app_list': app_list,
        'model_list': model_list,
        'selected_model': model_name,
        'selected_record': selected_record,
        'fields': fields,
        'list_fields': list_fields,
        'detail_fields': detail_fields,
        'all_fields': all_fields,
    }
    return render(request, 'admin/admin3.html', context)

def get_fields_for_role(role, model_name, view_type):
    return VIEW_CONFIG.get(role, {}).get(model_name, {}).get(view_type, [])