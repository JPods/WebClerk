from django.shortcuts import render
from django.apps import apps

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

    # Get the model class dynamically
    # Use Django's apps.get_model to get the model class by name
    model = None
    if model_name:
        # Search through all app configs to find the model
        for app_config in apps.get_app_configs():
            try:
                model = apps.get_model(app_config.label, model_name)
                if model:
                    break
            except LookupError:
                continue

    # Get the list of records for the selected model
    model_list = model.objects.all() if model else []

    # If a record is selected, fetch it and its fields
    if model and record_id:
        try:
            selected_record = model.objects.get(id=record_id)
            fields = [
                {'label': field.verbose_name, 'value': getattr(selected_record, field.name)}
                for field in model._meta.fields
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
    }
    return render(request, 'admin/admin3.html', context)