import os

# Ensure Django settings are configured for test imports that access settings at import-time
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webclerk3_api.settings")

# Do not call django.setup() here — let pytest-django manage Django setup and test DB creation.

# All former shell-script exclusions have been deleted.
# If new non-test files appear, add them here.


import pytest


def _ensure_company_profile():
    """Company profile with the standard ida sequences and default Terms.
    Transaction documents cannot be numbered, or invoices given a due date, without them."""
    import copy
    from apps.core.models import Setting
    from apps.accounts.models import Term
    from common.ida import DEFAULT_SEQUENCES

    company = Setting.objects.filter(purpose="wc:company_profile").first() or Setting(
        ida="company-profile", name="Company Profile", purpose="wc:company_profile", scope="system", config={})
    config = dict(company.config or {})
    if company.pk and "sequences" in config and "receivables" in config:
        return
    config.setdefault("sequences", copy.deepcopy(DEFAULT_SEQUENCES))
    # Receivables need a default Term: an invoice without terms must still get a due date.
    config.setdefault("receivables", {"default_term": "N30"})
    Term.objects.get_or_create(ida="N30", defaults={"name": "N30", "description": "Net 30 Days", "days_due": 30, "is_active": True})
    Term.objects.get_or_create(ida="DOR", defaults={"name": "DOR", "description": "Due on Receipt", "days_due": 0, "is_active": True})
    company.config = config
    company._setting_create_authorized = True
    company._setting_update_authorized = True
    company.save()


def _ensure_model_access():
    """Every model starts with the install defaults: superuser/admin/agent lists.

    Positive lists: a database with no wc:model access shows nothing, even to a
    superuser. A new install gets these from seed_model_definitions; the test
    database gets the same, from the same function (access.default_access).
    """
    from apps.core.constants.model_registry import MODEL_REGISTRY
    from apps.core.models import Setting
    from apps.core.services import access

    if Setting.objects.filter(purpose="wc:model", config__access__roles__has_key="superuser").exists():
        return
    for meta in MODEL_REGISTRY.values():
        key = meta.key
        try:
            acc = access.default_access(key)
        except Exception:
            continue          # a registry entry with no Django model has no leaves
        s = Setting.objects.filter(purpose="wc:model", parent_model=key).first() or Setting(
            purpose="wc:model", parent_model=key, ida=f"wc-model-{key}", name=f"{key} model", config={})
        config = dict(s.config or {})
        config["access"] = acc
        s.config = config
        s._setting_create_authorized = True
        s._setting_update_authorized = True
        s.save()
    access.clear_cache()


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Created once at database setup so Django TestCase classes (setUpTestData) see it too."""
    with django_db_blocker.unblock():
        _ensure_company_profile()
        _ensure_model_access()


@pytest.fixture(autouse=True)
def _company_profile_after_flush(request):
    """transaction=True tests flush the database after each test, which removes the
    company profile; restore it before any test that uses the database."""
    marker = request.node.get_closest_marker("django_db")
    uses_db = marker is not None or {"db", "transactional_db"} & set(request.fixturenames)
    if not uses_db:
        return
    request.getfixturevalue("transactional_db" if (marker and marker.kwargs.get("transaction")) else "db")
    _ensure_company_profile()
    _ensure_model_access()
