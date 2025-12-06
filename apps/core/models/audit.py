from django.db import models
from django.contrib.auth import get_user_model
from common.models import BaseModel

User = get_user_model()


class AuditLog(BaseModel):
    """Audit log for tracking all system changes."""

    class Meta:
        db_table = 'audit_logs'
        indexes = [
            models.Index(fields=['model_name', 'record_id']),
            models.Index(fields=['user', 'dt_created']),
            models.Index(fields=['action', 'dt_created']),
        ]

    # Who performed the action
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="User who performed the action"
    )

    # What was changed
    model_name = models.CharField(
        max_length=100,
        help_text="Model that was changed (e.g., 'proposal', 'sales_order')"
    )
    record_id = models.BigIntegerField(
        help_text="ID of the record that was changed"
    )

    # Action details
    action = models.CharField(
        max_length=50,
        help_text="Action performed (e.g., 'created', 'updated', 'deleted', 'transferred')"
    )

    # Change details
    changes = models.JSONField(
        default=dict,
        help_text="Details of what changed (old vs new values)"
    )

    # Context
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the user"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string from the request"
    )
    session_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Session ID for tracking user sessions"
    )

    # Additional metadata
    metadata = models.JSONField(
        default=dict,
        help_text="Additional context about the action"
    )

    def __str__(self):
        return f"AuditLog: {self.user} {self.action} {self.model_name} {self.record_id}"

    @classmethod
    def log_action(
        cls,
        user=None,
        model_name=None,
        record_id=None,
        action=None,
        changes=None,
        ip_address=None,
        user_agent=None,
        session_id=None,
        metadata=None,
        request=None
    ):
        """Convenience method to create an audit log entry."""
        if request and not user:
            user = getattr(request, 'user', None)
        if request and not ip_address:
            ip_address = cls._get_client_ip(request)
        if request and not user_agent:
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        if request and not session_id:
            session_id = request.session.session_key

        return cls.objects.create(
            user=user,
            model_name=model_name,
            record_id=record_id,
            action=action,
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            metadata=metadata or {}
        )

    @staticmethod
    def _get_client_ip(request):
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


__all__ = ["AuditLog"]