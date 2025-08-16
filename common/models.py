# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/common/models.py
# 
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

from django.db import models
import uuid


def default_metadata():
    """Default metadata structure for Universal API compatibility"""
    return {
        "security": "",
        "publish": "",
        "priority": "",
        "version": "1.0",
        "access": {"view": [], "edit": []},
        "history": {
            "created": {"dt": int(timezone.now().timestamp() * 1000), "contact_id": 0},
            "modified": {"dt": int(timezone.now().timestamp() * 1000), "contact_id": 0},
            "accessed": {"dt": int(timezone.now().timestamp() * 1000), "contact_id": 0},
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
    """Default refs structure for Universal API"""
    return {
        "keywords": [],
        "tags": [],
        "links": {"contacts": []},
        "categories": [],
        "related_ids": []
    }


def default_prefs():
    """Default preferences structure for Universal API"""
    return {"userdefined": ""}


def default_data():
    """Return the default structure for the data field in Pending records."""
    return {}


MAX_METADATA_SIZE = 320000  # bytes
MAX_REFS_SIZE = 320000      # bytes
MAX_PREFS_SIZE = 320000     # bytes

class BaseModel(models.Model):
    """
    Base model that provides Universal API metadata structure
    All models in the system inherit from this to get Universal API compatibility
    Implements the 4D-style metadata system with modern Django features
    """
    
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Universal API Metadata - Core of the 4D-style system
    metadata = models.JSONField(default=default_metadata, help_text="Universal API metadata structure")
    
    # Individual metadata fields for easier access and indexing
    refs = models.JSONField(default=default_refs, help_text="References: keywords, tags, categories")
    prefs = models.JSONField(default=default_prefs, help_text="User preferences and settings")
    
    # Timestamp fields for Universal API compatibility
    #dt_created = models.DateTimeField(auto_now_add=True, help_text="Record creation timestamp")
    #dt_modified = models.DateTimeField(auto_now=True, help_text="Record modification timestamp")
  
    # Health and quality metrics
    health_rating = models.IntegerField(default=0, help_text="Data quality rating (0-100)")
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        """Override save to update Universal API metadata"""
        now_timestamp = int(timezone.now().timestamp() * 1000)
        
        # Initialize metadata if it doesn't exist
        if not self.metadata:
            self.metadata = default_metadata()
        
        # Update modification timestamp
        if 'history' not in self.metadata:
            self.metadata['history'] = {}
        
        self.metadata['history']['modified'] = {
            'dt': now_timestamp,
            'contact_id': getattr(self, 'modified_by_id', 0)
        }
        
        # Set creation timestamp for new records
        if not self.pk:
            self.metadata['history']['created'] = {
                'dt': now_timestamp,
                'contact_id': getattr(self, 'created_by_id', 0)
            }
        
        # Update keywords from all text fields
        self.update_keywords()
        
        # Enforce size limits
        import sys

        def check_size(field_value, max_size, field_name):
            size = len(json.dumps(field_value).encode('utf-8'))
            if size > max_size:
                raise ValueError(f"{field_name} exceeds maximum size of {max_size} bytes")

        check_size(self.metadata, MAX_METADATA_SIZE, "metadata")
        check_size(self.refs, MAX_REFS_SIZE, "refs")
        check_size(self.prefs, MAX_PREFS_SIZE, "prefs")

        super().save(*args, **kwargs)
    
    def update_keywords(self):
        """Generate keywords from all text fields for Universal API search"""
        keywords = []
        
        # Get all text fields from the model
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                value = getattr(self, field.name, '')
                if value:
                    # Split into words and add to keywords
                    words = str(value).lower().split()
                    keywords.extend([word.strip('.,!?;:"()[]{}') for word in words if len(word) > 2])
        
        # Remove duplicates and store in refs
        if not self.refs:
            self.refs = default_refs()
        
        self.refs['keywords'] = list(set(keywords))[:50]  # Limit to 50 keywords
    
    def get_metadata_value(self, key_path):
        """Get a value from nested metadata using dot notation (e.g., 'history.created.dt')"""
        keys = key_path.split('.')
        value = self.metadata
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return None
    
    def set_metadata_value(self, key_path, value):
        """Set a value in nested metadata using dot notation"""
        keys = key_path.split('.')
        target = self.metadata
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        # Set the final value
        target[keys[-1]] = value
    
    def add_keyword(self, keyword):
        """Add a keyword to the refs.keywords list"""
        if not self.refs:
            self.refs = default_refs()
        
        if keyword.lower() not in [k.lower() for k in self.refs['keywords']]:
            self.refs['keywords'].append(keyword.lower())
    
    def add_tag(self, tag):
        """Add a tag to the refs.tags list"""
        if not self.refs:
            self.refs = default_refs()
        
        if tag not in self.refs['tags']:
            self.refs['tags'].append(tag)
    
    def get_created_timestamp(self):
        """Get creation timestamp in milliseconds (4D style)"""
        return self.get_metadata_value('history.created.dt') or 0
    
    def get_modified_timestamp(self):
        """Get modification timestamp in milliseconds (4D style)"""
        return self.get_metadata_value('history.modified.dt') or 0
    
    def __str__(self):
        """Default string representation"""
        if hasattr(self, 'name'):
            return str(self.name)
        elif hasattr(self, 'title'):
            return str(self.title)
        elif hasattr(self, 'email'):
            return str(self.email)
        else:
            return f"{self.__class__.__name__} #{self.pk}"