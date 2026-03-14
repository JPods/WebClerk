from __future__ import annotations

import logging
from django.db import models
from django.utils import timezone
from django.contrib.postgres.indexes import GinIndex

logger = logging.getLogger(__name__)

from common.models import BaseModel
from common.link_mixins import StandardLinksMixin
from common.stats_mixin import StatsMixin
from common.relationship_stats_mixin import RelationshipStatsMixin

from .constants import *
from apps.orgs.choices import ORG_STATUS_CHOICES


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
		"addresses": 10,
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

	org_type = models.CharField(max_length=20, choices=OrgType.choices, db_index=True, blank=True, null=True)
	display_name = models.CharField(max_length=255, db_index=True)
	# FK-first: proper ForeignKey to Contact for primary contact reference.
	contact = models.ForeignKey(
		'core.Contact', on_delete=models.SET_NULL,
		blank=True, null=True,
		db_column='contact_id', related_name='orgs_as_contact',
	)

	attention = models.CharField(max_length=255, blank=True, null=True)  # optional attention line for mailing
	address_id = models.IntegerField(blank=True, null=True)  # optional FK to an Address record for the primary address
	address_full = models.CharField(max_length=500, blank=True, null=True)  # optional denormalized full address for quick display/search
	email = models.EmailField(blank=True, null=True)  # optional primary email (could be denormalized from emails aspect)
	email_id = models.IntegerField(blank=True, null=True)  # optional FK to an Email record for the primary email
	phone_id = models.IntegerField(blank=True, null=True)  # optional FK to a Phone record for the primary phone
	phone = models.CharField(max_length=50, blank=True, null=True)  # optional primary phone (could be denormalized from phones aspect)
	# New alias property: prefer `company` in code, `display_name` remains the DB column until an explicit migration is performed.
	# Keep `display_name` as the actual DB-backed field for now for smooth migrations; provide a `company` property to use in code.
	domain = models.CharField(max_length=255, blank=True, null=True)  # optional primary domain (could be denormalized from domains aspect)
	domain_id = models.IntegerField(blank=True, null=True)  # optional FK to a Domain record for the primary domain
	price_level = models.CharField(max_length=30, blank=True, null=True)  # e.g. retail, wholesale; optional for future use
	terms = models.CharField(max_length=30, blank=True, null=True)  # e.g. retail, wholesale; optional for future use
	terms_fk = models.ForeignKey(
		'transactions.PaymentTerm', on_delete=models.SET_NULL,
		blank=True, null=True,
		db_column='terms_id', related_name='orgs_with_terms',
	)
	status = models.CharField(
		max_length=30,
		blank=True,
		choices=ORG_STATUS_CHOICES,
		db_index=True,
	)  # e.g. active, prospect, retired

	@property
	def company(self) -> str:
		"""Alias for `display_name`. Prefer using `company` in code; `display_name` retained on DB."""
		return getattr(self, 'display_name', '')

	@company.setter
	def company(self, value: str) -> None:
		setattr(self, 'display_name', value)

	def __repr__(self) -> str:
		"""Dev-friendly repr showing key value pairs for data cleanup."""
		pairs = [
			f"id={self.pk}",
			f"display_name={self.display_name!r}",
			f"attention={self.attention!r}",
			f"phone={self.phone!r}",
			f"email={self.email!r}",
			f"address_full={self.address_full!r}",
			f"domain={self.domain!r}",
		]
		return f"<OrgBase({', '.join(pairs)})>"

	# Aspect JSONB fields -------------------------------------------------
	# denormalized hybrid of table data into a flatter structure
	contacts = models.JSONField(default=default_contacts)
	addresses = models.JSONField(default=default_addresses)
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
			models.CheckConstraint(check=~models.Q(display_name=""), name="org_display_name_not_empty"),
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
					"display_name": getattr(self, 'display_name', ''),
					"status": getattr(self, 'status', None),
					"is_active": getattr(self, 'is_active', True),
					"contacts": [],
					"addresses": [],
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
		aspect_keys = set(self.ASPECT_LIMITS.keys()) | {"org_type","company","display_name","status","is_active"}
		if is_update:
			patch_subset = {k: v for k, v in data.items() if k in aspect_keys}
			return self.validate_aspects(partial=True, data=patch_subset)
		# full create/update (no id): validate full snapshot
		return self.validate_aspects(partial=False)

	# Example: customize universal dict to expose org_type & display_name directly
	def to_universal_dict(self):  # type: ignore[override]
		base = super().to_universal_dict()
		base.update({
			"org_type": self.org_type,
			"company": self.company,
			"display_name": self.display_name,  # deprecated; kept for compatibility
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
		# Prefer `company` for external use; keep display_name as fallback
		return " ".join(filter(None, [self.company or self.display_name, self.status] + contact_names + domain_list))
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
			"contacts","addresses","domains","phones","emails","relations","financial","docs","connections","data","metrics","gl_accounts"
		]
		for a in target_aspects:
			if prune:
				self._prune_aspect(a)
			self._update_aspect_meta(a)

	def refresh_and_save(self, prune: bool = True, aspects: list[str] | None = None, expected_version: int | None = None):
		"""Public convenience to refresh governance metadata then save with optional optimistic lock."""
		self.refresh_aspects(prune=prune, aspects=aspects)
		self.save(expected_version=expected_version)
	
	def save(self, *args, **kwargs):
		"""Override save to ensure org_type is set correctly for proxy models."""
		previous_display_name = None
		if self.pk:
			previous_display_name = (
				OrgBase.objects.filter(pk=self.pk)
				.values_list("display_name", flat=True)
				.first()
			)

		# For proxy models, ensure org_type is set correctly
		if getattr(self._meta, 'proxy', False):
			model_name = self.__class__.__name__
			if model_name == 'Customer' and self.org_type != 'customer':
				self.org_type = 'customer'
			elif model_name == 'Vendor' and self.org_type != 'vendor':
				self.org_type = 'vendor'
			elif model_name == 'Rep' and self.org_type != 'rep':
				self.org_type = 'rep'
			elif model_name == 'Employee' and self.org_type != 'employee':
				self.org_type = 'employee'
			elif model_name == 'Manufacturer' and self.org_type != 'manufacturer':
				self.org_type = 'manufacturer'
		
		try:
			# Try to validate aspects, but don't fail save if validation fails
			if hasattr(self, 'validate_aspects'):
				self.validate_aspects(partial=True)
		except Exception as e:
			# Log validation errors but continue with save for admin
			logger.warning("Validation error during save (continuing): %s", e)
		super().save(*args, **kwargs)

		# Keep contact.company aligned with the customer org display_name.
		if (
			(self.org_type or "").lower() == "customer"
			and self.pk
			and self.display_name
			and previous_display_name != self.display_name
		):
			try:
				from apps.core.models import Contact
				from apps.orgs.services.contact_linking import resolve_contact_ids_for_customer_org
				now_ms = int(timezone.now().timestamp() * 1000)
				linked_contact_ids = resolve_contact_ids_for_customer_org(self)
				if linked_contact_ids:
					Contact.objects.filter(id__in=linked_contact_ids).exclude(company=self.display_name).update(
						company=self.display_name,
						dt_modified=now_ms,
					)
			except Exception as e:
				logger.warning(
					"Failed syncing Contact.company for customer org %s: %s",
					self.pk,
					e,
				)
