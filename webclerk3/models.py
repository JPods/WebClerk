from django.db import models
import uuid
from django.utils import timezone

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

class BaseModel(models.Model):
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    metadata = models.JSONField(default=default_metadata)
    refs = models.JSONField(default=default_refs)
    prefs = models.JSONField(default=default_prefs)

    class Meta:
        abstract = True