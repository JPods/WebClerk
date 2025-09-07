# path: apps/communications/models/location.py
from django.db import models
from common.models import BaseModel
from django.utils import timezone
import uuid
from typing import Any, Dict, Optional

class Location(BaseModel):
    address1 = models.CharField(max_length=255, blank=True)
    address2 = models.CharField(max_length=255, blank=True)
    address_type = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=255, blank=True)
    instructions = models.TextField(blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    state = models.CharField(max_length=255, blank=True)
    zip = models.CharField(max_length=255, blank=True)
    full = models.CharField(max_length=255, blank=True)
    

    # all metadata changes occur in common.models.BaseModel


    class Meta:
        db_table = 'locations'
        
    def __str__(self):
        return f"{self.address1}, {self.city}, {self.state}"
    
    # --- Validation / cleanup stubs ----------------------------------------
    def queue_verification(self, provider: str = "osm") -> None:
        """Enqueue an asynchronous address verification task.

        Provider 'osm' is a placeholder for OpenStreetMap/Nominatim. The task is a stub
        (no network call by default) that records intent and sets metadata flags.
        """
        try:
            if provider == "osm":
                # Lazy import to avoid circulars at import time
                from apps.communications.tasks import validate_location_osm
                validate_location_osm.delay(self.pk)
        except Exception:
            # Non-fatal; callers may choose to log
            pass

    def apply_validation_result(self, result: Dict[str, Any]) -> None:
        """Apply a verification result payload to metadata/fields.

        Expected result keys (flexible, all optional):
          - provider: str (e.g., 'osm')
          - status: str (e.g., 'ok', 'not_found', 'stubbed')
          - match_score: int 0-100
          - latitude, longitude: floats
          - normalized: dict with cleaned fields
        """
        meta = self.metadata or {}
        ver = meta.setdefault("versioning", {}).setdefault("validation", {})
        if "provider" in result:
            ver["provider"] = result["provider"]
        if "status" in result:
            ver["status"] = result["status"]
        if "match_score" in result:
            try:
                ver["match_score"] = int(result["match_score"])  # best-effort cast
            except Exception:
                ver["match_score"] = 0
        # mirror verified timestamp in metadata.history.verified.dt for universal access
        hist = meta.setdefault("history", {})
        hist["verified"] = {"dt": int(timezone.now().timestamp() * 1000), "contact_id": 0}

        # Optionally update lat/long and normalized text if provided
        updated_fields = ["metadata"]
        if isinstance(result.get("latitude"), (int, float)):
            self.latitude = float(result["latitude"])  # type: ignore[assignment]
            updated_fields.append("latitude")
        if isinstance(result.get("longitude"), (int, float)):
            self.longitude = float(result["longitude"])  # type: ignore[assignment]
            updated_fields.append("longitude")
        normalized = result.get("normalized")
        if isinstance(normalized, dict):
            for key in ("address1", "address2", "city", "state", "zip", "country", "full"):
                if key in normalized and isinstance(normalized[key], str):
                    setattr(self, key, normalized[key])
                    if key not in updated_fields:
                        updated_fields.append(key)
        self.metadata = meta
        try:
            self.save(update_fields=updated_fields + ["dt_modified", "version"])  # type: ignore[list-item]
        except Exception:
            self.save()

    def clear_submission_snapshot(self, keep_copy_in_versioning: bool = False) -> None:
        """Clear prefs.submission.as_submitted after verification; optionally archive in metadata.versioning."""
        prefs = getattr(self, 'prefs', {}) or {}
        as_sub = prefs.get('submission', {}).get('as_submitted')
        if keep_copy_in_versioning and as_sub:
            meta = self.metadata or {}
            ver = meta.setdefault('versioning', {})
            ver['submission_archived'] = as_sub
            self.metadata = meta
        # remove snapshot
        if 'submission' in prefs and isinstance(prefs['submission'], dict):
            prefs['submission'].pop('as_submitted', None)
        self.prefs = prefs
        self.save(update_fields=['prefs', 'metadata', 'dt_modified'])
