"""Demo bundle definition — the one list of what a WebClerk sample dataset contains.

Used by:
  pack_demo_bundle --all          export every row of these models from the current DB
  load_demo_data --preserve-ids   load into an EMPTY database keeping original primary keys

Keeping original PKs means every FK column, refs.links id, and line `item.item_id`
stays valid without remapping. Use the uuid-remap loader path for non-empty databases.

Never exported: superusers/staff, credentials, runtime logs, bank statements,
internal projects/actions, connections, bundles.
"""
from __future__ import annotations

import hashlib
import re
from decimal import Decimal
from datetime import datetime, date

# Dependency order: parents before children.
DEMO_BUNDLE_MODELS = [
    "core.Contact",
    "core.UserProfile",          # roles/org scope are read through the profile — portal logins need it
    "communications.Email",
    "communications.Phone",
    "communications.Address",
    "communications.Domain",
    "orgs.OrgBase",
    "accounts.Currency",
    "accounts.Term",
    "accounts.GlAccount",
    "products.Warehouse",
    "products.Item",
    "products.Catalog",
    "products.BillOfMaterial",
    "transactions.Proposal",
    "transactions.ProposalLine",
    "transactions.Order",
    "transactions.OrderLine",
    "transactions.Invoice",
    "transactions.InvoiceLine",
    "transactions.Purchase",
    "transactions.PurchaseLine",
    "transactions.Cash",
    "accounts.GlJournal",
    "communications.Touch",
    "docs.Tag",
    "core.RoleConfig",
    "core.ModelRoleConfig",
    "core.Report",
    "sync.Connection",           # carrier connection templates only, never credentials
]

# Loaded with the bundle but system infrastructure (like Settings): never tagged or removed as demo data.
INFRASTRUCTURE_MODELS = {"core.RoleConfig", "core.ModelRoleConfig", "core.Report", "accounts.Currency", "accounts.Term", "accounts.GlAccount", "sync.Connection"}


def demo_tables_children_first() -> list[str]:
    """DB tables of demo-data models, children before parents (for removal)."""
    from django.apps import apps
    return [apps.get_model(label)._meta.db_table
            for label in reversed(DEMO_BUNDLE_MODELS) if label not in INFRASTRUCTURE_MODELS]


# Columns that point at a contact; references to excluded (privileged) contacts become 0/None.
CONTACT_REF_COLUMNS = {"contact_id", "user_id", "created_by_id", "owner_id"}

# Portal roles whose demo logins keep their (publicly documented) demo password.
PORTAL_DEMO_ROLES = {"user_customer", "user_vendor", "user_manufacturer", "user_rep"}


def privileged_contact_ids():
    from apps.core.models import Contact
    return set(Contact.objects.filter(is_superuser=True).values_list("pk", flat=True)) | \
        set(Contact.objects.filter(is_staff=True).values_list("pk", flat=True))


def serialize_value(val):
    if isinstance(val, Decimal):
        return str(val)
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, (bytes, memoryview)):
        return None
    return val


def serialize_row(obj) -> dict:
    return {f.attname: serialize_value(getattr(obj, f.attname, None)) for f in obj._meta.concrete_fields}


# Contact JSON keys that carry pre-anonymization identity, validation results, or activity history.
CONTACT_HISTORY_KEYS = {
    "config": ("original_mac", "phone_original"),
    "metadata": ("email_history", "email2", "phone", "company", "import_data", "audit_trail",
                 "history", "search_log", "navigation_log", "zb", "databrowser"),
}

# Email domains allowed to appear verbatim in a public bundle.
_ALLOWED_EMAIL_DOMAIN = re.compile(r"(\.fake|\.test|\.invalid|\.local|example\.(com|org|net)|jpods\.com|webclerk\.com)$", re.I)
_EMAIL = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9-]+)((?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})")


def _fake_email(match: re.Match) -> str:
    local, first_label, rest = match.group(1), match.group(2), match.group(3)
    domain = f"{first_label}{rest}"
    if _ALLOWED_EMAIL_DOMAIN.search(domain):
        return match.group(0)
    digest = hashlib.sha1(match.group(0).lower().encode()).hexdigest()[:8]
    return f"user{digest}@{first_label.lower()}.fake"


_PHONE = re.compile(r"(\(?\b)(\d{3})(\)?[-. ])(\d{3})([-. ])(\d{4})\b")


def _fake_phone(match: re.Match) -> str:
    if match.group(4) == "555":
        return match.group(0)
    digest = int(hashlib.sha1(match.group(0).encode()).hexdigest(), 16)
    return f"{match.group(1)}{match.group(2)}{match.group(3)}555{match.group(5)}01{digest % 100:02d}"


_E164_US = re.compile(r"\+1(\d{3})(\d{3})(\d{4})\b")
_BARE_10 = re.compile(r"\b1?(\d{3})(\d{3})(\d{4})\b")
# Bare 10-digit strings are phone numbers only under these keys (elsewhere they may be epoch seconds).
_PHONE_KEYS = re.compile(r"phone|mobile|fax|e164|keywords|search", re.I)


def _fake_digits(match: re.Match, prefix: str) -> str:
    if match.group(2) == "555":
        return match.group(0)
    digest = int(hashlib.sha1(match.group(0).encode()).hexdigest(), 16)
    return f"{prefix}{match.group(1)}55501{digest % 100:02d}"


def scrub_emails(value, _phone_context: bool = False):
    """Replace emails on non-allowed domains with stable .fake addresses and
    phone numbers outside the 555 range with stable 555-01xx numbers."""
    if isinstance(value, str):
        value = _EMAIL.sub(_fake_email, value)
        value = _PHONE.sub(_fake_phone, value)
        value = _E164_US.sub(lambda m: _fake_digits(m, "+1"), value)
        if _phone_context:
            value = _BARE_10.sub(lambda m: _fake_digits(m, ""), value)
        return value
    if isinstance(value, list):
        return [scrub_emails(v, _phone_context) for v in value]
    if isinstance(value, dict):
        return {k: scrub_emails(v, _phone_context or bool(_PHONE_KEYS.search(str(k)))) for k, v in value.items()}
    return value


def strip_contact_history(config: dict | None, metadata: dict | None, prefs: dict | None):
    """Return (config, metadata, prefs) without identity history. Shared by export and DB scrub."""
    config = dict(config or {})
    metadata = dict(metadata or {})
    prefs = dict(prefs or {})
    for key in CONTACT_HISTORY_KEYS["config"]:
        config.pop(key, None)
    for key in CONTACT_HISTORY_KEYS["metadata"]:
        metadata.pop(key, None)
    if isinstance(metadata.get("myCarryOn"), dict):
        metadata["myCarryOn"] = {k: v for k, v in metadata["myCarryOn"].items() if k != "token"}
    prefs["userdefined"] = {}
    return config, metadata, prefs


def sanitize_contact(row: dict) -> dict:
    """Strip authority, credentials and identity history; keep demo portal logins usable."""
    roles = set(((row.get("refs") or {}).get("roles")) or [])
    if not (roles & PORTAL_DEMO_ROLES):
        row["password"] = "!"
    row["is_superuser"] = False
    row["is_staff"] = False
    row["last_login"] = None
    row["config"], row["metadata"], row["prefs"] = strip_contact_history(
        row.get("config"), row.get("metadata"), row.get("prefs"))
    return row


# Settings that hold runtime state computed from data (Alice's aggregates are
# rebuilt by refresh_all). They describe one database; bundles never carry them.
RUNTIME_SETTING_PURPOSES = ("alice:aggregates",)


def sanitize_setting(setting: dict) -> dict:
    """Remove company-identifying and cash-account details from Settings in a public bundle."""
    purpose = setting.get("purpose")
    config = setting.get("config") or {}
    if purpose == "wc:cash_gateway":
        for i, gw in enumerate(config.get("gateway") or []):
            if isinstance(gw, dict):
                gw["name"] = f"account_{i + 1}"
                gw["account"] = f"Demo account {i + 1}"
    if purpose == "wc:company_profile":
        primary = config.get("primary_org")
        if isinstance(primary, dict):
            primary.pop("wc2defaults", None)
        # Bundles are public. Keep city/state/zip (tax origin, shipping origin);
        # drop the tax id, phone, and street lines.
        company = config.get("company")
        if isinstance(company, dict):
            company["tax_id"] = ""
            company["registration_number"] = ""
            company["phone"] = ""
            company["fax"] = ""
            company["address_receiving"] = ""
            address = company.get("address")
            if isinstance(address, dict):
                address["street1"] = ""
                address["street2"] = ""
                company["address_full"] = ", ".join(
                    p for p in (address.get("city"), f'{address.get("state", "")} {address.get("zip", "")}'.strip()) if p)
    setting["config"] = scrub_emails(config)
    return setting


def export_rows(label: str, excluded_contacts: set) -> list[dict]:
    from django.apps import apps
    Model = apps.get_model(label)
    nullable = {f.attname: f.null for f in Model._meta.concrete_fields}
    rows = []
    missing = Model.objects.filter(uuid__isnull=True).count()
    if missing:
        raise ValueError(f"{label}: {missing} rows have no uuid — every bundled record must be uuid-addressable")
    for obj in Model.objects.all().order_by("pk"):
        row = serialize_row(obj)
        if label == "sync.Connection":
            # Only carrier templates ship in the demo, and never with credentials.
            if not (row.get("ida") or "").startswith("conn-carrier-"):
                continue
            creds = (row.get("config") or {}).get("credentials")
            if isinstance(creds, dict):
                row["config"]["credentials"] = {k: "" for k in creds}
        if label == "core.Contact":
            if obj.pk in excluded_contacts:
                continue
            rows.append(sanitize_contact(row))
            continue
        # Contact detail rows and profiles belonging to excluded contacts are not exported.
        if (label.startswith("communications.") and label != "communications.Touch") or label == "core.UserProfile":
            if row.get("contact_id") in excluded_contacts or row.get("user_id") in excluded_contacts:
                continue
        for col in CONTACT_REF_COLUMNS & row.keys():
            if row[col] in excluded_contacts:
                row[col] = None if nullable.get(col) else 0
        rows.append(row)
    return [scrub_emails(r) for r in rows]
