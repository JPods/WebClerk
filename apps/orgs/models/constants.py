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


def default_locations():  # list[{id,type,address:{...},geo:{lat,lng}}]
	return []


def default_domains():  # list[{domain, verified:bool, dt_verified:int_ms}]
	return []


def default_phones():  # list[{id,type,number,ext,primary:bool}]
	return []


def default_emails():  # list[{id,type,email,primary:bool,bounce_count:int}]
	return []


def default_relations():  # {parents:[], children:[], linked_ids:[]}
	return {"parents": [], "children": [], "linked_ids": []}


def default_financial():  # {credit:{limit,used}, balances:{open:0,...}, due_buckets:[{range,amount}], metrics:{ytd:{sales:0}}}
	return {"credit": {}, "balances": {}, "due_buckets": [], "metrics": {}}


def default_docs():  # list[{id, kind, name, size, sha256}]
	return []


def default_connections():  # pointers only, e.g. {"email_svc": "vault:cred:123"}
	return {}

# Legacy default for historical migration 0001_initial (kept to allow migrations to load)
def default_access():  # pragma: no cover - legacy
	return {}


def default_data():  # small misc extras (avoid unbounded growth)
	return {}


def default_metrics():  # counters & period aggregates {counts:{}, periods:{"2025Q1":{sales:...}}}
	return {"counts": {}, "periods": {}}


def default_gl_accounts():  # {sales:"4000", expense:"5000", ...}
	return {}