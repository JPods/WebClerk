from django.shortcuts import render
from django.apps import apps

def admin_dashboard(request):
    # Get all apps and models
    app_list = []
    for app_config in apps.get_app_configs():
        models = []
        for model in app_config.get_models():
            models.append({
                "name": model._meta.verbose_name_plural.title(),
                "object_name": model._meta.model_name,
            })
        if models:
            app_list.append({
                "name": app_config.verbose_name.title(),
                "models": models,
            })

    # Get selected model and records
    selected_model = request.GET.get("model")
    model_list = []
    selected_record = None
    if selected_model:
        for app in app_list:
            for model in app["models"]:
                if model["object_name"] == selected_model:
                    model_class = apps.get_model(app["name"].lower(), selected_model)
                    model_list = model_class.objects.all()
                    record_id = request.GET.get("record_id")
                    if record_id:
                        try:
                            selected_record = model_class.objects.get(id=record_id)
                        except model_class.DoesNotExist:
                            selected_record = None
    context = {
        "app_list": app_list,
        "model_list": model_list,
        "selected_model": selected_model,
        "selected_record": selected_record,
    }
    return render(request, "admin/admin3.html", context)