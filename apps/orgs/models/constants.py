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


def default_addresses():  # list[{id,type,address:{...},geo:{lat,lng}}]
    return []


def default_domains():  # list[{domain, verified:bool, dt_verified:int_ms}]
	return []


def default_phones():  # list[{id,type,number,ext,primary:bool}]
	return []


def default_emails():  # list[{id,type,email,primary:bool,bounce_count:int}]
	return []


def default_relations():  # {parents:[], children:[], linked_ids:[]}
	return {"parents": [], "children": [], "linked_ids": []}


def default_financial():
	"""
	Type-keyed financial profile for orgs.
	Common fields apply to all. Type-specific sections populated based on org roles.
	An org can be multiple types (customer + vendor + manufacturer).
	"""
	return {
		# ===== COMMON (all org types) =====
		"common": {
			"currency": "USD",  # ISO 4217
			"account": {
				"dt_opened": None,
				"dt_last_activity": None,
				"hold": False,
				"cod_only": False,
				"inactive": False,
			},
			"rating": {
				"internal": None,    # your internal score (A/B/C or 1-10)
				"comments": "",
				"credit_score": None,  # external credit score
			},
			"settings": {
				"discount_pct": 0,
				"tax_exempt": False,
				"tax_exempt_id": "",
				"terms_id": None,
				"notes": "",
			},
		},

		# ===== CUSTOMER (what they owe us) =====
		"customer": {
			"credit": {
				"limit": 0,
				"high": 0,        # historical high balance
				"available": 0,
			},
			"balances": {
				"due": 0,
				"current": 0,
				"open_orders": 0,
				"total_exposure": 0,
			},
			"aging": {
				"future": 0,
				"period_1": 0,    # 1-30 days
				"period_2": 0,    # 31-60 days
				"period_3": 0,    # 61-90+ days
			},
			"payment": {
				"days_avg_paid": 0,
				"days_pay": 0,
				"dt_last_payment": None,
				"last_payment_amount": 0,
			},
			"sales": {
				"mtd": 0,
				"ytd": 0,
				"lifetime": 0,
				"dt_last_sale": None,
				"last_sale_amount": 0,
			},
			"margin": {
				"mtd": 0,
				"ytd": 0,
				"pct": 0,
			},
			"returns": {
				"mtd": 0,
				"ytd": 0,
				"count": 0,
			},
			"deposits": {
				"unapplied": 0,
			},
			"collection": {
				"cost_mtd": 0,
				"cost_ytd": 0,
				"cost_alltime": 0,
			},
			"minimums": {
				"order": 0,
			},
			"stats": {
				"proposals": {"issued": {"count": 0, "value": 0}, "canceled": {"count": 0, "value": 0}, "executed": {"count": 0, "value": 0}},
				"orders": {"issued": {"count": 0, "value": 0}, "canceled": {"count": 0, "value": 0}, "executed": {"count": 0, "value": 0}},
				"invoices": {"issued": {"count": 0, "value": 0}, "canceled": {"count": 0, "value": 0}, "executed": {"count": 0, "value": 0}},
				"payments": {"issued": {"count": 0, "value": 0}, "canceled": {"count": 0, "value": 0}, "executed": {"count": 0, "value": 0}},
			},
			"complaints": {"our_fault": 0, "their_fault": 0, "unresolved": 0, "costs": {"us": 0, "partner": 0, "rep": 0}},
			"small_stings": {
				"received": {"count": 0, "value": 0, "paid": 0, "pending": 0},
				"issued": {"count": 0, "value": 0, "collected": 0, "pending": 0},
				"by_category": {
					"shipping": {"count": 0, "value": 0},
					"billing": {"count": 0, "value": 0},
					"quality": {"count": 0, "value": 0},
					"service": {"count": 0, "value": 0},
					"other": {"count": 0, "value": 0},
				},
			},
		},

		# ===== VENDOR (what we owe them) =====
		"vendor": {
			"credit": {
				"limit": 0,
				"terms_days": 0,
			},
			"balances": {
				"due": 0,
				"current": 0,
				"open_pos": 0,
			},
			"aging": {
				"future": 0,
				"period_1": 0,
				"period_2": 0,
				"period_3": 0,
			},
			"purchases": {
				"mtd": 0,
				"ytd": 0,
				"lifetime": 0,
				"dt_last_purchase": None,
				"last_purchase_amount": 0,
			},
			"costs": {
				"mtd": 0,
				"ytd": 0,
			},
			"payments_made": {
				"mtd": 0,
				"ytd": 0,
				"dt_last_payment": None,
			},
			"minimums": {
				"order": 0,
				"purchase": 0,
			},
			"stats": {
				"purchases": {"issued": {"count": 0, "value": 0}, "canceled": {"count": 0, "value": 0}, "executed": {"count": 0, "value": 0}},
			},
			"complaints": {"our_fault": 0, "their_fault": 0, "unresolved": 0, "costs": {"us": 0, "partner": 0, "rep": 0}},
			"small_stings": {
				"received": {"count": 0, "value": 0, "paid": 0, "pending": 0},
				"issued": {"count": 0, "value": 0, "collected": 0, "pending": 0},
				"by_category": {
					"shipping": {"count": 0, "value": 0},
					"billing": {"count": 0, "value": 0},
					"quality": {"count": 0, "value": 0},
					"service": {"count": 0, "value": 0},
					"other": {"count": 0, "value": 0},
				},
			},
		},

		# ===== REP (commission tracking) =====
		"rep": {
			"commissions": {
				"mtd": 0,
				"ytd": 0,
				"lifetime": 0,
				"pending": 0,
				"paid": 0,
				"rate_pct": 0,
			},
			"sales_credited": {
				"mtd": 0,
				"ytd": 0,
				"lifetime": 0,
			},
			"customers_count": 0,
			"stats": {
				"proposals": {"issued": {"count": 0, "value": 0}, "executed": {"count": 0, "value": 0}},
				"orders": {"issued": {"count": 0, "value": 0}, "executed": {"count": 0, "value": 0}},
			},
		},

		# ===== EMPLOYEE (payroll/expense) =====
		"employee": {
			"payroll": {
				"salary": 0,
				"rate_hourly": 0,
				"rate_type": "salary",  # salary | hourly | commission
			},
			"expenses": {
				"mtd": 0,
				"ytd": 0,
				"pending": 0,
			},
			"commissions": {
				"mtd": 0,
				"ytd": 0,
			},
			"time": {
				"hours_mtd": 0,
				"hours_ytd": 0,
			},
		},

		# ===== MANUFACTURER (supply chain) =====
		"manufacturer": {
			"purchases": {
				"mtd": 0,
				"ytd": 0,
				"lifetime": 0,
			},
			"rebates": {
				"earned_ytd": 0,
				"received_ytd": 0,
				"pending": 0,
			},
			"pricing_tier": None,
			"lead_time_days": 0,
			"freight_terms": "",
			"min_order": 0,
			"stats": {
				"purchases": {"issued": {"count": 0, "value": 0}, "canceled": {"count": 0, "value": 0}, "executed": {"count": 0, "value": 0}},
			},
		},

		# ===== CURRENCY IMPACT (for multi-currency orgs) =====
		"fx": {
			"gain_loss_mtd": 0,
			"gain_loss_ytd": 0,
			"gain_loss_alltime": 0,
		},
	}


def default_docs():  # list[{id, kind, name, size, sha256}]
	return []


def default_connections():  # pointers only, e.g. {"email_svc": "vault:cred:123"}
	return {}

# Legacy defaults for historical migration 0001_initial (kept to allow migrations to load)
def default_access():  # pragma: no cover - legacy
	return {}

default_locations = default_addresses  # pragma: no cover - legacy alias


def default_data():  # small misc extras (avoid unbounded growth)
	return {}


def default_metrics():  # counters & period aggregates {counts:{}, periods:{"2025Q1":{sales:...}}}
	return {"counts": {}, "periods": {}}


def default_gl_accounts():  # {sales:"4000", expense:"5000", ...}
	return {}
