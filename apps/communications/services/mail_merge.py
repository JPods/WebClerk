"""
Letter / Email Template Service (Mail Merge)
=============================================

Template-based document generation and email sending. Templates are stored
as Document records (model_name='template' or 'letter'). Placeholders use
{{field}} syntax with support for nested fields like {{customer.display_name}}.

All datetimes are UTC (Axiom 14).
"""
from __future__ import annotations

import copy
import logging
import re
import time
from typing import Any, Dict, List, Optional

from django.apps import apps as dj_apps
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

# Regex for {{field.subfield}} placeholders
_PLACEHOLDER_RE = re.compile(r"\{\{(\w+(?:\.\w+)*)\}\}")


def _now_ms() -> int:
    return int(time.time() * 1000)


def _resolve_field(obj, field_path: str) -> str:
    """Resolve a dotted field path against an object or dict.

    Supports:
        - Django model attributes
        - JSON dict fields (metadata, refs, financial, etc.)
        - Nested paths like customer.financial.customer.aging.total

    Returns the string representation of the value, or '' if not found.
    """
    parts = field_path.split(".")
    current = obj

    for part in parts:
        if current is None:
            return ""

        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            val = getattr(current, part)
            # If it's a FK, follow it
            if hasattr(val, "pk"):
                current = val
            elif callable(val) and not isinstance(val, type):
                try:
                    current = val()
                except Exception:
                    return ""
            else:
                current = val
        else:
            return ""

    if current is None:
        return ""
    return str(current)


def _load_record(model_name: str, record_id: int):
    """Load a record by model name and ID.

    Supports common model names across the codebase.
    """
    model_map = {
        "order": ("transactions", "Order"),
        "invoice": ("transactions", "Invoice"),
        "proposal": ("transactions", "Proposal"),
        "purchase": ("transactions", "Purchase"),
        "payment": ("transactions", "Payment"),
        "contact": ("core", "Contact"),
        "orgbase": ("orgs", "OrgBase"),
        "org": ("orgs", "OrgBase"),
        "customer": ("orgs", "OrgBase"),
        "vendor": ("orgs", "OrgBase"),
        "item": ("products", "Item"),
        "document": ("docs", "Document"),
        "project": ("transactions", "Project"),
    }

    key = model_name.lower().strip()
    if key not in model_map:
        raise ValueError(f"Unknown model: {model_name}")

    app_label, cls_name = model_map[key]
    Model = dj_apps.get_model(app_label, cls_name)

    try:
        return Model.objects.get(pk=record_id)
    except Model.DoesNotExist:
        raise ValueError(f"{cls_name} #{record_id} not found")


def _build_merge_context(record) -> Dict[str, Any]:
    """Build a flat + nested context dict from a record for template merging.

    Includes the record itself plus related objects accessible via FK:
    customer, vendor, contact, etc.
    """
    ctx: Dict[str, Any] = {"record": record}

    # Add the record's direct fields
    for field in record._meta.get_fields():
        name = getattr(field, "name", None) or getattr(field, "attname", None)
        if name:
            try:
                ctx[name] = getattr(record, name, None)
            except Exception:
                pass

    # Follow common FK relationships
    for fk_name in ("customer", "vendor", "manufacturer", "contact"):
        try:
            related = getattr(record, fk_name, None)
            if related and hasattr(related, "pk"):
                ctx[fk_name] = related
        except Exception:
            pass

    # Company name from settings
    ctx["company_name"] = getattr(settings, "COMPANY_NAME", "")
    if not ctx["company_name"]:
        ctx["company_name"] = getattr(settings, "SITE_NAME", "WebClerk")

    return ctx


def _merge_text(template_text: str, context: Dict[str, Any]) -> str:
    """Replace all {{field}} placeholders in text with values from context."""
    if not template_text:
        return ""

    def replacer(match):
        field_path = match.group(1)
        # Try direct context keys first
        parts = field_path.split(".")
        root = parts[0]

        if root in context:
            obj = context[root]
            if len(parts) == 1:
                return str(obj) if obj is not None else ""
            remaining = ".".join(parts[1:])
            return _resolve_field(obj, remaining)

        # Try resolving against the record itself
        record = context.get("record")
        if record:
            return _resolve_field(record, field_path)

        return ""

    return _PLACEHOLDER_RE.sub(replacer, template_text)


def _get_recipient_info(record, context: Dict[str, Any]) -> Dict[str, str]:
    """Extract recipient email and name from the record context."""
    email = ""
    name = ""

    # Try contact first
    contact = context.get("contact")
    if contact:
        email = getattr(contact, "email", "") or ""
        name = getattr(contact, "display_name", "") or getattr(contact, "name", "") or ""

    # Fall back to customer org
    if not email:
        customer = context.get("customer")
        if customer:
            email = getattr(customer, "email", "") or ""
            name = getattr(customer, "attention", "") or getattr(customer, "name", "") or ""

    # Fall back to record-level email
    if not email:
        email = getattr(record, "email", "") or ""

    if not name:
        name = getattr(record, "attention", "") or ""

    return {"email": email, "name": name}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def merge_template(
    template_id: int,
    record_model: str,
    record_id: int,
) -> Dict[str, Any]:
    """Load a Document template and merge with record data.

    Args:
        template_id: PK of the Document template
        record_model: model name of the record to merge with
        record_id: PK of the record

    Returns:
        {subject, body_html, body_text, recipient_email, recipient_name}
    """
    Document = dj_apps.get_model("docs", "Document")
    try:
        template = Document.objects.get(pk=template_id)
    except Document.DoesNotExist:
        raise ValueError(f"Template #{template_id} not found")

    # Verify it is a template
    if template.model_name not in ("template", "letter", "email_template"):
        raise ValueError(
            f"Document #{template_id} is not a template (model_name={template.model_name})"
        )

    record = _load_record(record_model, record_id)
    context = _build_merge_context(record)

    # Merge body
    body_html = _merge_text(template.body or "", context)
    body_text = strip_tags(body_html)

    # Merge subject (from template name or data.subject)
    tmpl_data = template.data or {}
    subject_template = tmpl_data.get("subject", "") or template.name or ""
    subject = _merge_text(subject_template, context)

    # Recipient
    recipient = _get_recipient_info(record, context)

    return {
        "subject": subject,
        "body_html": body_html,
        "body_text": body_text,
        "recipient_email": recipient["email"],
        "recipient_name": recipient["name"],
        "template_id": template_id,
        "template_name": template.name or "",
    }


def preview_merge(
    template_id: int,
    record_model: str,
    record_id: int,
) -> Dict[str, Any]:
    """Preview a template merge without sending.

    Same as merge_template — returns preview data for UI confirmation.

    Returns:
        {subject, body_html, body_text, recipient_email, recipient_name}
    """
    result = merge_template(template_id, record_model, record_id)
    result["preview"] = True
    return result


def get_available_templates(
    model_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List available letter/email templates.

    Args:
        model_name: optional filter by template's target model
            (stored in template.data.target_model)

    Returns:
        [{id, name, model_name, description}]
    """
    Document = dj_apps.get_model("docs", "Document")
    qs = Document.objects.filter(
        model_name__in=["template", "letter", "email_template"]
    ).order_by("name")

    templates = []
    for doc in qs:
        # Optional filter by target model
        if model_name:
            tmpl_data = doc.data or {}
            target = tmpl_data.get("target_model", "")
            if target and target.lower() != model_name.lower():
                continue

        templates.append({
            "id": doc.pk,
            "ida": getattr(doc, "ida", ""),
            "name": doc.name or "",
            "model_name": doc.model_name or "",
            "description": doc.description or "",
        })

    return templates


@transaction.atomic
def send_email(
    template_id: int,
    record_model: str,
    record_id: int,
    to_email: Optional[str] = None,
    contact_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Merge template and send via Django email backend.

    Args:
        template_id: PK of the template Document
        record_model: model name of the target record
        record_id: PK of the target record
        to_email: override recipient email
        contact_id: optional contact to log against

    Returns:
        {sent, to, subject, dt_sent}
    """
    merged = merge_template(template_id, record_model, record_id)

    recipient = to_email or merged["recipient_email"]
    if not recipient:
        raise ValueError("No recipient email available — provide to_email or ensure record has contact email")

    subject = merged["subject"]
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@webclerk.com")

    try:
        send_mail(
            subject=subject,
            message=merged["body_text"],
            from_email=from_email,
            recipient_list=[recipient],
            html_message=merged["body_html"],
            fail_silently=False,
        )
    except Exception as e:
        logger.error("send_email failed: template=%s record=%s/%s to=%s: %s",
                      template_id, record_model, record_id, recipient, e)
        return {
            "sent": False,
            "to": recipient,
            "subject": subject,
            "error": str(e),
        }

    dt_sent = _now_ms()

    # Log the send in the record's metadata.communications[]
    try:
        record = _load_record(record_model, record_id)
        meta = copy.deepcopy(getattr(record, "metadata", None) or {})
        comms = meta.setdefault("communications", [])
        if not isinstance(comms, list):
            comms = []
        comms.append({
            "type": "email",
            "template_id": template_id,
            "to": recipient,
            "subject": subject,
            "dt_sent": dt_sent,
            "contact_id": contact_id,
        })
        meta["communications"] = comms
        record.metadata = meta
        record.save(update_fields=["metadata", "dt_modified", "version"])
    except Exception as e:
        logger.warning("send_email: failed to log communication on record: %s", e)

    return {
        "sent": True,
        "to": recipient,
        "subject": subject,
        "dt_sent": dt_sent,
    }


def bulk_send(
    template_id: int,
    record_model: str,
    record_ids: List[int],
) -> Dict[str, Any]:
    """Send merged template to multiple records.

    Args:
        template_id: PK of the template Document
        record_model: model name for all records
        record_ids: list of record PKs

    Returns:
        {sent, failed, errors}
    """
    sent = 0
    failed = 0
    errors = []

    for rid in record_ids:
        try:
            result = send_email(template_id, record_model, rid)
            if result.get("sent"):
                sent += 1
            else:
                failed += 1
                errors.append({
                    "record_id": rid,
                    "error": result.get("error", "send returned False"),
                })
        except Exception as e:
            failed += 1
            errors.append({
                "record_id": rid,
                "error": str(e),
            })

    return {
        "sent": sent,
        "failed": failed,
        "errors": errors,
    }
