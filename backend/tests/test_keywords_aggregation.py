import pytest

from apps.core.models.contact import Contact
from apps.core.services.record_keywords import build_keywords_for_record


@pytest.mark.django_db
def test_build_keywords_includes_scalar_and_tags_but_not_links_without_refs_setup(monkeypatch):
    # Force empty refs_setup so baseline aggregation behavior is exercised.
    monkeypatch.setattr("apps.core.services.record_keywords.get_keyword_requirements", lambda: {})
    monkeypatch.setattr("apps.core.services.record_keywords.cache_service.get", lambda _key: {})

    contact = Contact.objects.create(
        email="agg-keywords@example.com",
        name_first="Bill",
        name_last="Employee",
        attention="Bill Employee",
        company="WebClerk",
    )

    refs = contact.refs if isinstance(contact.refs, dict) else {}
    refs["links"] = {
        "email": [
            {
                "id": 718,
                "email": "3@3.com",
                "name": "account",
            },
            {
                "id": 721,
                "email": "35@3.com",
                "name": "other",
            },
        ],
        "phone": [{"id": 46, "number": "+1612414421", "name": "primary"}],
        "domain": [{"id": 458, "path": "www.JPods.com/billjames", "status": "active"}],
        "address": [
            {
                "id": 4,
                "full": "3939 East 60th Place Tulsa OK 74135",
                "city": "Tulsa",
            }
        ],
    }
    refs["tags"] = ["vip", "priority_customer", "work", "home", "shit", "fuck"]

    Contact.objects.filter(pk=contact.pk).update(refs=refs)

    keywords = set(build_keywords_for_record("contact", contact.pk))

    assert "bill" in keywords
    assert "employee" in keywords
    assert "webclerk" in keywords
    assert "35@3.com" not in keywords
    # domain is now a property (not a scalar field), so with empty refs_setup
    # it won't appear in baseline keyword extraction unless configured.
    # assert "www.jpods.com/billjames" in keywords
    assert "vip" in keywords
    assert "priority_customer" in keywords
    assert "work" not in keywords
    assert "home" not in keywords
    assert "shit" not in keywords
    assert "fuck" not in keywords
    assert "account" not in keywords
    assert "other" not in keywords
    assert not any("pbkdf2_sha256" in token for token in keywords)
