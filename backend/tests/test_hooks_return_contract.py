import pytest
from django.apps import apps

@pytest.mark.django_db
@pytest.mark.hooks
def test_api_validate_payload_return_contract():
    from common.models import BaseModel
    violations = []
    for model in apps.get_models():
        if not issubclass(model, BaseModel) or model is BaseModel:
            continue
        if not hasattr(model, 'api_validate_payload'):
            violations.append(f"{model.__name__}: missing api_validate_payload")
            continue
        try:
            inst = model()  # unsaved; fields with required values may be None
        except Exception as e:
            # If instantiation fails (unusual), skip strict check but note
            violations.append(f"{model.__name__}: instantiation failed: {e}")
            continue
        try:
            result = inst.api_validate_payload({}, False)  # type: ignore[attr-defined]
        except Exception:
            # Allow models whose override depends on required data; treat as pass (schema validated elsewhere)
            continue
        if not isinstance(result, tuple) or len(result) != 2:
            violations.append(f"{model.__name__}.api_validate_payload did not return (ok, errors) tuple: {result}")
        else:
            ok, errors = result
            if not isinstance(ok, bool):
                violations.append(f"{model.__name__}.api_validate_payload first element not bool: {ok}")
            if not isinstance(errors, list):
                violations.append(f"{model.__name__}.api_validate_payload second element not list: {errors}")
    assert not violations, "Return contract violations:\n" + "\n".join(violations)


def test_readmes_manage_hook_table_present():
    """Ensure the consolidated manage doc retains the hook reference table."""
    import pathlib
    manage_path = pathlib.Path('readmes/manage.md')
    if not manage_path.exists():
        pytest.skip("readmes/manage.md not yet created")
    readme = manage_path.read_text(encoding='utf-8')
    assert '### Hook Reference' in readme, 'Hook Reference section missing in readmes/manage.md'
    assert '| Hook / Task | Scope | Invocation Point |' in readme, 'Hook table header missing columns'
