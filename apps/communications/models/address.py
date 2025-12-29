from django.db import models
from common.models import BaseModel
from django.utils import timezone
import uuid
from typing import Any, Dict, Optional

class Address(BaseModel):
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
    full = models.CharField(max_length=1000, blank=True)

    # all metadata changes occur in common.models.BaseModel

    class Meta:
        # keep the existing table name to avoid extra DB churn during rename
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
                validate_location_osm(self.pk)
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
        meta: Dict[str, Any] = dict(self.metadata or {})
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
            meta: Dict[str, Any] = dict(self.metadata or {})
            ver = meta.setdefault('versioning', {})
            ver['submission_archived'] = as_sub
            self.metadata = meta
        # remove snapshot
        if 'submission' in prefs and isinstance(prefs['submission'], dict):
            prefs['submission'].pop('as_submitted', None)
        self.prefs = prefs
        self.save(update_fields=['prefs', 'metadata', 'dt_modified'])

    # --- Compact display metadata ---------------------------------------
    def _compute_display_location(self) -> Dict[str, Any]:
        """Return a small dict suitable for metadata.display.* storage.

        Keeps it concise: {'full_location': str, 'standard': 'us'|'eu', 'country_code': 'US'|..}
        """
        data = self.as_standard('auto')
        return {
            'full_location': data.get('full', ''),
            'standard': data.get('standard', 'auto'),
            'country_code': data.get('country_code', ''),
        }

    def _refresh_display_metadata(self) -> None:
        try:
            meta: Dict[str, Any] = dict(self.metadata or {})
            display = meta.setdefault('display', {})
            display.update(self._compute_display_location())
            self.metadata = meta
        except Exception:
            # Never block save due to formatting issues
            pass

    def save(self, *args, **kwargs):  # type: ignore[override]
        # Auto-populate full field from address components
        self.full = self.format_auto()
        # Persist computed display bits prior to saving
        self._refresh_display_metadata()
        return super().save(*args, **kwargs)

    # --- Standard formatting helpers (US/EU generic) ----------------------
    # Note: Python stdlib doesn’t include postal address formatters.
    # These helpers provide lightweight, conventional formats without deps.
    # For advanced i18n, consider: libpostal (py-libpostal) or Babel+i18naddress.

    _COUNTRY_NORMALIZE = {
        'UNITED STATES': ('US', 'United States'), 'USA': ('US', 'United States'), 'US': ('US', 'United States'),
        'UNITED KINGDOM': ('GB', 'United Kingdom'), 'UK': ('GB', 'United Kingdom'), 'GB': ('GB', 'United Kingdom'),
        'GERMANY': ('DE', 'Germany'), 'DE': ('DE', 'Germany'),
        'FRANCE': ('FR', 'France'), 'FR': ('FR', 'France'),
        'CANADA': ('CA', 'Canada'), 'CA': ('CA', 'Canada'),
    }

    def _norm_str(self, v: Optional[str]) -> str:
        return (v or '').strip()

    def _country_norm(self) -> tuple[str, str]:
        raw = self._norm_str(getattr(self, 'country', ''))
        key = raw.upper()
        return self._COUNTRY_NORMALIZE.get(key, (raw[:2].upper() if raw else '', raw or ''))

    def parts(self) -> Dict[str, str]:
        """Return sanitized address parts."""
        return {
            'address1': self._norm_str(getattr(self, 'address1', '')),
            'address2': self._norm_str(getattr(self, 'address2', '')),
            'city': self._norm_str(getattr(self, 'city', '')),
            'state': self._norm_str(getattr(self, 'state', '')),
            'zip': self._norm_str(getattr(self, 'zip', '')),
            'country': self._norm_str(getattr(self, 'country', '')),
        }

    # Generic EU-ish single-line (postal code before city), minimal heuristic
    def full_eu(self, include_country: bool = False) -> str:
        p = self.parts()
        segments: list[str] = []
        if p['address1']:
            segments.append(p['address1'])
        if p['address2']:
            segments.append(p['address2'])
        town = ' '.join(s for s in [p['zip'], p['city']] if s)
        region = p['state']
        if town:
            segments.append(town)
        if region:
            segments.append(region)
        if include_country and p['country']:
            segments.append(p['country'])
        return ', '.join([s for s in segments if s])

    # US single-line (City, ST ZIP)
    def full_us(self, include_country: bool = False) -> str:
        p = self.parts()
        line1 = p['address1']
        line2 = p['address2']
        city_state_zip = ' '.join(s for s in [f"{p['city']}," if p['city'] else '', p['state'], p['zip']] if s)
        segments = [line1]
        if line2:
            segments.append(line2)
        if city_state_zip:
            segments.append(city_state_zip)
        if include_country and p['country']:
            segments.append(p['country'])
        return ', '.join([s for s in segments if s])

    def lines_us(self, include_country: bool = False) -> list[str]:
        p = self.parts()
        lines: list[str] = []
        if p['address1']:
            lines.append(p['address1'])
        if p['address2']:
            lines.append(p['address2'])
        city_line = ' '.join(s for s in [f"{p['city']}," if p['city'] else '', p['state'], p['zip']] if s)
        if city_line:
            lines.append(city_line)
        if include_country and p['country']:
            lines.append(p['country'])
        return lines

    def lines_eu(self, include_country: bool = False) -> list[str]:
        p = self.parts()
        lines: list[str] = []
        if p['address1']:
            lines.append(p['address1'])
        if p['address2']:
            lines.append(p['address2'])
        town = ' '.join(s for s in [p['zip'], p['city']] if s)
        if town:
            lines.append(town)
        if p['state']:
            lines.append(p['state'])
        if include_country and p['country']:
            lines.append(p['country'])
        return lines

    def format_auto(self, include_country_if_foreign: bool = True) -> str:
        code, _ = self._country_norm()
        include_country = include_country_if_foreign and code not in ('', 'US')
        if code == 'US':
            return self.full_us(include_country=include_country)
        return self.full_eu(include_country=include_country)

    def as_standard(self, standard: str = 'auto') -> Dict[str, Any]:
        """Return a standard dictionary for common uses.

        standard: 'auto'|'us'|'eu'. Includes:
          - standard, country_code, country
          - parts: normalized components
          - lines: array form
          - full: single-line label
        """
        code, name = self._country_norm()
        p = self.parts()
        std = standard.lower() if isinstance(standard, str) else 'auto'
        if std == 'auto':
            std = 'us' if code == 'US' else 'eu'
        if std == 'us':
            lines = self.lines_us(include_country=False)
            full = self.full_us(include_country=False)
        else:
            lines = self.lines_eu(include_country=False)
            full = self.full_eu(include_country=False)
        return {
            'standard': std,
            'country_code': code,
            'country': name or p['country'],
            'parts': p,
            'lines': lines,
            'full': full,
        }

