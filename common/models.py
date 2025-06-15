from django.db import models
from django.db.models import JSONField
from django.utils import timezone
from .ignore_fields import IGNORE_FIELDS
from .ignore_keywords import IGNORE_KEYWORDS

def default_metadata():
    return {
        "security": None,
        "publish": None,
        "priority": None,
        "version": "1.0",
        "access": {"view": [], "edit": []},
        "approvals": [],
        "health": {
            "dtCreated": int(timezone.now().timestamp() * 1000),
            "dtUpdated": None,
            "dtCompleted": None,
            "dtExpire": None,
            "dtRetired": None,
            "dtLastSync": None,
        },
        "history": {
            "created": None,
            "modified": None,
            "active": None,
            "expire": None,
            "retired": None,
            "lastUsed": None,
            "sync": None,
        },
        "profiles": [],
        "undefined": {},
    }

def default_refs():
    return {
        "keywords": "",
        "tags": "",
        "links": [],
    }

def default_prefs():
    return {}

class BaseModel(models.Model):
    refs = JSONField(default=default_refs, null=True, blank=True)
    prefs = JSONField(default=default_prefs, null=True, blank=True)
    metadata = JSONField(default=default_metadata, null=True, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Capture undefined fields from kwargs or instance attributes
        undefined_fields = {}
        defined_fields = {field.name for field in self._meta.fields}

        # Check kwargs for undefined fields
        if kwargs.get('force_insert') or kwargs.get('force_update'):
            for key, value in kwargs.items():
                if key not in defined_fields and key not in ('force_insert', 'force_update', 'using'):
                    undefined_fields[key] = value

        # Check instance attributes
        for key, value in vars(self).items():
            if key.startswith('_') or key in defined_fields:
                continue
            if key in ('id', 'pk'):
                continue
            undefined_fields[key] = value

        # Update metadata with undefined fields
        if undefined_fields:
            self.metadata = self.metadata or default_metadata()
            self.metadata["undefined"].update(undefined_fields)

        # Generate model-specific metadata
        self.update_metadata()
        super().save(*args, **kwargs)

    def update_metadata(self):
        """Update metadata with model-specific data."""
        if not self.metadata:
            self.metadata = default_metadata()

        # Generate keywords
        keywords = self.generate_keywords()
        self.refs = self.refs or default_refs()
        self.refs["keywords"] = keywords

        # Update health timestamps
        self.metadata["health"]["dtUpdated"] = int(timezone.now().timestamp() * 1000)
        if not self.metadata["health"]["dtCreated"]:
            self.metadata["health"]["dtCreated"] = int(timezone.now().timestamp() * 1000)

        # Set metadata.undefined from model-specific data
        self.metadata["undefined"] = self.set_undefined()

    def generate_keywords(self):
        """Generate comma-separated keywords from all base and subclass fields, splitting by spaces and trimming."""
        keywords = []
        model_name = self.__class__.__name__.lower()
        keywords.append(model_name)

        # Get all fields from base and subclass
        for field in self._meta.get_fields():
            if field.name in IGNORE_FIELDS:
                continue
            # Skip many-to-many fields if instance is not saved (no id)
            if isinstance(field, models.ManyToManyField) and self.id is None:
                continue
            try:
                value = getattr(self, field.name, None)
            except ValueError:
                continue  # Skip fields that can't be accessed
            if value is None:
                continue
            if isinstance(value, (str)):
                # Split string by spaces, trim, filter ignored keywords
                parts = [part.strip().lower() for part in value.split() if part.strip()]
                filtered_parts = [part for part in parts if part not in IGNORE_KEYWORDS]
                keywords.extend(filtered_parts)
            elif isinstance(value, (int, float)):
                keyword = str(value).lower()
                if keyword not in IGNORE_KEYWORDS:
                    keywords.append(keyword)
            elif isinstance(value, (list, tuple)):
                # Handle arrays (e.g., Contact.role)
                for item in value:
                    if isinstance(item, (str)):
                        parts = [part.strip().lower() for part in item.split() if part.strip()]
                        filtered_parts = [part for part in parts if part not in IGNORE_KEYWORDS]
                        keywords.extend(filtered_parts)
                    elif isinstance(item, (int, float)):
                        keyword = str(item).lower()
                        if keyword not in IGNORE_KEYWORDS:
                            keywords.append(keyword)
            elif isinstance(value, dict):
                # Extract string/number values from JSON fields
                for v in value.values():
                    if isinstance(v, (str)):
                        parts = [part.strip().lower() for part in v.split() if part.strip()]
                        filtered_parts = [part for part in parts if part not in IGNORE_KEYWORDS]
                        keywords.extend(filtered_parts)
                    elif isinstance(v, (int, float)):
                        keyword = str(v).lower()
                        if keyword not in IGNORE_KEYWORDS:
                            keywords.append(keyword)
            
        # Append tags from refs if they exist
        if hasattr(self, 'refs') and isinstance(self.refs, dict) and 'tags' in self.refs:
            tags = self.refs.get('tags', [])
            if isinstance(tags, (list, tuple)):
                for tag in tags:
                    if isinstance(tag, str):
                        # Split tag by spaces, trim, lowercase, filter
                        parts = [part.strip().lower() for part in tag.split() if part.strip()]
                        filtered_parts = [part for part in parts if part not in IGNORE_KEYWORDS]
                        keywords.extend(filtered_parts)

        return ",".join(set(keywords))

    def set_undefined(self):
        """Return dictionary to set metadata.undefined (override in subclasses)."""
        return {}