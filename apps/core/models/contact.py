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
        """
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        if 'first_name' in extra_fields or 'last_name' in extra_fields:
            raise TypeError('Use name_first / name_last fields (legacy first_name/last_name no longer accepted)')
        # Drop any provided username silently (no legacy username field in model)
        user = self.model(email=email, **extra_fields)
        # Some databases enforce NOT NULL on uuid; ensure it's populated on create
        if not getattr(user, 'uuid', None):
            user.uuid = uuid.uuid4()
        user.set_password(password)
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
    
    # Core Identity Fields - Django auto-creates 'id' as primary key
    # REMOVED: id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
 
    
    # Name Fields
    name_first = models.CharField(max_length=100, blank=True, help_text="First name")
    name_last = models.CharField(max_length=100, blank=True, help_text="Last name")
    name_middle = models.CharField(max_length=100, blank=True, help_text="Middle name")
    name_prefix = models.CharField(max_length=20, blank=True, help_text="Title (Mr., Ms., Dr.)")
    name_suffix = models.CharField(max_length=20, blank=True, help_text="Suffix (Jr., Sr., III)")
    attention = models.CharField(max_length=201, blank=True, help_text="Auto-filled attention line from first and last name")

    email = models.EmailField(unique=True, help_text="Primary email address for login")
    email_id = models.BigIntegerField(blank=True, null=True, help_text="Optional FK to primary email record if needed")
    address_full = models.CharField(max_length=500, blank=True, null=True)  # optional denormalized full address for quick display/search
    address_id = models.BigIntegerField(blank=True, null=True, help_text="Optional FK to primary address record if needed")
    phone = models.CharField(max_length=50, blank=True, null=True)  # optional primary phone (could be denormalized from phones aspect)
    phone_id = models.BigIntegerField(blank=True, null=True, help_text="Optional FK to primary phone record if needed")
    domain = models.CharField(max_length=255, blank=True, null=True, help_text="Primary domain extracted from email for quick search")
    domain_id = models.BigIntegerField(blank=True, null=True, help_text="Optional FK to primary domain record if needed")
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
    other_id = models.BigIntegerField(null=True, blank=True, help_text="Other associated ID if applicable")
    company = models.CharField(max_length=200, blank=True, help_text="Company name")
    title = models.CharField(max_length=100, blank=True, help_text="Job title")
    department = models.CharField(max_length=100, blank=True, help_text="Department")
    # General notes / legacy compatibility (column exists with NOT NULL constraint in current schema)
    comment = models.TextField(blank=True, default="", help_text="General notes about this contact")
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
        """String representation of contact"""
        if self.name_first or self.name_last:
            return f"{self.name_first} {self.name_last}".strip()
        return self.email
    
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
    # Backward compatibility properties for legacy code/tests referencing first_name/last_name
    @property
    def first_name(self):  # pragma: no cover - simple alias
        return self.name_first
    @first_name.setter
    def first_name(self, value):  # pragma: no cover
        self.name_first = value
    @property
    def last_name(self):  # pragma: no cover
        return self.name_last
    @last_name.setter
    def last_name(self, value):  # pragma: no cover
        self.name_last = value
    

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
        """Synchronize primary scalar comm values with communication models and refs.links."""
        try:
            from apps.communications.models import Address, Domain, Email, Phone

            updates = {}

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

            normalized_phone = self._norm_comm_value(self.phone)
            if normalized_phone:
                phone_obj = self._find_or_create_comm_record(
                    Phone,
                    {'number': normalized_phone},
                    {'number': normalized_phone, 'name': 'primary'},
                )
                if self.phone_id != phone_obj.id:
                    updates['phone_id'] = phone_obj.id

            normalized_domain = self._norm_comm_value(self.domain)
            if normalized_domain:
                domain_obj = self._find_or_create_comm_record(
                    Domain,
                    {'path': normalized_domain},
                    {'path': normalized_domain, 'type': 'website', 'status': 'active'},
                )
                if self.domain_id != domain_obj.id:
                    updates['domain_id'] = domain_obj.id

            normalized_address_full = self._norm_comm_value(self.address_full)
            if normalized_address_full:
                own_addr = Address.objects.filter(
                    contact_id=self.pk,
                ).filter(Q(full=normalized_address_full) | Q(address1=normalized_address_full)).first()
                if own_addr:
                    address_obj = own_addr
                else:
                    unowned_addr = Address.objects.filter(contact__isnull=True).filter(
                        Q(full=normalized_address_full) | Q(address1=normalized_address_full),
                    ).first()
                    if unowned_addr:
                        unowned_addr.contact_id = self.pk
                        unowned_addr.save(update_fields=['contact', 'dt_modified'])
                        address_obj = unowned_addr
                    else:
                        address_obj = Address.objects.create(
                            contact_id=self.pk,
                            address1=normalized_address_full,
                            full=normalized_address_full,
                        )

                if self.address_id != address_obj.id:
                    updates['address_id'] = address_obj.id

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
    
    def _ensure_account_email_linked(self):
        """
        If the account email (self.email) is not already in refs.links.email,
        create an Email record and link it with name='account'.
        """
        # Kept for backward compatibility. Primary comm sync now handles this.
        self._sync_primary_communication_links()
    
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
        # Custom logic after fields are set, before save
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
    

