from copy import deepcopy

from django.db import models


# ---------------- Enumerations -----------------
class OrgType(models.TextChoices):
	CUSTOMER = "customer", "Customer"
	VENDOR = "vendor", "Vendor"
	REP = "rep", "Rep"
	EMPLOYEE = "employee", "Employee"
	MANUFACTURER = "manufacturer", "Manufacturer"
	OTHER = "other", "Other"


# ---------------- Aspect JSON defaults ----------
def default_contacts():  # list[{id,name,role,phones:[...],emails:[...]}]
	return []


def default_addresses():
    """Party-keyed address aspect: prime, bill_to, ship_to."""
    return {
        "prime": {"contact_id": None, "company": "", "attention": "", "full_address": "", "instructions": ""},
        "bill_to": {"contact_id": None, "company": "", "attention": "", "full_address": "", "instructions": ""},
        "ship_to": {"contact_id": None, "company": "", "attention": "", "full_address": "", "instructions": ""},
    }


def default_domains():  # list[{domain, verified:bool, dt_verified:int_ms}]
	return []


def default_phones():
    """Party-keyed phone aspect: prime, bill_to, ship_to."""
    return {
        "prime": {"phone_id": None, "number": ""},
        "bill_to": {"phone_id": None, "number": ""},
        "ship_to": {"phone_id": None, "number": ""},
    }


def default_emails():
    """Party-keyed email aspect: prime, bill_to, ship_to."""
    return {
        "prime": {"email_id": None, "email": ""},
        "bill_to": {"email_id": None, "email": ""},
        "ship_to": {"email_id": None, "email": ""},
    }


def default_relations():
	"""{parents, children, linked_ids} — the shape is common.schemas.org_aspects.OrgRelations."""
	from common.schemas.org_aspects import OrgRelations
	return OrgRelations().model_dump()


def default_financial():
	"""Type-keyed financial profile — the shape is common.schemas.org_aspects.OrgFinancial."""
	from common.schemas.org_aspects import OrgFinancial
	return OrgFinancial().model_dump()


def default_docs():  # list[{id, kind, name, size, sha256}]
	return []


def default_connections():  # pointers only, e.g. {"email_svc": "vault:cred:123"}
	return {}

# Legacy defaults for historical migration 0001_initial (kept to allow migrations to load)
def default_access():  # pragma: no cover - legacy
	return {}


def default_data():  # small misc extras (avoid unbounded growth)
	return {}


def default_metrics():  # counters & period aggregates {counts:{}, periods:{"2025Q1":{sales:...}}}
	return {"counts": {}, "periods": {}}


def default_gl_accounts():  # {sales:"4000", expense:"5000", ...}
	return {}


# ---------------- Financial metrics dictionary (UI contract) -----------------
# This dictionary is intended to be the canonical source for compact financial
# metric views (labels + preferred JSON paths + formatting hints).
#
# Consumers can either read the whole dictionary or request per-org-type merged
# specs via get_financial_metrics_spec().

FINANCIAL_METRICS_DICTIONARY_VERSION = 3


def _metric(metric_id: str, label: str, fmt: str, *paths: str) -> dict:
	"""Compact helper to define financial metric specs consistently."""
	return {
		"id": metric_id,
		"label": label,
		"format": fmt,
		"paths": [p for p in paths if p],
	}


ORG_FINANCIAL_METRICS_DICTIONARY = {
	"common": [
		_metric(
			"balance_due",
			"Balance Due",
			"currency",
			"balances.due",
		),
	],
	"customer": [
		_metric(
			"orders_in_period",
			"Orders In Period",
			"count",
			"stats.orders.executed.count",
			"stats.orders.issued.count",
		),
		_metric("sales_mtd", "Sales MTD", "currency", "sales.mtd"),
		_metric("sales_ytd", "Sales YTD", "currency", "sales.ytd"),
		_metric("sales_all_time", "Sales All-Time", "currency", "sales.lifetime"),
		_metric(
			"days_paid",
			"Days Paid",
			"days",
			"cash.days_avg_paid",
			"cash.days_pay",
		),
		_metric("open_orders", "Open Orders", "currency", "balances.open_orders"),
	],
	"vendor": [
		_metric(
			"purchases_in_period",
			"Purchases In Period",
			"count",
			"stats.purchases.executed.count",
			"stats.purchases.issued.count",
		),
		_metric("purchases_mtd", "Purchases MTD", "currency", "purchases.mtd"),
		_metric("purchases_ytd", "Purchases YTD", "currency", "purchases.ytd"),
		_metric(
			"purchases_all_time",
			"Purchases All-Time",
			"currency",
			"purchases.lifetime",
		),
		_metric("days_paid", "Terms Days", "days", "credit.terms_days"),
		_metric("open_pos", "Open POs", "currency", "balances.open_pos"),
	],
	"rep": [
		_metric("commission_ytd", "Commission YTD", "currency", "commissions.ytd"),
		_metric(
			"commission_all_time",
			"Commission All-Time",
			"currency",
			"commissions.lifetime",
		),
		_metric(
			"sales_credited_ytd",
			"Sales Credited YTD",
			"currency",
			"sales_credited.ytd",
		),
	],
	"employee": [
		_metric("payroll_salary", "Salary", "currency", "payroll.salary"),
		_metric("expenses_ytd", "Expenses YTD", "currency", "expenses.ytd"),
	],
	"manufacturer": [
		_metric("purchases_ytd", "Purchases YTD", "currency", "purchases.ytd"),
		_metric(
			"rebates_earned_ytd",
			"Rebates Earned YTD",
			"currency",
			"rebates.earned_ytd",
		),
	],
}


def get_financial_metrics_dictionary() -> dict:
	"""Return the full canonical financial metrics dictionary."""
	return deepcopy(ORG_FINANCIAL_METRICS_DICTIONARY)


def get_financial_metrics_spec(org_type: str | None = None) -> dict:
	"""Return merged metrics spec for a given org_type.

	Output shape:
	{
	  "version": <int>,
	  "org_type": <resolved type>,
	  "metrics": [
	    {id,label,format,paths},
	    ...
	  ]
	}
	"""
	resolved_type = (org_type or OrgType.CUSTOMER).lower()
	if resolved_type not in ORG_FINANCIAL_METRICS_DICTIONARY:
		resolved_type = OrgType.CUSTOMER

	common = ORG_FINANCIAL_METRICS_DICTIONARY.get("common", [])
	specific = ORG_FINANCIAL_METRICS_DICTIONARY.get(resolved_type, [])

	return {
		"version": FINANCIAL_METRICS_DICTIONARY_VERSION,
		"org_type": resolved_type,
		"metrics": deepcopy(common + specific),
	}


def _deep_merge_dict(base: dict, overlay: dict) -> dict:
	"""Recursively merge overlay into base, returning a new dict."""
	out = deepcopy(base)
	for key, value in (overlay or {}).items():
		if isinstance(value, dict) and isinstance(out.get(key), dict):
			out[key] = _deep_merge_dict(out[key], value)
		else:
			out[key] = deepcopy(value)
	return out


def flatten_financial_for_type(financial: dict | None, org_type: str | None) -> dict:
	"""Flatten type-keyed financial JSON to a model-centric dictionary.

	Input (stored):
	  {common:{...}, customer/vendor/...:{...}, fx:{...}}

	Output (flat):
	  {<common fields>, <type fields>, fx:{...}, _org_type:"..."}
	"""
	resolved_type = (org_type or OrgType.CUSTOMER).lower()
	if resolved_type not in {c.value for c in OrgType}:
		resolved_type = OrgType.CUSTOMER

	merged = _deep_merge_dict(default_financial(), financial or {})
	flat: dict = {}
	flat.update(deepcopy(merged.get("common", {})))
	flat.update(deepcopy(merged.get(resolved_type, {})))
	if isinstance(merged.get("fx"), dict):
		flat["fx"] = deepcopy(merged["fx"])
	flat["_org_type"] = resolved_type
	return flat


def inflate_flat_financial_for_type(
	flat_financial: dict | None,
	org_type: str | None,
	existing: dict | None = None,
) -> dict:
	"""Convert a flat model-centric financial payload back to type-keyed storage."""
	resolved_type = (org_type or OrgType.CUSTOMER).lower()
	if resolved_type not in {c.value for c in OrgType}:
		resolved_type = OrgType.CUSTOMER

	base = _deep_merge_dict(default_financial(), existing or {})
	if not isinstance(flat_financial, dict):
		return base

	common_template = default_financial().get("common", {})
	type_template = default_financial().get(resolved_type, {})

	for key, value in flat_financial.items():
		if key == "_org_type":
			continue
		if key == "fx":
			if isinstance(value, dict):
				base["fx"] = _deep_merge_dict(base.get("fx", {}), value)
			continue

		if key in common_template:
			if isinstance(value, dict) and isinstance(base["common"].get(key), dict):
				base["common"][key] = _deep_merge_dict(base["common"][key], value)
			else:
				base["common"][key] = deepcopy(value)
		elif key in type_template:
			if isinstance(value, dict) and isinstance(base[resolved_type].get(key), dict):
				base[resolved_type][key] = _deep_merge_dict(base[resolved_type][key], value)
			else:
				base[resolved_type][key] = deepcopy(value)
		else:
			# Unknown keys are kept under the type-specific section.
			base[resolved_type][key] = deepcopy(value)

	return base
