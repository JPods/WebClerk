<<<<<<< HEAD:core/models/contact.py
# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/models/contact.py
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

# Django requires a custom manager for custom user models.
# ContactManager inherits from BaseUserManager (from django.contrib.auth.models)
# and provides create_user and create_superuser methods for authentication.
class ContactManager(BaseUserManager):
    """Custom user manager for Contact model (Django authentication)"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user"""
        if not email:
            raise ValueError('The Email field must be set')
        
=======
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.contrib.postgres.fields import ArrayField
from common.base_model import BaseModel
import uuid

class ContactUserManager(BaseUserManager):
    def get_by_natural_key(self, email):
        return self.get(email=email)

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
>>>>>>> 01558f6ebce5d18d828e022158343627fc8162d8:apps/core/models/contact.py
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
<<<<<<< HEAD:core/models/contact.py
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)
    
    def get_by_natural_key(self, email):
        return self.get(**{self.model.USERNAME_FIELD: email})


# see ContactManager below that is used for authentication
class Contact(BaseModel, AbstractBaseUser, PermissionsMixin):
    """
    Contact model with Universal API metadata support and Django authentication
    Uses JSON metadata field instead of inheriting BaseModel to avoid dt_created conflicts
    """
    
    # Role choices for Universal API and serializers
    ROLE_CHOICES = [
        ('user', 'User'),
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('guest', 'Guest'),
    ]
    
    # Core Identity Fields - Django auto-creates 'id' as primary key
    # REMOVED: id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    email = models.EmailField(unique=True, help_text="Primary email address for login")
    
    # Name Fields
    name_first = models.CharField(max_length=100, blank=True, help_text="First name")
    name_last = models.CharField(max_length=100, blank=True, help_text="Last name")
    name_middle = models.CharField(max_length=100, blank=True, help_text="Middle name")
    name_prefix = models.CharField(max_length=20, blank=True, help_text="Title (Mr., Ms., Dr.)")
    name_suffix = models.CharField(max_length=20, blank=True, help_text="Suffix (Jr., Sr., III)")
    
    
    # Business Fields
    company = models.CharField(max_length=200, blank=True, help_text="Company name")
    title = models.CharField(max_length=100, blank=True, help_text="Job title")
    department = models.CharField(max_length=100, blank=True, help_text="Department")
    comment = models.TextField(blank=True, help_text="Additional comments")
    # System Fields
    role = models.CharField(
        max_length=50, 
        choices=ROLE_CHOICES, 
        default='user', 
        help_text="User role in system"
    )
    is_active = models.BooleanField(default=True, help_text="User account is active")
    is_staff = models.BooleanField(default=False, help_text="User can access admin")
    date_joined = models.DateTimeField(default=timezone.now, help_text="Account creation date")
    
 
    
    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name_first', 'name_last']
    
    objects = ContactManager()
    
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
    

        # Auto-assign admin role to superusers
        if self.is_superuser and self.role != 'admin':
            self.role = 'admin'
        
        super().save(*args, **kwargs)
    
    @property
    def display_name(self):
        """Property for template display"""
        return self.get_full_name()

    # all metadata changes inside common/models/BaseModel.py

    def has_addresses(self):
        """Check if contact has any addresses"""
        return hasattr(self, 'addresses') and self.addresses.exists()
    
    def has_phones(self):
        """Check if contact has any phone numbers"""
        return hasattr(self, 'phones') and self.phones.exists()
    
    def has_emails(self):
        """Check if contact has any additional emails"""
        return hasattr(self, 'emails') and self.emails.exists()
    
    def has_domains(self):
        """Check if contact has any domains"""
        return hasattr(self, 'domains') and self.domains.exists()
    
    def get_role_display_name(self):
        """Get human-readable role name"""
        return dict(self.ROLE_CHOICES).get(self.role, self.role)
    
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
    

=======

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_email_verified', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('role', ['SUPER'])

        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class Contact(BaseModel, AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('SUPER', 'Superuser'),
        ('ADMIN', 'Administrator'),
        ('SALE', 'Sales'),
        ('REP', 'Representative'),
        ('VENDOR', 'Vendor'),
        ('CUSTOMER', 'Customer'),
        ('USER', 'User'),
        ('PUBLIC', 'Public'),
    ]

    id = models.BigAutoField(primary_key=True)
    uuid = models.CharField(max_length=36, unique=True, editable=False)
    email = models.EmailField(unique=True)
    opt_out = models.JSONField(default=None, null=True)
    password = models.CharField(max_length=128)
    role = models.CharField(
        max_length=50, 
        choices=ROLE_CHOICES, 
        default='USER', 
        help_text="User role in system"
    )
    role_default = models.CharField(max_length=50, blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login = models.DateTimeField(blank=True, null=True)
    attention = models.CharField(max_length=255, blank=True, null=True)
    comment_alert = models.CharField(max_length=255, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    name_first = models.CharField(max_length=50)
    name_last = models.CharField(max_length=50)
    name_middle = models.CharField(max_length=50, blank=True, null=True)
    prefix = models.CharField(max_length=50, blank=True, null=True)
    suffix = models.CharField(max_length=50, blank=True, null=True)
    salutation = models.CharField(max_length=50, blank=True, null=True)
    publish = models.IntegerField(blank=True, null=True)
    rank = models.CharField(max_length=50, blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, null=True)
    verification_code = models.CharField(max_length=100, blank=True, null=True)
    verification_code_expiry = models.DateTimeField(blank=True, null=True)

    objects = ContactUserManager()

    class Meta:
        db_table = 'contacts'

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name_first', 'name_last']

    def save(self, *args, **kwargs):
        if not self.uuid:
            self.uuid = str(uuid.uuid4())
        if self.is_superuser and 'SUPER' not in self.role:
            self.role = ['SUPER'] if not self.role else list(set(self.role + ['SUPER']))
        if not self.metadata:
            self.metadata = BaseModel.metadata.field.get_default()
        super(Contact, self).save(*args, **kwargs)

    def __str__(self):
        return self.email
>>>>>>> 01558f6ebce5d18d828e022158343627fc8162d8:apps/core/models/contact.py
