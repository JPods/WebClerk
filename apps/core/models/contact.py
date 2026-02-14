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
    
    
    # Business Fields a person can be associated with multiple orgs. A vendor may be a manufaucturer, customer, and a rep. Tranaction differ but the contact and relationship with the person is the same.
    employee_id = models.BigIntegerField(null=True, blank=True, help_text="Associated employee ID if applicable")
    customer_id = models.BigIntegerField(null=True, blank=True, help_text="Associated customer ID if applicable")
    vendor_id = models.BigIntegerField(null=True, blank=True, help_text="Associated vendor ID if applicable")
    manufacturer_id = models.BigIntegerField(null=True, blank=True, help_text="Associated manufacturer ID if applicable")
    rep_id = models.BigIntegerField(null=True, blank=True, help_text="Associated sales rep ID if applicable")
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
        
        # After save, ensure account email exists as an Email record linked to this contact
        self._ensure_account_email_linked()
    
    def _ensure_account_email_linked(self):
        """
        If the account email (self.email) is not already in refs.links.email,
        create an Email record and link it with name='account'.
        """
        if not self.email:
            return
        
        # Check if email already exists in refs.links.email
        refs = self.refs if isinstance(self.refs, dict) else {}
        links = refs.get('links', {})
        if not isinstance(links, dict):
            links = {}
        email_links = links.get('email', [])
        if not isinstance(email_links, list):
            email_links = []
        
        # Check if account email is already linked
        for email_entry in email_links:
            if isinstance(email_entry, dict) and email_entry.get('email') == self.email:
                return  # Already linked, nothing to do
        
        # Create the Email record and link it
        try:
            from apps.communications.models import Email
            
            # Check if an Email record with this address already exists
            existing_email = Email.objects.filter(email=self.email).first()
            if existing_email:
                email_obj = existing_email
            else:
                email_obj = Email.objects.create(
                    email=self.email,
                    name='account',
                    is_primary=True,
                    is_verified=False,
                )
            
            # Add to refs.links.email
            email_link = {
                'id': email_obj.id,
                'email': email_obj.email,
                'name': 'account',
                'is_primary': True,
            }
            email_links.append(email_link)
            links['email'] = email_links
            refs['links'] = links
            
            # Update refs without triggering another full save (avoid recursion)
            type(self).objects.filter(pk=self.pk).update(refs=refs)
            # Refresh the in-memory refs
            self.refs = refs
        except Exception as e:
            # Log but don't fail the contact save
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to auto-create account email record for contact {self.pk}: {e}")
    
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
        print("Pre-save logic here")
        # return False  # Return False to abort save
        return True  # Return False to abort save

    def save_after(self, data):
        # Custom logic after fields are set, before save
        print("Post-save logic here")
        # return False  # Return False to abort save
        return True  # Return False to abort save

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
    

