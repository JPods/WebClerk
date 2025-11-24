"""Unified organization model layer.

This module introduces `OrgBase`, a concrete table leveraging the shared
`BaseModel` capability stack (metadata, refs, prefs, comments, keywords,
atomic JSON ops, lifecycle, telemetry) while flattening previously ad‑hoc
"refs" usage into semantically named JSONB aspect fields for clarity and
future evolution.

Design goals:
1. Single flexible table for all organization actors (customer, vendor,
   rep, employee, manufacturer, other) => simpler generic APIs.
2. Promote only universally hot query fields to columns (org_type,
   company, status, is_active). Everything sparse / volatile lives in
	aspect JSONBs (contacts, locations, phones, emails, domains, relations,
	financial, docs, connections, data, metrics, gl_accounts) to minimize schema churn.
3. Permit optional lightweight proxy subclasses (Customer, Vendor, ...)
   for ergonomic filtered querysets WITHOUT creating separate physical tables.
4. Reuse existing size telemetry & potential future offload mechanism; each
   aspect field stays below ~64–128 KB practical caps (enforced via global
   BaseModel checks + prospective per-field thresholds if needed later).
5. Provide helper methods for common mutations (add_contact, credit_utilization)
   that automatically mark keywords dirty where relevant.

Security & PII notes:
- Do not store raw secrets in `connections`; instead store pointers (e.g., vault IDs).
- Sensitive identifiers (e.g., full SSN) should be relocated to an encrypted
  model; store only last4 or a hashed reference here if absolutely required.

Future evolution hooks:
- Add FTS / generated search vector index (across company + contact names + domains) once usage patterns stabilize.
- Offload large historical financial arrays (aging buckets, time‑series metrics)
  via existing offload telemetry path when thresholds show benefit.
"""
# https://docs.google.com/document/d/e/2PACX-1vRIoXVaerJitp9nux7GqUnj6qeKACMQRPj06DDi_QgC8bugpIQqJFO9fNT-wA6wRJHmef4GuxzaQo9j/pub


from __future__ import annotations

from django.db import models
from django.utils import timezone
from django.contrib.postgres.indexes import GinIndex

from common.models import BaseModel
from common.link_mixins import StandardLinksMixin
from common.stats_mixin import StatsMixin
from common.relationship_stats_mixin import RelationshipStatsMixin


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


# ---------------- Unified model -----------------
class OrgBase(StandardLinksMixin, RelationshipStatsMixin, StatsMixin, BaseModel):
	"""Unified organization entity with flexible aspect JSON envelopes.

	Key columns kept minimal for performance & indexing; JSON aspects capture
	heterogeneous data per org_type. Proxies provide ergonomic type scoping.
	"""

	feature_flags = BaseModel.feature_flags | {"org", "stats", "relationship_stats"}

	# Per-aspect item count soft limits (govern snapshot size). Tune as needed.
	ASPECT_LIMITS: dict[str, int] = {
		"contacts": 15,
		"locations": 10,
		"domains": 10,
		"phones": 10,
		"emails": 10,
		"relations": 50,  # relation lists are IDs mostly
		"financial": 1,    # treated as singleton object; limit means placeholder only
		"docs": 25,
		"connections": 1,  # small dict pointer
		"data": 1,         # misc small dict (not a list, limit semantic only docs)
		"metrics": 1,
		"gl_accounts": 1,
	}

	org_type = models.CharField(max_length=20, choices=OrgType.choices, db_index=True)
	company = models.CharField(max_length=255, db_index=True)
	status = models.CharField(max_length=30, blank=True, db_index=True)  # e.g. active, prospect, retired

	# Aspect JSONB fields -------------------------------------------------
	# denormalized hybrid of table data into a flatter structure
	contacts = models.JSONField(default=default_contacts)
	locations = models.JSONField(default=default_locations)
	domains = models.JSONField(default=default_domains)
	phones = models.JSONField(default=default_phones)
	emails = models.JSONField(default=default_emails)
	docs = models.JSONField(default=default_docs)
	connections = models.JSONField(default=default_connections)
	
	relations = models.JSONField(default=default_relations)
	financial = models.JSONField(default=default_financial)
	data = models.JSONField(default=default_data)
	metrics = models.JSONField(default=default_metrics)
	gl_accounts = models.JSONField(default=default_gl_accounts)

	class Meta:
		indexes = [
			GinIndex(fields=["contacts"], name="org_contacts_gin"),
			GinIndex(fields=["relations"], name="org_rel_gin"),
			GinIndex(fields=["financial"], name="org_financial_gin"),
			GinIndex(fields=["domains"], name="org_domains_gin"),
		]
		constraints = [
			models.CheckConstraint(check=~models.Q(company=""), name="org_company_not_empty"),
		]
		verbose_name = "Organization"
		verbose_name_plural = "Organizations"

	# -------- Helpers ---------------------------------------------------
	def add_contact(self, contact_id: int | None, name: str, role: str | None = None, **extras):
		entry = {"id": contact_id, "name": name, "role": role}
		if extras:
			entry.update(extras)
		self.contacts.append(entry)
		# flag keywords for refresh (KeywordsMixin semantics)
		self.mark_keywords_dirty()
		self._prune_aspect("contacts")
		self._update_aspect_meta("contacts")

	def credit_utilization(self) -> float:
		credit = self.financial.get("credit", {}) if isinstance(self.financial, dict) else {}
		limit_ = credit.get("limit") or 0
		used = credit.get("used") or 0
		return float(used) / float(limit_) if limit_ else 0.0

	def primary_domain(self) -> str | None:
		if isinstance(self.domains, list) and self.domains:
			return self.domains[0].get("domain")
		return None

	# -------- Validation (Pydantic schemas) ------------------------------
	def validate_aspects(self, partial: bool = False, data: dict | None = None):
		"""Validate current (or provided) aspect JSON blobs against pydantic schemas.

		Returns (ok: bool, errors: list[str]). When partial=True uses OrgSnapshotPatch schema
		allowing sparse keys (e.g., for patch payload validation before applying).

		Parameters:
		- partial: validate a patch dict instead of full snapshot.
		- data: for partial, the patch payload; for full, overrides to merge into the built snapshot.

		Note: This method does not mutate or save the model; caller decides what to do
		with any validation failures. Intended for service layer or management commands.
		"""
		try:
			from apps.orgs.pydantic_schemas import (
				OrgSnapshot, OrgSnapshotPatch, build_org_snapshot
			)
		except Exception as imp_err:  # pragma: no cover - import failure path
			return False, [f"pydantic schemas unavailable: {imp_err}"]
		if partial:
			payload = data or {}
			model_cls = OrgSnapshotPatch
		else:
			# Build snapshot defensively: if core scalar fields themselves are invalid (e.g., org_type)
			# allow caller to override by passing data dict (e.g., during creation before save())
			try:
				base_payload = build_org_snapshot(self).dict()
			except Exception:
				base_payload = {
					"org_type": getattr(self, 'org_type', None),
					"company": getattr(self, 'company', ''),
					"status": getattr(self, 'status', None),
					"is_active": getattr(self, 'is_active', True),
					"contacts": [],
					"locations": [],
					"domains": [],
					"phones": [],
					"emails": [],
					"relations": {},
					"financial": {},
					"docs": [],
					"connections": {},
					"data": {},
					"metrics": {},
					"gl_accounts": {},
				}
			if data:
				base_payload.update(data)
			payload = base_payload
			model_cls = OrgSnapshot
		try:
			model_cls(**payload)  # instantiate for validation side effects
			return True, []
		except Exception as e:  # capture ValidationError generically
			errs: list[str] = []
			if hasattr(e, 'errors'):
				for err in e.errors():  # type: ignore[attr-defined]
					loc = '.'.join(str(p) for p in err.get('loc', []))
					msg = err.get('msg') or 'invalid'
					errs.append(f"{loc}: {msg}")
			else:
				errs.append(str(e))
			return False, errs

	def api_validate_payload(self, data: dict, is_update: bool):  # called by universal save view when enabled
		"""Universal API integration hook.

		Returns (ok, errors). Delegates to validate_aspects with partial flag for updates.
		Filters patch payload to aspect + core fields so unrelated metadata fields do not cause noise.
		"""
		aspect_keys = set(self.ASPECT_LIMITS.keys()) | {"org_type","company","status","is_active"}
		if is_update:
			patch_subset = {k: v for k, v in data.items() if k in aspect_keys}
			return self.validate_aspects(partial=True, data=patch_subset)
		# full create/update (no id): validate full snapshot
		return self.validate_aspects(partial=False)

	# Example: customize universal dict to expose org_type & company directly
	def to_universal_dict(self):  # type: ignore[override]
		base = super().to_universal_dict()
		base.update({
			"org_type": self.org_type,
			"company": self.company,
			"status": self.status,
			"is_active": self.is_active,
		})
		return base

	# Provide a text blob for keyword generation (KeywordsMixin scans char/text fields only)
	@property
	def keywords_source(self) -> str:  # optional: used indirectly by keyword refresh if added later
		contact_names = []
		if isinstance(self.contacts, list):
			for c in self.contacts[:10]:  # cap to avoid huge strings
				n = c.get('name')
				if n:
					contact_names.append(n)
		domain_list = []
		if isinstance(self.domains, list):
			for d in self.domains[:10]:
				dm = d.get('domain')
				if dm:
					domain_list.append(dm)
		return " ".join(filter(None, [self.company, self.status] + contact_names + domain_list))

	# -------- Aspect governance helpers ---------------------------------
	def _prune_aspect(self, aspect: str):
		"""Prune list-like aspect to its ASPECT_LIMITS count (in-place, keep earliest items).

		For non-list aspects (dict/singleton) no action. This is invoked on mutation paths
		(e.g. add_contact) and by refresh methods for uniform enforcement.
		"""
		limit = self.ASPECT_LIMITS.get(aspect)
		if not limit or limit < 1:
			return
		val = getattr(self, aspect, None)
		if isinstance(val, list) and len(val) > limit:
			# Keep first N (could later apply priority heuristics)
			del val[limit:]

	def _update_aspect_meta(self, aspect: str):
		"""Update metadata.versioning.aspects entry for given aspect with count & dt_refreshed."""
		if not hasattr(self, "metadata"):
			return
		aspects_meta = self.metadata.setdefault("versioning", {}).setdefault("aspects", {})  # type: ignore[attr-defined]
		val = getattr(self, aspect, None)
		count = 0
		if isinstance(val, list):
			count = len(val)
		elif isinstance(val, dict):
			count = len(val.keys())
		aspects_meta[aspect] = {
			"count": count,
			"dt_refreshed": int(timezone.now().timestamp() * 1000),
		}

	def refresh_aspects(self, prune: bool = True, aspects: list[str] | None = None):
		"""Refresh & optionally prune selected aspects; update metadata counts.

		Currently acts mainly as governance (prune + metadata). Future hook: repopulate
		from normalized child tables when they exist.
		"""
		target_aspects = aspects or [
			"contacts","locations","domains","phones","emails","relations","financial","docs","connections","data","metrics","gl_accounts"
		]
		for a in target_aspects:
			if prune:
				self._prune_aspect(a)
			self._update_aspect_meta(a)

	def refresh_and_save(self, prune: bool = True, aspects: list[str] | None = None, expected_version: int | None = None):
		"""Public convenience to refresh governance metadata then save with optional optimistic lock."""
		self.refresh_aspects(prune=prune, aspects=aspects)
		self.save(expected_version=expected_version)


# -------------- Proxy type models (ergonomic filters, no new tables) -----
class _TypeFilteredManager(models.Manager):
	def __init__(self, org_type: str):
		super().__init__()
		self._org_type = org_type

	def get_queryset(self):  # type: ignore[override]
		return super().get_queryset().filter(org_type=self._org_type)
	
	def create(self, **kwargs):
		"""Auto-set org_type when creating records through proxy models."""
		kwargs['org_type'] = self._org_type
		return super().create(**kwargs)


class Customer(OrgBase):
	class Meta:
		proxy = True
		verbose_name = "Customer"
		verbose_name_plural = "Customers"

	objects = _TypeFilteredManager(OrgType.CUSTOMER)


class Vendor(OrgBase):
	class Meta:
		proxy = True
		verbose_name = "Vendor"
		verbose_name_plural = "Vendors"

	objects = _TypeFilteredManager(OrgType.VENDOR)


class Rep(OrgBase):
	class Meta:
		proxy = True
		verbose_name = "Rep"
		verbose_name_plural = "Reps"

	objects = _TypeFilteredManager(OrgType.REP)


class Employee(OrgBase):
	class Meta:
		proxy = True
		verbose_name = "Employee"
		verbose_name_plural = "Employees"

	objects = _TypeFilteredManager(OrgType.EMPLOYEE)


class Manufacturer(OrgBase):
	class Meta:
		proxy = True
		verbose_name = "Manufacturer"
		verbose_name_plural = "Manufacturers"

	objects = _TypeFilteredManager(OrgType.MANUFACTURER)


__all__ = [
	"OrgType",
	"OrgBase",
	"Customer",
	"Vendor",
	"Rep",
	"Employee",
	"Manufacturer",
]

