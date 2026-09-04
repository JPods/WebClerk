"""
WebServing models — local commerce directory and inventory router.

WebServing is a business directory (like Google Maps / Yelp) combined
with a live inventory router. The directory data lives here; the
inventory stays at each store's own WebClerk instance and is queried
in real time.

All models use plain Django — no BaseModel, no WC3 dependencies.
WebServing has its own database (commerce_webserving) and can be
deployed independently.
"""
import uuid
from django.db import models


class Category(models.Model):
    """Business category — hierarchical.

    Examples: Sporting Goods, Hearth Products, Hardware, Grocery.
    Stores can belong to multiple categories.
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='children',
    )
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'webserving_category'
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Company(models.Model):
    """A business listed in the WebServing directory.

    This is the public-facing store profile — what a searcher sees.
    The inventory is queried live from the store's own WebClerk instance
    via api_url. WebServing never stores inventory.

    Fields modeled after Google Maps / Yelp business listings:
    identity, location, contact, hours, categories, ratings.
    """
    # Identity
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    logo_url = models.URLField(max_length=500, blank=True)

    # Location
    address = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=50, default='US')
    latitude = models.FloatField()
    longitude = models.FloatField()

    # Contact
    domain = models.CharField(max_length=200, blank=True, help_text='Store website.')
    phones = models.JSONField(
        default=list, blank=True,
        help_text='[{"dept": "sales", "number": "918-555-0100", "hours": "9-5"}, ...]',
    )
    email = models.EmailField(blank=True)

    # Categories
    categories = models.ManyToManyField(
        Category, blank=True, related_name='companies',
    )

    # Hours of operation
    hours = models.JSONField(
        default=dict, blank=True,
        help_text='{"mon": ["9:00","17:00"], "tue": ["9:00","17:00"], ...}',
    )

    # Ratings (aggregated from reviews)
    rating_avg = models.FloatField(default=0.0)
    rating_count = models.IntegerField(default=0)

    # WebClerk connection
    instance_uuid = models.UUIDField(
        null=True, blank=True, unique=True,
        help_text='UUID from the WebClerk instance wc:company_profile Setting.',
    )
    api_url = models.URLField(
        max_length=500, blank=True,
        help_text='WebClerk wcapi base URL for live inventory queries.',
    )
    athena_token = models.CharField(
        max_length=200, blank=True,
        help_text='Auth token for querying this instance.',
    )

    # Network membership
    TIER_CHOICES = [
        ('free', 'Free — included in network'),
        ('standard', 'Standard — priority placement'),
        ('professional', 'Professional — priority + analytics'),
    ]
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='free')

    # Health
    is_online = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    dt_last_heartbeat = models.DateTimeField(null=True, blank=True)
    consecutive_failures = models.IntegerField(default=0)

    # Staff contact — the person who keeps this listing current
    contact_name = models.CharField(max_length=200, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)

    # Timestamps
    dt_created = models.DateTimeField(auto_now_add=True)
    dt_modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webserving_company'
        indexes = [
            models.Index(fields=['latitude', 'longitude'], name='ws_co_lat_lng_idx'),
            models.Index(fields=['is_online', 'is_active', 'tier'], name='ws_co_online_idx'),
            models.Index(fields=['city', 'state'], name='ws_co_city_state_idx'),
        ]
        ordering = ['name']
        verbose_name_plural = 'companies'

    def __str__(self):
        return f'{self.name} ({self.city}, {self.state})'


class Review(models.Model):
    """Customer review of a store."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(help_text='1-5 stars.')
    text = models.TextField(blank=True)
    author_name = models.CharField(max_length=100, blank=True)
    source = models.CharField(
        max_length=50, default='webserving',
        help_text='Origin: webserving, google, yelp, etc.',
    )
    dt_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webserving_review'
        ordering = ['-dt_created']

    def __str__(self):
        return f'{self.company.name} — {self.rating}★ by {self.author_name}'


class SearchLog(models.Model):
    """Log of searches — Alice's demand signal.

    What people search for, where, and whether they find it locally.
    Zero-result searches are demand gaps.
    """
    query = models.CharField(max_length=500)
    latitude = models.FloatField()
    longitude = models.FloatField()
    radius_miles = models.FloatField(default=5.0)
    results_count = models.IntegerField(default=0)
    stores_queried = models.IntegerField(default=0)
    stores_responded = models.IntegerField(default=0)
    elapsed_ms = models.IntegerField(default=0)
    dt_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webserving_search_log'
        indexes = [
            models.Index(fields=['-dt_created'], name='ws_search_dt_idx'),
        ]
        ordering = ['-dt_created']

    def __str__(self):
        return f'"{self.query}" — {self.results_count} results'


class HealthCheck(models.Model):
    """API health check record for a company.

    Tracks response time, status, and failures over time.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='health_checks')
    is_reachable = models.BooleanField()
    response_ms = models.IntegerField(null=True, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    error = models.CharField(max_length=200, blank=True)
    dt_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webserving_health'
        indexes = [
            models.Index(fields=['company', '-dt_created'], name='ws_health_co_dt_idx'),
        ]
        ordering = ['-dt_created']

    def __str__(self):
        status = 'UP' if self.is_reachable else 'DOWN'
        return f'{self.company.name} — {status} ({self.response_ms}ms)'
