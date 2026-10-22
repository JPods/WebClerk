# 
# PURPOSE: Main Contact model with Universal API support and Django authentication
# UNIVERSAL API: Accessible via 'contacts' table name in Universal API
# REPLACES: Old Contact model without Universal API metadata support
# TEAM NOTE: This is the central user/contact entity that other models reference
# ARCHITECTURE: Combines Django's AbstractBaseUser with Universal API metadata
# RELATIONSHIPS: Referenced by addresses, phones, emails, domains, actions
# FEATURES:
#   - Django authentication integration
#   - Universal API metadata via JSON field
#   - Role-based permissions
#   - UUID generation
#   - Superuser auto-role assignment
# TABLES: Stored in 'contacts' table, accessible via /wcapi/contacts/
# METADATA: Uses contact.metadata.history.created.dt instead of dt  _created

import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.db.models import Q
from django.utils import timezone

from common.models import BaseModel
from common.link_mixins import StandardLinksMixin
from apps.core.choices import CONTACT_ROLE_CHOICES
from apps.core.services.record_keywords import build_keywords_for_record

# Django requires a custom manager for custom user models.
# ContactManager inherits from BaseUserManager (from django.contrib.auth.models)
# and provides create_user and create_superuser methods for authentication.
class ContactManager(BaseUserManager):
    """Custom user manager enforcing explicit name_first/name_last.

    create_user: requires callers to supply name_first/name_last directly (no legacy mapping).
    create_superuser: still accepts optional legacy first_name/last_name for external tooling, maps them, and ignores username.
    """

    def create_user(self, email=None, password=None, username=None, **extra_fields):  # username accepted then ignored (compat)
        """Create a regular user.

        Enforces explicit name_first/name_last; rejects legacy first_name/last_name.
        Accepts an optional username param (ignored) so existing code paths that still
        supply username= don't break or trigger static analysis warnings.
        Email is required for login-capable users but optional for record-only contacts.
        """
        if email:
            email = self.normalize_email(email)
        if 'first_name' in extra_fields or 'last_name' in extra_fields:
            raise TypeError('Use name_first / name_last fields (legacy first_name/last_name no longer accepted)')
        user = self.model(email=email or None, **extra_fields)
        if not getattr(user, 'uuid', None):
            user.uuid = uuid.uuid4()
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, username=None, **extra_fields):  # username ignored; kept for Django CLI compat
        # Map legacy names only here to stay compatible with manage.py createsuperuser flows
        legacy_first = extra_fields.pop('first_name', None)
        legacy_last = extra_fields.pop('last_name', None)
        if legacy_first and not extra_fields.get('name_first'):
            extra_fields['name_first'] = legacy_first
        if legacy_last and not extra_fields.get('name_last'):
            extra_fields['name_last'] = legacy_last
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email=email, password=password, username=username, **extra_fields)
    
    def get_by_natural_key(self, email):
        return self.get(**{self.model.USERNAME_FIELD: email})


# see ContactManager below that is used for authentication
class Contact(StandardLinksMixin, BaseModel, AbstractBaseUser, PermissionsMixin):
    """
    Contact model with Universal API metadata support and Django authentication
    Uses JSON metadata field instead of inheriting BaseModel to avoid dt_created conflicts
    """

    # Fields snapshot into refs.links when this model appears in another
    # record's denormalized links.  Authoritative — denorm_registry falls
    # back to this when present.
    DENORM_FIELDS = [
        "id", "ida", "display_name",
        "company", "title", "role", "email", "phone", "attention",
    ]

    # Properties to include in API serialization (not DB fields, but computed from FK pointers)
    COMPUTED_FIELDS = ["phone", "address_full", "domain", "display_name"]
    #: Each computed value and the field it is derived from: a role that may view the
    #: source is served the value (field_projection.filter_response_data).
    COMPUTED_FROM = {"phone": "phone_id", "address_full": "address_id",
                     "domain": "domain_id", "display_name": "name_first"}

    # FK fields to expand into {id, ida, name} objects for display
    EXPAND_FK_FIELDS = ["customer", "vendor", "manufacturer", "rep"]

    # Core Identity Fields - Django auto-creates 'id' as primary key
    # REMOVED: id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
 
    
    # Name Fields
    name_first = models.CharField(max_length=100, blank=True, help_text="First name")
    name_last = models.CharField(max_length=100, blank=True, help_text="Last name")
    name_middle = models.CharField(max_length=100, blank=True, help_text="Middle name")
    name_prefix = models.CharField(max_length=20, blank=True, help_text="Title (Mr., Ms., Dr.)")
    name_suffix = models.CharField(max_length=20, blank=True, help_text="Suffix (Jr., Sr., III)")
    attention = models.CharField(max_length=201, blank=True, help_text="Auto-filled attention line from first and last name")

    email = models.EmailField(unique=True, null=True, blank=True, help_text="Primary email address — required for login, null for record-only contacts")
    email_id = models.BigIntegerField(blank=True, null=True, help_text="Optional FK to primary email record if needed")
    address_id = models.BigIntegerField(blank=True, null=True, help_text="Optional FK to primary address record if needed")
    phone_id = models.BigIntegerField(blank=True, null=True, help_text="Optional FK to primary phone record if needed")
    domain_id = models.BigIntegerField(blank=True, null=True, help_text="Optional FK to primary domain record if needed")
    # address_full, phone, domain removed — read from FK pointer records (PJPV)
    company = models.CharField(max_length=200, blank=True, help_text="Company name")
    title = models.CharField(max_length=100, blank=True, help_text="Job title")
    department = models.CharField(max_length=100, blank=True, help_text="Department")
    
    # Business Fields — FK-first: proper ForeignKey for all org references.
    # A person can be associated with multiple orgs (vendor, manufacturer, customer, rep).
    is_employee = models.BooleanField(default=False, help_text="Contact is an employee of this company")
    customer = models.ForeignKey(
        'orgs.OrgBase', on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='customer_id', related_name='contacts_as_customer',
        help_text="Associated customer org",
    )
    vendor = models.ForeignKey(
        'orgs.OrgBase', on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='vendor_id', related_name='contacts_as_vendor',
        help_text="Associated vendor org",
    )
    manufacturer = models.ForeignKey(
        'orgs.OrgBase', on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='manufacturer_id', related_name='contacts_as_manufacturer',
        help_text="Associated manufacturer org",
    )
    rep = models.ForeignKey(
        'orgs.OrgBase', on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='rep_id', related_name='contacts_as_rep',
        help_text="Associated sales rep org",
    )
    # other_id removed — use refs for general-purpose relations (Q9 decision 2026-07-01)
    # company, title, department declared above (lines 114-116)
    # Source attribution — where did this contact come from?
    source_name = models.CharField(max_length=80, blank=True, default='', db_index=True,
        help_text="How this contact originated: Facebook, Referral, Walk-in, Trade Show, etc.")
    # System Fields
    role = models.CharField(
        max_length=50, 
        choices=CONTACT_ROLE_CHOICES,
        default='user', 
        help_text="User role in system"
    )
    is_active = models.BooleanField(default=True, help_text="User account is active")
    is_staff = models.BooleanField(default=False, help_text="User can access admin")
    dt_joined = models.DateTimeField(default=timezone.now, help_text="Account creation date")
    # Override AbstractBaseUser.password to allow blank — contacts without login still need records
    password = models.CharField(max_length=128, blank=True, default='', help_text="Hashed password")
    
    objects = ContactManager()

    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name_first', 'name_last']
    
    class Meta:
        db_table = 'contacts'
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'
        ordering = ['name_last', 'name_first']
    
    def __str__(self):
        if self.name_first or self.name_last:
            return f"{self.name_first or ''} {self.name_last or ''}".strip()
        return self.email or self.ida or f"Contact #{self.pk}"
    
    def get_full_name(self):
        """Return full name with proper formatting"""
        parts = []
        if self.name_prefix:
            parts.append(self.name_prefix)
        if self.name_first:
            parts.append(self.name_first)
        if self.name_middle:
            parts.append(self.name_middle)
        if self.name_last:
            parts.append(self.name_last)
        if self.name_suffix:
            parts.append(self.name_suffix)
        return ' '.join(parts) if parts else self.email
    
    def get_short_name(self):
        """Return short name for display"""
        if self.name_first:
            return self.name_first
        return self.email.split('@')[0]
    def _primary_value(self, kind: str, key: str) -> str:
        """The primary record's value, from the cache; one query only when the cache lacks it."""
        entry = self.primary_communication(kind)
        if entry:
            return entry.get(key) or ''
        model_cls, pointer, _entry = self._communication_kinds()[kind]
        target = getattr(self, pointer)
        if not target:
            return ''
        return model_cls.objects.filter(pk=target).values_list(key, flat=True).first() or ''

    @property
    def address_full(self):
        """The primary address, from the cache (rebuilt from Address records)."""
        return self._primary_value('address', 'full')

    @property
    def phone(self):
        """The primary phone, from the cache (rebuilt from Phone records)."""
        return self._primary_value('phone', 'number')

    @property
    def domain(self):
        """The primary domain, from the cache (rebuilt from Domain records)."""
        if self.domain_id:
            return self._primary_value('domain', 'path')
        # Fall back to extracting from email
        if self.email and '@' in self.email:
            return self.email.split('@')[1]
        return ''

    def save(self, *args, **kwargs):  # ensure role and attention sync
        # Attention fills from the names only when empty; a typed attention is the user's
        # (Bill, 2026-10-16). The form applies the same rule (frontend utils/derivedFields.ts).
        # An attention still equal to the stored names is derived, not typed, and follows them.
        names = f"{self.name_first or ''} {self.name_last or ''}".strip()
        attention = (self.attention or '').strip()
        if not attention:
            self.attention = names
        elif self.pk and attention != names:
            old = type(self).objects.filter(pk=self.pk).values(
                'name_first', 'name_last', 'attention').first()
            if old and attention == (old['attention'] or '').strip() == \
                    f"{old['name_first'] or ''} {old['name_last'] or ''}".strip():
                self.attention = names
        # Sync company from primary affiliation (customer > vendor > manufacturer > rep)
        for fk_field in ('customer', 'vendor', 'manufacturer', 'rep'):
            org = getattr(self, fk_field, None)
            if org is not None:
                org_name = getattr(org, 'display_name', '') or str(org)
                if org_name and self.company != org_name:
                    self.company = org_name
                break
        # Only set role to admin for superusers if they don't already have a role set
        if self.is_superuser and not self.role:
            self.role = 'admin'
        super().save(*args, **kwargs)
        # After save, keep scalar comm fields and communication tables in sync. The records
        # this makes or claims must not save the contact again (communications.signals).
        from apps.communications.signals import contact_saving
        with contact_saving(self.pk):
            self._sync_primary_communication_links()

    @staticmethod
    def _norm_comm_value(value):
        return str(value or "").strip()

    def _find_or_create_comm_record(self, model_cls, lookup_kwargs, create_kwargs):
        """Resolve a communication row for this contact.

        Resolution order:
        1) existing row owned by this contact
        2) existing unowned row (contact is null) -> claim for this contact
        3) create a new row for this contact
        """
        own = model_cls.objects.filter(contact=self, **lookup_kwargs).first()
        if own:
            return own

        unowned = model_cls.objects.filter(contact__isnull=True, **lookup_kwargs).first()
        if unowned:
            unowned.contact = self
            unowned.save(update_fields=['contact', 'dt_modified'])
            return unowned

        payload = {'contact': self, **create_kwargs}
        return model_cls.objects.create(**payload)

    def _sync_primary_communication_links(self):
        """Keep the login email in its Email record, then rebuild the communication cache.

        Email is the one communication scalar on the contact (the login). A contact saved
        with an email (signup, import) gets its Email record and email_id here; after that
        the email is edited in its card and the login follows the primary Email record
        (rebuild_communication_cache). Phone, address and domain are edited only in their
        own records; the contact keeps pointers and a cache (PJPV).
        """
        from apps.communications.models import Domain, Email

        updates = {}
        normalized_email = self._norm_comm_value(self.email).lower()
        if normalized_email:
            email_obj = self._find_or_create_comm_record(
                Email,
                {'email': normalized_email},
                {'email': normalized_email, 'name': 'account', 'is_primary': True,
                 'is_verified': False},
            )
            if self.email_id != email_obj.id:
                updates['email_id'] = email_obj.id

        # A domain from the email when the contact has none.
        if not self.domain_id and normalized_email and '@' in normalized_email:
            domain_part = normalized_email.split('@')[1]
            if domain_part:
                domain_obj = self._find_or_create_comm_record(
                    Domain, {'path': domain_part},
                    {'path': domain_part, 'type': 'website', 'status': 'active'},
                )
                if self.domain_id != domain_obj.id:
                    updates['domain_id'] = domain_obj.id

        if updates:
            type(self).objects.filter(pk=self.pk).update(**updates)
            for field, value in updates.items():
                setattr(self, field, value)
        self.rebuild_communication_cache()

    #: The cache: refs.links.<kind> rebuilt from the records, and the primary pointer kept
    #: on a record the contact owns. (model, pointer, entry builder)
    @staticmethod
    def _communication_kinds():
        from apps.communications.models import Address, Domain, Email, Phone
        return {
            'email': (Email, 'email_id', lambda e: {
                'id': e.id, 'email': e.email, 'name': e.name or '',
                'is_primary': bool(e.is_primary), 'is_verified': bool(e.is_verified),
                'opt_out': e.opt_out or ''}),
            'phone': (Phone, 'phone_id', lambda p: {
                'id': p.id, 'number': p.number, 'name': p.name or '',
                'country_code': p.country_code or '', 'format': p.format or '',
                'opt_out': bool(p.opt_out)}),
            'domain': (Domain, 'domain_id', lambda d: {
                'id': d.id, 'path': d.path, 'name': d.type or '', 'status': d.status}),
            'address': (Address, 'address_id', lambda a: {
                'id': a.id, 'name': a.address_type or '', 'address1': a.address1,
                'address2': a.address2, 'city': a.city, 'state': a.state, 'zip': a.zip,
                'country': a.country, 'full': a.full}),
        }

    def rebuild_communication_cache(self):
        """Rebuild refs.links.{email,phone,domain,address} from the records this contact owns.

        Called after the contact saves and after any communication record saves or is
        deleted (apps/communications/signals.py), so the cache follows whichever side
        changed (Bill, 2026-10-16). A pointer to a record the contact no longer owns moves
        to its first record, or clears. The login column is not touched here: it moves only
        when its Email record is edited or deleted (communications.signals._refresh),
        never because a contact save made a new Email record. Writes with update(), never
        save(): no recursion, no version bump for a cache. A failure raises — a stale cache
        is not silent.
        """
        if not self.pk:
            return
        refs = self.refs if isinstance(self.refs, dict) else {}
        links = refs.get('links') if isinstance(refs.get('links'), dict) else {}
        updates = {}
        for kind, (model_cls, pointer, entry) in self._communication_kinds().items():
            rows = list(model_cls.objects.filter(contact_id=self.pk).order_by('id'))
            if rows:
                links[kind] = [entry(r) for r in rows]
            else:
                links.pop(kind, None)
            ids = [r.id for r in rows]
            current = getattr(self, pointer)
            primary = current if current in ids else (ids[0] if ids else None)
            if primary != current:
                updates[pointer] = primary
        refs['links'] = links
        updates['refs'] = refs
        type(self).objects.filter(pk=self.pk).update(**updates)
        for field, value in updates.items():
            setattr(self, field, value)

    def primary_communication(self, kind: str) -> dict:
        """The primary record's cache entry ({} when none) — read without a query."""
        pointer = self._communication_kinds()[kind][1]
        target = getattr(self, pointer)
        if not target:
            return {}
        refs = self.refs if isinstance(self.refs, dict) else {}
        for row in (refs.get('links') or {}).get(kind) or []:
            if isinstance(row, dict) and row.get('id') == target:
                return row
        return {}

    @property
    def display_name(self):
        """Property for template display"""
        return self.get_full_name()

    # all metadata changes inside common/models/BaseModel.py

    def has_addresses(self):
        """Check if contact has any addresses"""
        addresses = getattr(self, 'addresses', None)
        return bool(addresses and addresses.exists())
    
    def has_phones(self):
        """Check if contact has any phone numbers"""
        phones = getattr(self, 'phones', None)
        return bool(phones and phones.exists())
    
    def has_emails(self):
        """Check if contact has any additional emails"""
        emails = getattr(self, 'emails', None)
        return bool(emails and emails.exists())
    
    def has_domains(self):
        """Check if contact has any domains"""
        domains = getattr(self, 'domains', None)
        return bool(domains and domains.exists())
    
    def get_role_display_name(self):
        """Get human-readable role name"""
        return dict(CONTACT_ROLE_CHOICES).get(self.role, self.role)
    
    def save_before(self, data):
        # Custom logic before save
        return True

    def update_keywords(self):
        """Update keywords for this contact record."""
        # Get current refs or initialize if needed
        refs = getattr(self, 'refs', {}) or {}
        if not isinstance(refs, dict):
            refs = {}
        
        # Ensure refs has the expected structure
        refs.setdefault('keywords', [])
        
        # Use the actual model name from class name
        model_name = self.__class__.__name__.lower()
        keywords = build_keywords_for_record(model_name, self.id)
        
        # Store keywords in refs.keywords (preserve other refs data)
        refs['keywords'] = keywords
        self.refs = refs
        
        # Note: Save is handled by the calling thread in save_view.py
    

