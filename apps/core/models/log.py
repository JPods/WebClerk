from django.db import models
from django.contrib.auth import get_user_model
from common.models import BaseModel

User = get_user_model()


class APILog(BaseModel):
    """Log for tracking API requests between systems (R25, WC3, external services)."""

    class Meta:
        db_table = 'api_logs'
        indexes = [
            models.Index(fields=['source', 'dt_created']),
            models.Index(fields=['destination', 'dt_created']),
            models.Index(fields=['endpoint', 'status_code']),
            models.Index(fields=['correlation_id']),
            models.Index(fields=['user_id', 'dt_created']),
        ]

    # Source/destination systems
    SOURCE_CHOICES = [
        ('r25', 'React2025 Frontend'),
        ('wc3', 'WebClerk3 Internal'),
        ('ext', 'External Service'),
    ]
    source = models.CharField(
        max_length=10,
        choices=SOURCE_CHOICES,
        help_text="System that initiated the request"
    )
    destination = models.CharField(
        max_length=100,
        help_text="Target system (e.g., 'wc3', 'shipstation', 'quickbooks', 'stripe')"
    )

    # Request details
    method = models.CharField(
        max_length=10,
        help_text="HTTP method (GET, POST, PUT, DELETE, etc.)"
    )
    endpoint = models.CharField(
        max_length=500,
        help_text="API endpoint path"
    )
    request_headers = models.JSONField(
        default=dict,
        blank=True,
        help_text="Request headers (sensitive data should be redacted)"
    )
    request_body = models.JSONField(
        default=dict,
        blank=True,
        help_text="Request body/payload"
    )

    # Response details
    status_code = models.IntegerField(
        null=True,
        blank=True,
        help_text="HTTP response status code"
    )
    response_headers = models.JSONField(
        default=dict,
        blank=True,
        help_text="Response headers"
    )
    response_body = models.JSONField(
        default=dict,
        blank=True,
        help_text="Response body (may be truncated for large responses)"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if request failed"
    )

    # Timing
    duration_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Request duration in milliseconds"
    )

    # Context
    user_id = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='api_logs',
        help_text="User who triggered the request"
    )
    correlation_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="UUID to link related requests across systems"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Client IP address"
    )

    # Additional context
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context (model_name, record_id, etc.)"
    )

    def __str__(self):
        return f"APILog: {self.source}→{self.destination} {self.method} {self.endpoint} [{self.status_code}]"

    @property
    def is_success(self) -> bool:
        """Check if the request was successful (2xx status code)."""
        return self.status_code is not None and 200 <= self.status_code < 300

    @property
    def is_error(self) -> bool:
        """Check if the request resulted in an error (4xx or 5xx)."""
        return self.status_code is not None and self.status_code >= 400

    @classmethod
    def log_request(
        cls,
        source: str,
        destination: str,
        method: str,
        endpoint: str,
        request_body: dict = None,
        request_headers: dict = None,
        status_code: int = None,
        response_body: dict = None,
        response_headers: dict = None,
        error_message: str = '',
        duration_ms: int = None,
        user=None,
        correlation_id: str = '',
        ip_address: str = None,
        metadata: dict = None,
        request=None,
    ):
        """Convenience method to create an API log entry.
        
        Args:
            source: System initiating request ('r25', 'wc3', 'ext')
            destination: Target system name
            method: HTTP method
            endpoint: API endpoint path
            request_body: Request payload
            request_headers: Request headers (will redact sensitive data)
            status_code: HTTP response code
            response_body: Response payload
            response_headers: Response headers
            error_message: Error description if failed
            duration_ms: Request duration in milliseconds
            user: User who triggered the request
            correlation_id: UUID linking related requests
            ip_address: Client IP
            metadata: Additional context
            request: Django request object (to extract user, IP)
        """
        # Extract from request if provided
        if request:
            if not user:
                user = getattr(request, 'user', None)
                if user and not user.is_authenticated:
                    user = None
            if not ip_address:
                ip_address = cls._get_client_ip(request)
            if not correlation_id:
                correlation_id = request.headers.get('X-Correlation-ID', '')

        # Redact sensitive headers
        safe_request_headers = cls._redact_headers(request_headers or {})
        safe_response_headers = cls._redact_headers(response_headers or {})

        return cls.objects.create(
            source=source,
            destination=destination,
            method=method.upper(),
            endpoint=endpoint,
            request_headers=safe_request_headers,
            request_body=request_body or {},
            status_code=status_code,
            response_headers=safe_response_headers,
            response_body=response_body or {},
            error_message=error_message or '',
            duration_ms=duration_ms,
            user_id=user,
            correlation_id=correlation_id or '',
            ip_address=ip_address,
            metadata=metadata or {},
        )

    @staticmethod
    def _get_client_ip(request) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    @staticmethod
    def _redact_headers(headers: dict) -> dict:
        """Redact sensitive header values."""
        sensitive_keys = {'authorization', 'cookie', 'x-api-key', 'api-key', 'token', 'secret'}
        return {
            k: '[REDACTED]' if k.lower() in sensitive_keys else v
            for k, v in headers.items()
        }


__all__ = ["APILog"]
