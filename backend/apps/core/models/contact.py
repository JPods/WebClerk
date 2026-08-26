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
from apps.core.services.keywords import build_keywords_for_record

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
    employee = models.ForeignKey(
        'orgs.OrgBase', on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='employee_id', related_name='contacts_as_employee',
        help_text="Associated employee org",
    )
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
    @property
    def address_full(self):
        """Read from primary address record via FK pointer."""
        if self.address_id:
            from apps.communications.models import Address
            addr = Address.objects.filter(pk=self.address_id).values_list('full', flat=True).first()
            return addr or ''
        return ''

    @property
    def phone(self):
        """Read from primary phone record via FK pointer."""
        if self.phone_id:
            from apps.communications.models import Phone
            ph = Phone.objects.filter(pk=self.phone_id).values_list('number', flat=True).first()
            return ph or ''
        return ''

    @property
    def domain(self):
        """Read from primary domain record via FK pointer."""
        if self.domain_id:
            from apps.communications.models import Domain
            dom = Domain.objects.filter(pk=self.domain_id).values_list('path', flat=True).first()
            return dom or ''
        # Fall back to extracting from email
        if self.email and '@' in self.email:
            return self.email.split('@')[1]
        return ''

    def save(self, *args, **kwargs):  # ensure role and attention sync
        self.attention = f"{self.name_first} {self.name_last}".strip()
        # Only set role to admin for superusers if they don't already have a role set
        if self.is_superuser and not self.role:
            self.role = 'admin'
        super().save(*args, **kwargs)
        # After save, keep scalar comm fields and communication tables in sync.
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
        own = model_cls.objects.filter(contact_id=self.pk, **lookup_kwargs).first()
        if own:
            return own

        unowned = model_cls.objects.filter(contact__isnull=True, **lookup_kwargs).first()
        if unowned:
            unowned.contact_id = self.pk
            unowned.save(update_fields=['contact', 'dt_modified'])
            return unowned

        payload = {'contact_id': self.pk, **create_kwargs}
        return model_cls.objects.create(**payload)

    def _sync_primary_communication_links(self):
        """Synchronize email with Email records and rebuild refs.links from communication tables.

        Shadow fields (phone, domain, address_full) have been removed — PJPV.
        Communication records are now edited directly. This method:
        1. Syncs email (the only remaining scalar) with Email records
        2. Rebuilds refs.links from all communication tables
        """
        try:
            from apps.communications.models import Address, Domain, Email, Phone

            updates = {}

            # Email is the only remaining scalar field — sync it to Email records
            normalized_email = self._norm_comm_value(self.email).lower()
            if normalized_email:
                email_obj = self._find_or_create_comm_record(
                    Email,
                    {'email': normalized_email},
                    {
                        'email': normalized_email,
                        'name': 'account',
                        'is_primary': True,
                        'is_verified': False,
                    },
                )
                if self.email_id != email_obj.id:
                    updates['email_id'] = email_obj.id

            # Extract domain from email if no domain_id is set
            if not self.domain_id and normalized_email and '@' in normalized_email:
                domain_part = normalized_email.split('@')[1]
                if domain_part:
                    domain_obj = self._find_or_create_comm_record(
                        Domain,
                        {'path': domain_part},
                        {'path': domain_part, 'type': 'website', 'status': 'active'},
                    )
                    if self.domain_id != domain_obj.id:
                        updates['domain_id'] = domain_obj.id

            refs = self.refs if isinstance(self.refs, dict) else {}
            links = refs.get('links', {})
            if not isinstance(links, dict):
                links = {}

            email_links = [
                {
                    'id': e.id,
                    'email': e.email,
                    'name': e.name or '',
                    'is_primary': bool(e.is_primary),
                    'is_verified': bool(e.is_verified),
                    'opt_out': e.opt_out or '',
                }
                for e in Email.objects.filter(contact_id=self.pk).order_by('id')
            ]
            if email_links:
                links['email'] = email_links
            else:
                links.pop('email', None)

            phone_links = [
                {
                    'id': p.id,
                    'number': p.number,
                    'name': p.name or '',
                    'country_code': p.country_code or '',
                    'format': p.format or '',
                    'opt_out': bool(p.opt_out),
                }
                for p in Phone.objects.filter(contact_id=self.pk).order_by('id')
            ]
            if phone_links:
                links['phone'] = phone_links
            else:
                links.pop('phone', None)

            domain_links = [
                {
                    'id': d.id,
                    'path': d.path,
                    'name': d.type or '',
                    'status': d.status,
                }
                for d in Domain.objects.filter(contact_id=self.pk).order_by('id')
            ]
            if domain_links:
                links['domain'] = domain_links
            else:
                links.pop('domain', None)

            address_links = [
                {
                    'id': a.id,
                    'name': a.address_type or '',
                    'address1': a.address1,
                    'address2': a.address2,
                    'city': a.city,
                    'state': a.state,
                    'zip': a.zip,
                    'country': a.country,
                    'full': a.full,
                }
                for a in Address.objects.filter(contact_id=self.pk).order_by('id')
            ]
            if address_links:
                links['address'] = address_links
            else:
                links.pop('address', None)

            refs['links'] = links
            updates['refs'] = refs

            type(self).objects.filter(pk=self.pk).update(**updates)

            if 'email_id' in updates:
                self.email_id = updates['email_id']
            if 'phone_id' in updates:
                self.phone_id = updates['phone_id']
            if 'domain_id' in updates:
                self.domain_id = updates['domain_id']
            if 'address_id' in updates:
                self.address_id = updates['address_id']
            self.refs = refs
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to sync communication links for contact {self.pk}: {e}")
    
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

    def save_after(self, data):
        """Ensure bidirectional refs between contact and linked orgs."""
        ROLE_FIELDS = ('customer', 'vendor', 'manufacturer', 'employee', 'rep')

        # --- Bidirectional refs sync ---
        for field in ROLE_FIELDS:
            org = getattr(self, field, None)
            if org is None:
                continue
            try:
                refs = getattr(org, 'refs', None) or {}
                if not isinstance(refs, dict):
                    refs = {}
                links = refs.setdefault('links', {})
                contact_links = links.get('contact', [])
                contact_ids = [c.get('id') for c in contact_links if isinstance(c, dict)]
                if self.pk and self.pk not in contact_ids:
                    contact_links.append({'id': self.pk, 'name': str(self.attention or self.email or '')})
                    links['contact'] = contact_links
                    refs['links'] = links
                    org.__class__.objects.filter(pk=org.pk).update(refs=refs)
            except Exception:
                pass
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
    

