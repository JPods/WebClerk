"""
Role-Based Access Control (RBAC) Configuration Models.

These models define role permissions, per-model field access, and
denormalization templates for refs.links.

See readmes/topics/architecture/role-based-access-plan.md for full documentation.
"""
from django.conf import settings
from django.db import models
from common.models import BaseModel


class RoleConfig(BaseModel):
    """
    Role definition and global permissions.
    
    Roles control what users can see and edit across the application.
    Portal roles (is_portal=True) are for external users like customers/vendors.
    Internal roles are for employees with varying access levels.
    
    Example:
        role="user_sales", is_portal=False, parent_role="admin"
        permissions={"can_create_orders": True, "can_delete": False}
    """
    
    role = models.CharField(
        max_length=50, 
        unique=True, 
        db_index=True,
        help_text="Unique role identifier (e.g., 'user_sales', 'user_customer')"
    )
    description = models.TextField(
        blank=True,
        help_text="Human-readable description of the role"
    )
    is_portal = models.BooleanField(
        default=False,
        help_text="True for external users (customers, vendors, reps)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive roles are ignored during permission checks"
    )
    parent_role = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Inherit permissions from this role if not explicitly defined"
    )
    
    # Global permissions (not model-specific)
    permissions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Global permissions: {can_create_orders: true, can_export: true, ...}"
    )
    
    class Meta:
        db_table = 'core_roleconfig'
        verbose_name = 'Role Configuration'
        verbose_name_plural = 'Role Configurations'
    
    def __str__(self):
        portal = " (portal)" if self.is_portal else ""
        return f"{self.role}{portal}"


class ModelRoleConfig(BaseModel):
    """
    Per-model, per-role access configuration.
    
    Defines query filters, viewable fields, editable fields, and
    create/delete permissions for a specific model and role combination.
    
    Query filters use variables like $user.org_ids.customer that are
    resolved at runtime based on the authenticated user.
    
    Field lists support dotted paths:
        - "*" for all fields
        - "id", "status" for top-level fields
        - "totals.total" for nested JSON fields
        - "refs.tags" for refs fields
        - "lines.status" for related model fields
    
    Example:
        model_name="order", role="user_customer"
        query_filters={"customer_id__in": "$user.org_ids.customer"}
        view_fields=["id", "ida", "status", "totals.total"]
        edit_fields=[]
    """
    
    model_name = models.CharField(
        max_length=100, 
        db_index=True,
        help_text="Model name as registered in wcapi_registry"
    )
    role = models.CharField(
        max_length=50, 
        db_index=True,
        help_text="Role this config applies to"
    )
    
    # Query filtering - restricts which records the role can access
    query_filters = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Query filters applied to all queries. Supports OR conditions. "
            "Variables: $user.org_ids.customer, $user.contact_id"
        )
    )
    
    # Field access - separate view and edit lists
    view_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="Fields visible to this role. Use '*' for all, or list specific paths."
    )
    
    edit_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="Fields editable by this role. Supports dotted paths like 'refs.tags'."
    )
    
    # Permissions
    allow_create = models.BooleanField(
        default=False,
        help_text="Can this role create new records of this model?"
    )
    allow_delete = models.BooleanField(
        default=False,
        help_text="Can this role delete records of this model?"
    )
    
    class Meta:
        db_table = 'core_modelroleconfig'
        verbose_name = 'Model Role Configuration'
        verbose_name_plural = 'Model Role Configurations'
        unique_together = [('model_name', 'role')]
        indexes = [
            models.Index(fields=['model_name', 'role']),
        ]
    
    def __str__(self):
        return f"{self.model_name}:{self.role}"


class ModelLinkConfig(BaseModel):
    """
    Denormalization templates for refs.links entries.
    
    When a model is linked to another record (e.g., customer linked to order),
    this config defines:
    
    1. keyword_fields: Which fields to extract for refs.keywords searchability
    2. link_template: Structure of the refs.links.<model>[{...}] entry
    
    Link template values are field paths on the source model. Use null for
    fields that should be set at link time (e.g., role, commission_pc).
    
    Example:
        model_name="rep"
        keyword_fields=["display_name", "ida", "company"]
        link_template={
            "id": "id",
            "attention": "display_name",
            "company": "org.display_name",
            "role": null,
            "commission_pc": null
        }
    """
    
    model_name = models.CharField(
        max_length=100, 
        unique=True, 
        db_index=True,
        help_text="Model name for which this template applies"
    )
    
    # Fields to extract for refs.keywords when this model is linked
    keyword_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="Field names to include in refs.keywords: ['company', 'ida', 'email']"
    )
    
    # Template for refs.links.<model>[{...}]
    link_template = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Template mapping: {dest_field: source_path}. "
            "Use null for fields set at link time."
        )
    )
    
    class Meta:
        db_table = 'core_modellinkconfig'
        verbose_name = 'Model Link Configuration'
        verbose_name_plural = 'Model Link Configurations'
    
    def __str__(self):
        return f"{self.model_name} link template"


class UserProfile(BaseModel):
    """
    Extended user profile linking Django User to Contact.
    
    The contact record contains:
    - FKs to primary org (customer_id, vendor_id, etc.)
    - refs.links for additional org associations
    - refs.roles[] for assigned roles
    
    This enables user→role→org resolution for RBAC query filtering.
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        help_text="Django User this profile belongs to"
    )
    contact = models.ForeignKey(
        'core.Contact',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_profiles',
        help_text="Contact record containing org associations and roles"
    )
    
    # Cached role list for quick access (synced from contact.refs.roles)
    cached_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="Cached copy of contact.refs.roles for quick lookups"
    )
    
    class Meta:
        db_table = 'core_userprofile'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"Profile for {self.user.username}"
    
    def get_roles(self) -> list:
        """Get user's roles from contact.refs.roles."""
        if self.user.is_superuser:
            return ["superuser"]
        
        if not self.contact:
            return []
        
        refs = self.contact.refs or {}
        return refs.get("roles", [])
    
    def get_org_ids(self, org_type: str) -> list:
        """
        Get org IDs user is associated with for a given type.
        
        Args:
            org_type: One of 'customer', 'vendor', 'manufacturer', 'employee'
        
        Returns:
            List of org IDs from FK + refs.links
        """
        if not self.contact:
            return []
        
        ids = []
        
        # Primary FK
        fk_id = getattr(self.contact, f"{org_type}_id", None)
        if fk_id:
            ids.append(fk_id)
        
        # Additional from refs.links
        refs = self.contact.refs or {}
        links = refs.get("links", {}).get(org_type, [])
        for link in links:
            link_id = link.get("id") if isinstance(link, dict) else None
            if link_id:
                ids.append(link_id)
        
        return list(set(ids))
    
    def sync_cached_roles(self):
        """Sync cached_roles from contact.refs.roles."""
        self.cached_roles = self.get_roles()
        self.save(update_fields=["cached_roles", "dt_modified"])
