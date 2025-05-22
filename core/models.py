from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models import JSONField
from django.contrib.auth.models import BaseUserManager
from django.contrib.postgres.fields import ArrayField
import uuid

class ContactUserManager(BaseUserManager):
    def get_by_natural_key(self, email):
        return self.get(email=email)

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_email_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class Contact(AbstractBaseUser, PermissionsMixin):
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
    password = models.CharField(max_length=128)  # Handled by set_password
    verification_code = models.CharField(max_length=100, blank=True, null=True)
    verification_code_expiry = models.DateTimeField(blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    attention = models.CharField(max_length=255, blank=True, null=True)
    comment_alert = models.CharField(max_length=255, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    name_first = models.CharField(max_length=50, blank=True)
    name_last = models.CharField(max_length=50, blank=True)
    name_middle = models.CharField(max_length=50, blank=True, null=True)
    opt_out = models.CharField(max_length=255, blank=True, null=True)
    prefix = models.CharField(max_length=50, blank=True, null=True)
    publish = models.IntegerField(blank=True, null=True)
    rank = models.CharField(max_length=50, blank=True, null=True)
    salutation = models.CharField(max_length=50, blank=True, null=True)
    suffix = models.CharField(max_length=50, blank=True, null=True)
    role = ArrayField(
        models.CharField(max_length=50, choices=ROLE_CHOICES),
        default=list,
        blank=True
    )
    comment = models.TextField(blank=True, null=True)
    refs = JSONField(default=dict, blank=True)
    metadata = JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

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
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email