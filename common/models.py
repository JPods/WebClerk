# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/common/models.py
# PURPOSE: Base model with Universal API metadata system for ALL models
# UNIVERSAL API: Provides foundation metadata structure that makes Universal API work
# REPLACES: Individual metadata handling scattered across different models
# TEAM NOTE: Every model inherits from BaseModel to get Universal API compatibility
# ARCHITECTURE: Implements the 4D-style metadata system (history, health, refs, prefs)
# METADATA STRUCTURE: 
#   - history.dt.created/modified (timestamps)
#   - health.rating (data quality scores)
#   - refs.keywords (searchable keywords)
#   - prefs (user preferences)
# FEATURES:
#   - Automatic timestamp management
#   - Keyword generation from all fields
#   - Undefined field capture
#   - JSON metadata storage
# TABLES: Base class inherited by all models (contacts, addresses, phones, emails, etc.)

# All timestamps are saved as GMT/UTC (Universal API standard)

from django.db import models
import uuid
from django.utils import timezone
import json
from django.contrib.postgres.indexes import GinIndex

MAX_METADATA_SIZE = 320000  # bytes
MAX_REFS_SIZE = 320000      # bytes
MAX_PREFS_SIZE = 320000     # bytes

# functions must be defined before they are used

def default_metadata():
    now_ms = int(timezone.now().timestamp() * 1000)
    return {
        "security": "",
        "publish": "",
        "priority": "",
        "version": "1.0",
        "access": {"view": [], "edit": []},
        "history": {
            "created": {"dt": now_ms, "contact_id": 0},
            "modified": {"dt": now_ms, "contact_id": 0},
            "accessed": {"dt": now_ms, "contact_id": 0},
            "verified": {"dt": 0, "contact_id": 0},
            "synced": {"dt": 0, "contact_id": 0}
        },
        "health": {
            "rating": 0,
            "completeness": 0,
            "accuracy": 0,
            "freshness": 0,
            "consistency": 0
        },
        "undefined": {}
    }

def default_refs():
    return {
        "keywords": [],
        "tags": [],
        #QQQ add linkages
        "links": {"contacts": []},
        "categories": [],
        "related_ids": []
    }

def default_prefs():
    return {"userdefined": ""}

def default_data():
    return {}

class BaseModel(models.Model):
    """
    Base model that provides Universal API metadata structure.
    All models in the system inherit from this to get Universal API compatibility.
    Implements the 4D-style metadata system with modern Django features.
    """
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ida = models.CharField(max_length=40, blank=True, help_text="Alternate ID for external systems")
    metadata = models.JSONField(default=default_metadata, help_text="Universal API metadata structure")
    refs = models.JSONField(default=default_refs, help_text="References: keywords, tags, categories")
    prefs = models.JSONField(default=default_prefs, help_text="User preferences and settings")
    comments = models.JSONField(default=default_prefs, help_text="User comments and notes")
    health_rating = models.IntegerField(default=0, help_text="Data quality rating (0-100)")

    class Meta:
        abstract = True
        indexes = [
            GinIndex(fields=['refs'], name='refs_gin_idx'),
            GinIndex(fields=['prefs'], name='prefs_gin_idx'),
        ]

    def save(self, *args, **kwargs):
        now_timestamp = int(timezone.now().timestamp() * 1000)  # UTC milliseconds
        self.metadata['history']['modified'] = {
            'dt': now_timestamp,
            'contact_id': getattr(self, 'modified_by_id', 0)
        }
        if not self.pk:
            self.metadata['history']['created'] = {
                'dt': now_timestamp,
                'contact_id': getattr(self, 'created_by_id', 0)
            }
        self.update_keywords()
        def check_size(field_value, max_size, field_name):
            size = len(json.dumps(field_value).encode('utf-8'))
            if size > max_size:
                raise ValueError(f"{field_name} exceeds maximum size of {max_size} bytes")
        check_size(self.metadata, MAX_METADATA_SIZE, "metadata")
        check_size(self.refs, MAX_REFS_SIZE, "refs")
        check_size(self.prefs, MAX_PREFS_SIZE, "prefs")
        super().save(*args, **kwargs)

    def update_keywords(self):
        keywords = []
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                value = getattr(self, field.name, '')
                if value:
                    words = str(value).lower().split()
                    keywords.extend([word.strip('.,!?;:"()[]{}') for word in words if len(word) > 2])
        self.refs['keywords'] = list(set(keywords))[:50]

    def get_metadata_value(self, key_path):
        keys = key_path.split('.')
        value = self.metadata
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return None

    def set_metadata_value(self, key_path, value):
        keys = key_path.split('.')
        target = self.metadata
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value

    def add_keyword(self, keyword):
        if keyword.lower() not in [k.lower() for k in self.refs['keywords']]:
            self.refs['keywords'].append(keyword.lower())

    def add_tag(self, tag):
        if tag not in self.refs['tags']:
            self.refs['tags'].append(tag)

    def get_created_timestamp(self):
        return self.get_metadata_value('history.created.dt') or 0

    def get_modified_timestamp(self):
        return self.get_metadata_value('history.modified.dt') or 0

    @property
    def dt_verified(self):
        """Get verified timestamp from metadata.history.verified.dt (as GMT/UTC)."""
        if not self.metadata:
            return None
        verified_dt_ms = self.metadata.get('history', {}).get('verified', {}).get('dt', 0)
        if verified_dt_ms:
            return timezone.datetime.fromtimestamp(verified_dt_ms / 1000, tz=timezone.utc)
        return None

    def set_comments(self, partner=None, process=None, public=None):
        """
        Populate the comments JSONB with .partner, .process, .public keys.
        """
        if not isinstance(self.comments, dict):
            self.comments = {}
        if partner is not None:
            self.comments['partner'] = partner
        if process is not None:
            self.comments['process'] = process
        if public is not None:
            self.comments['public'] = public
        self.save()

    def __str__(self):
        if hasattr(self, 'name'):
            return str(self.name)
        elif hasattr(self, 'title'):
            return str(self.title)
        elif hasattr(self, 'email'):
            return str(self.email)
        else:
            return f"{self.__class__.__name__} #{self.pk}"

