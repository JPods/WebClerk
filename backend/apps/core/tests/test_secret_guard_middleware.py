"""SecretGuardMiddleware: a password in any JSON write is refused with a 422 before a view runs."""
import json

from django.http import HttpResponse
from django.test import RequestFactory

from common.middleware.secret_guard import SecretGuardMiddleware

rf = RequestFactory()
mw = SecretGuardMiddleware(lambda r: HttpResponse("stored"))


def _post(path, body):
    return mw(rf.post(path, data=json.dumps(body), content_type="application/json"))


def test_note_with_password_is_refused():
    r = _post("/wcapi/action/", {"model": "action", "fields": {"comments": {"notes": "router wifi password is Summer2026!"}}})
    assert r.status_code == 422
    body = json.loads(r.content)
    assert body["error"]["code"] == "secret_detected"
    assert "Summer2026" not in r.content.decode()
    assert body["error"]["fields"] == ["fields.comments.notes"]


def test_clean_note_passes():
    assert _post("/wcapi/action/", {"model": "action", "fields": {"name": "Change the WiFi password"}}).content == b"stored"


def test_password_forms_and_login_are_exempt():
    assert _post("/wcapi/token/", {"email": "a@b.test", "password": "Summer2026!"}).content == b"stored"
    assert _post("/wcapi/contact/", {"model": "contact", "fields": {"password": "Summer2026!"}}).content == b"stored"


def test_alice_chat_is_scanned():
    assert _post("/ai/ask/", {"question": "my postgres is postgres://u:Summer2026@db:5432/x"}).status_code == 422
