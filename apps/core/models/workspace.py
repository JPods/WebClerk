"""
Workspace — registered feature windows in the WebClerk UI.

Each workspace is a self-contained functional area: Apply Payments,
Cash Flow Forecast, Script Editor, Kanban, Gantt, Calendar, Console.

Workspaces have:
  - A component reference (which React component renders it)
  - Panels (sub-components within the workspace)
  - Permissions (who can see/use it)
  - Config (behavior settings, refresh intervals, limits)
  - Enabled/disabled state

The Workspace model replaces wc:workspace Setting records. Settings are
for configuration; workspaces are functional components with their own
lifecycle, permissions, and UI structure.

Usage:
    # All active workspaces for the sidebar
    Workspace.objects.filter(is_active=True, show_in_nav=True)

    # Check if user can access a workspace
    ws = Workspace.objects.get(ida='apply_payments')
    if ws.user_has_access(request.user):
        ...
"""
from django.db import models
from common.models import BaseModel


class Workspace(BaseModel):
    """A registered feature window in the WebClerk UI."""

    # ── Identity ──────────────────────────────────────────────────────
    name = models.CharField(max_length=255, help_text="Display name (e.g. 'Apply Payments')")
    component = models.CharField(
        max_length=255, blank=True,
        help_text="React component path (e.g. 'apps/accounting/ApplyPayments')",
    )
    icon = models.CharField(max_length=50, blank=True, help_text="Icon identifier for nav/toolbar")
    description = models.TextField(blank=True, help_text="What this workspace does")

    # ── Navigation ────────────────────────────────────────────────────
    route = models.CharField(
        max_length=255, blank=True,
        help_text="URL route segment (e.g. '/app/apply-payments')",
    )
    show_in_nav = models.BooleanField(default=True, help_text="Show in sidebar navigation")
    nav_order = models.IntegerField(default=100, help_text="Sort order in navigation")
    nav_group = models.CharField(
        max_length=100, blank=True,
        help_text="Navigation group (e.g. 'accounting', 'inventory', 'admin')",
    )

    # ── Permissions ───────────────────────────────────────────────────
    required_role = models.CharField(
        max_length=100, blank=True,
        help_text="Minimum role required (blank = all authenticated users)",
    )

    # ── Config ────────────────────────────────────────────────────────
    # Inherited from BaseModel:
    #   config (JSONField) — panels, refresh_interval, limits, etc.
    #   metadata (JSONField) — system metadata
    #   refs (JSONField) — cross-references
    #   prefs (JSONField) — user preferences overlay

    class Meta:
        db_table = 'workspace'
        ordering = ['nav_order', 'name']
        verbose_name = 'Workspace'
        verbose_name_plural = 'Workspaces'

    def __str__(self):
        return self.name

    def user_has_access(self, user) -> bool:
        """Check if a user has access to this workspace."""
        if not self.is_active:
            return False
        if not self.required_role:
            return user.is_authenticated
        profile = getattr(user, 'userprofile', None)
        if not profile:
            return user.is_superuser
        cached_roles = getattr(profile, 'cached_roles', []) or []
        return self.required_role in cached_roles or 'admin' in cached_roles
