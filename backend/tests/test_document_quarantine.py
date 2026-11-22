"""An upload waits in a quarantine folder until a check that applies to it has run and
passed; only then is it moved to permanent storage (Bill, 2026-11-22)."""
import io
import os
from unittest import mock

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.docs.models import Document
from apps.docs.services import document_sanitizer as san

PDF = b"%PDF-1.4\n1 0 obj << /Type /Catalog /OpenAction 2 0 R >> endobj\n%%EOF\n"


def _png() -> bytes:
    from PIL import Image
    out = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(out, format="PNG")
    return out.getvalue()


@pytest.fixture
def box(tmp_path, settings):
    """A private data folder and a signed-in person; the scanner's answer is set per test."""
    settings.DATA_DIR = tmp_path
    from django.contrib.auth import get_user_model
    user = get_user_model().objects.create_user(
        email="q@test.example", password="x", name_first="Q", name_last="T", username="")
    client = APIClient()
    client.force_authenticate(user)
    state = {"scan": ("clean", [])}
    with mock.patch.object(san, "clamav_scan", side_effect=lambda path: state["scan"]):
        yield client, state, tmp_path


def _upload(client, name, content, mime):
    r = client.post("/wcapi/upload/", {"file": SimpleUploadedFile(name, content, content_type=mime)},
                    format="multipart")
    assert r.status_code == 201, r.content
    body = r.json()
    return Document.objects.get(pk=body.get("data", body)["document_id"])


def _files(root, folder):
    return [f for _, _, names in os.walk(root / folder) for f in names]


@pytest.mark.django_db
def test_a_clean_file_is_checked_then_moved_to_permanent_storage(box):
    client, state, root = box
    doc = _upload(client, "terms.pdf", PDF, "application/pdf")
    q = doc.config["quarantine"]
    assert (q["status"], q["sanitized"], q["virus_scan"]) == ("cleared", True, "clean")
    assert q["released_at"] and "PDF has /OpenAction (allowed)" in q["threats_found"]
    assert doc.path["storage"] == "local" and doc.path["key"].startswith("uploads/document/")
    assert _files(root, "quarantine") == [] and len(_files(root, "uploads")) == 1
    assert doc.metadata["virus"]["status"] == "clean" and doc.metadata["virus"]["quarantined"] is False
    r = client.get(f"/wcapi/document/{doc.id}/download/")
    assert r.status_code == 200 and r["X-Content-Type-Options"] == "nosniff"


@pytest.mark.django_db
def test_no_scanner_is_not_a_pass(box):
    client, state, root = box
    state["scan"] = ("not_run", ["virus scanner not reachable"])
    doc = _upload(client, "prices.csv", b"sku,price\nA,1\n", "text/csv")
    q = doc.config["quarantine"]
    assert (q["status"], q["sanitized"], q["virus_scan"]) == ("pending", False, "not_run")
    assert "waiting for a virus scan" in q["reason"]
    assert doc.path["storage"] == "quarantine" and len(_files(root, "quarantine")) == 1
    assert _files(root, "uploads") == []
    r = client.get(f"/wcapi/document/{doc.id}/download/")
    assert r.status_code == 403 and "waiting for a virus scan" in str(r.json())

    # the scanner comes up; the recheck releases what was waiting
    state["scan"] = ("clean", [])
    call_command("quarantine", "--recheck")
    doc.refresh_from_db()
    assert doc.config["quarantine"]["status"] == "cleared" and doc.path["storage"] == "local"
    assert _files(root, "quarantine") == []
    assert client.get(f"/wcapi/document/{doc.id}/download/").status_code == 200


@pytest.mark.django_db
def test_an_image_is_made_safe_by_its_own_check_without_a_scanner(box):
    client, state, root = box
    state["scan"] = ("not_run", ["virus scanner not reachable"])
    doc = _upload(client, "photo.png", _png() + b"<script>hidden</script>", "image/png")
    assert doc.config["quarantine"]["status"] == "cleared"
    stored = (root / doc.path["key"]).read_bytes()
    assert b"hidden" not in stored and stored.startswith(b"\x89PNG")
    assert doc.metadata["virus"]["status"] == "skipped"


@pytest.mark.django_db
@pytest.mark.parametrize("name, content, mime, reason", [
    ("photo.png", b"<html><script>alert(1)</script></html>", "image/png", "not a readable PNG image"),
    ("photo.jpg", _png(), "image/jpeg", "says image/jpeg but holds PNG"),
    ("form.pdf", b"%PDF-1.4\n<< /S /JavaScript /JS (app.alert(1)) >>\n", "application/pdf", "active content: /JS, /JavaScript"),
    ("invoice.pdf", b"<html>not a pdf</html>", "application/pdf", "does not begin as one"),
    ("report.pdf", b"MZ\x90\x00 this is a program", "application/pdf", "Windows executable"),
    ("notes.txt", b"#!/bin/sh\nrm -rf ~\n", "text/plain", "script with an interpreter line"),
])
def test_what_is_refused_stays_in_quarantine(box, name, content, mime, reason):
    client, state, root = box
    doc = _upload(client, name, content, mime)
    q = doc.config["quarantine"]
    assert (q["status"], q["sanitized"]) == ("failed", False) and reason in q["reason"]
    assert doc.path["storage"] == "quarantine" and _files(root, "uploads") == []
    assert client.get(f"/wcapi/document/{doc.id}/download/").status_code == 403


@pytest.mark.django_db
def test_an_infected_file_is_refused_whatever_its_type(box):
    client, state, root = box
    state["scan"] = ("infected", ["Eicar-Test-Signature (FOUND)"])
    doc = _upload(client, "photo.png", _png(), "image/png")
    assert doc.config["quarantine"]["status"] == "failed"
    assert doc.metadata["virus"]["status"] == "infected"
    assert doc.metadata["virus"]["threat"] == "Eicar-Test-Signature (FOUND)"
    assert doc.path["storage"] == "quarantine"


@pytest.mark.django_db
def test_where_athena_is_required_the_file_waits_for_her(box):
    client, state, root = box
    with mock.patch.object(san, "athena_required_for_installation", return_value=True):
        doc = _upload(client, "terms.pdf", PDF, "application/pdf")
    assert doc.config["quarantine"]["status"] == "sanitized"
    assert doc.path["storage"] == "quarantine"
    assert client.get(f"/wcapi/document/{doc.id}/download/").status_code == 403
    san.athena_clear_document(doc, reviewer_id=7)
    doc.refresh_from_db()
    assert doc.config["quarantine"]["status"] == "cleared" and doc.path["storage"] == "local"
    assert _files(root, "quarantine") == []
    assert client.get(f"/wcapi/document/{doc.id}/download/").status_code == 200


@pytest.mark.django_db
def test_a_page_is_handed_over_as_a_download_never_shown_in_place(box):
    client, state, root = box
    doc = _upload(client, "page.html", b"<html><script>alert(1)</script></html>", "text/html")
    r = client.get(f"/wcapi/document/{doc.id}/download/")
    assert r.status_code == 200
    assert r["Content-Disposition"].startswith("attachment")
    assert r["X-Content-Type-Options"] == "nosniff"
    picture = _upload(client, "photo.png", _png(), "image/png")
    assert client.get(f"/wcapi/document/{picture.id}/download/")["Content-Disposition"].startswith("inline")


@pytest.mark.django_db
def test_svg_scripts_are_removed(box):
    client, state, root = box
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" onload="x()"><script>alert(1)</script><rect/></svg>'
    doc = _upload(client, "logo.svg", svg, "image/svg+xml")
    stored = (root / doc.path["key"]).read_bytes()
    assert b"script" not in stored and b"onload" not in stored and b"<rect/>" in stored


def test_the_scanner_that_is_not_there_says_so(settings):
    settings.CLAMD_SOCKET = "/nonexistent/clamd.sock"
    state, findings = san.clamav_scan(__file__)
    assert state == "not_run" and "not reachable at /nonexistent/clamd.sock" in findings[0]
