"""
WebServing models — local inventory routing network.

Each WebClerk instance that opts in registers here. WebServing.com
queries registered instances to find local inventory for customers.

No central catalog. Each instance is sovereign. WebServing is the
router, not the owner.
"""
from django.db import models
from common.models import BaseModel


class RegisteredInstance(BaseModel):
    """A WebClerk installation registered in the routing network.

    Stores the instance's public API endpoint, geographic location,
    and connection health. Instances self-register via the /register/
    endpoint and heartbeat periodically.
    """
    # Identity
    instance_uuid = models.UUIDField(
        unique=True, db_index=True,
        help_text='UUID from the instance Setting(purpose=wc:company_profile).',
    )
    business_name = models.CharField(
        max_length=200,
        help_text='Display name — the business or store name.',
    )
    api_url = models.URLField(
        max_length=500,
        help_text='Public wcapi base URL (e.g. https://bobs-hardware.webclerk.com/wcapi/).',
    )

    # Location — required for radius search
    latitude = models.FloatField(
        help_text='Store latitude (WGS84).',
    )
    longitude = models.FloatField(
        help_text='Store longitude (WGS84).',
    )
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)

    # Subscription tier affects search ranking
    TIER_CHOICES = [
        ('free', 'Free — included in network'),
        ('standard', 'Standard — priority placement'),
        ('professional', 'Professional — priority + analytics'),
    ]
    tier = models.CharField(
        max_length=20, choices=TIER_CHOICES, default='free', db_index=True,
    )

    # Health
    dt_last_heartbeat = models.BigIntegerField(
        default=0,
        help_text='Last successful heartbeat (epoch ms). Stale > 24h.',
    )
    is_online = models.BooleanField(
        default=True, db_index=True,
        help_text='Set False when heartbeat fails 3 consecutive times.',
    )
    consecutive_failures = models.IntegerField(default=0)

    # Athena token for authenticated queries
    athena_token = models.CharField(
        max_length=200, blank=True,
        help_text='Token for querying this instance inventory.',
    )

    class Meta:
        db_table = 'webserving_instance'
        indexes = [
            models.Index(fields=['latitude', 'longitude'], name='ws_lat_lng_idx'),
            models.Index(fields=['is_online', 'tier'], name='ws_online_tier_idx'),
        ]
        ordering = ['-dt_last_heartbeat']

    def __str__(self):
        return f'{self.business_name} ({self.city}, {self.state})'


class SearchLog(BaseModel):
    """Log of searches performed through WebServing.com.

    Alice uses these to learn demand patterns — what are people
    searching for, where, and whether they find it locally.
    """
    query = models.CharField(max_length=500)
    latitude = models.FloatField()
    longitude = models.FloatField()
    radius_miles = models.FloatField(default=5.0)
    results_count = models.IntegerField(default=0)
    instances_queried = models.IntegerField(default=0)
    instances_responded = models.IntegerField(default=0)
    elapsed_ms = models.IntegerField(default=0)

    class Meta:
        db_table = 'webserving_search_log'
        indexes = [
            models.Index(fields=['-dt_created'], name='ws_search_dt_idx'),
        ]
        ordering = ['-dt_created']

    def __str__(self):
        return f'"{self.query}" — {self.results_count} results'
