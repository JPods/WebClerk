import inspect
import pytest
from django.apps import apps

EXPECTED_HOOKS = {
    'pre_save_hook': ('self', 'data'),
    'api_validate_payload': ('self', 'data', 'is_update'),
    'post_save_hook': ('self', 'data'),
}

@pytest.mark.django_db
@pytest.mark.hooks
def test_base_model_hooks_contract():
    from common.models import BaseModel
    violations = []
    for model in apps.get_models():
        if not issubclass(model, BaseModel) or model is BaseModel:
            continue
        for hook, expected_params in EXPECTED_HOOKS.items():
            if not hasattr(model, hook):
                violations.append(f"{model.__name__}: missing {hook}")
                continue
            fn = getattr(model, hook)
            # bound function -> inspect on function defined on class
            try:
                sig = inspect.signature(fn)
            except (TypeError, ValueError):
                continue
            params = tuple(p.name for p in sig.parameters.values())
            if params[:len(expected_params)] != expected_params:
                violations.append(f"{model.__name__}.{hook} params {params} != {expected_params}")
    assert not violations, "Hook contract violations:\n" + "\n".join(violations)
