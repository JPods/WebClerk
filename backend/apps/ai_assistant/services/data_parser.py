"""
5C. Data Input Parsing — Clean and normalize addresses, phones, and vCards.

Deterministic libraries first (phonenumbers, usaddress, vobject), then
Ollama for fuzzy cases that rules can't handle.

Usage:
    from apps.ai_assistant.services.data_parser import DataParser

    parser = DataParser()
    result = parser.parse_address("123 Main St, Anytown, CA 90210")
    result = parser.parse_phone("+1 (555) 123-4567")
    result = parser.parse_vcard(vcard_string)
    result = parser.clean_address_record(address_id=42)
    report = parser.bulk_clean_addresses(limit=200)
"""
from __future__ import annotations

import logging
import re
from typing import Any

from django.utils import timezone

logger = logging.getLogger(__name__)


# ── Phone parsing (deterministic) ──────────────────────────────────────

def _parse_phone_deterministic(raw: str, default_region: str = "US") -> dict[str, Any]:
    """Parse a phone number using the phonenumbers library."""
    try:
        import phonenumbers
        parsed = phonenumbers.parse(raw, default_region)
        return {
            "valid": phonenumbers.is_valid_number(parsed),
            "e164": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
            "national": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
            "international": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            "country_code": parsed.country_code,
            "type": str(phonenumbers.number_type(parsed)),
            "confidence": 1.0,
            "method": "phonenumbers",
        }
    except ImportError:
        logger.warning("phonenumbers library not installed — using regex fallback")
        return _parse_phone_regex(raw)
    except Exception as e:
        logger.debug("phonenumbers parse failed for '%s': %s", raw, e)
        return {"valid": False, "raw": raw, "error": str(e), "confidence": 0.0, "method": "failed"}


def _parse_phone_regex(raw: str) -> dict[str, Any]:
    """Basic regex phone parser fallback."""
    digits = re.sub(r'\D', '', raw)
    if len(digits) == 10:
        formatted = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        return {
            "valid": True,
            "e164": f"+1{digits}",
            "national": formatted,
            "international": f"+1 {formatted}",
            "country_code": 1,
            "confidence": 0.7,
            "method": "regex",
        }
    elif len(digits) == 11 and digits[0] == "1":
        d = digits[1:]
        formatted = f"({d[:3]}) {d[3:6]}-{d[6:]}"
        return {
            "valid": True,
            "e164": f"+{digits}",
            "national": formatted,
            "international": f"+1 {formatted}",
            "country_code": 1,
            "confidence": 0.7,
            "method": "regex",
        }
    return {"valid": False, "raw": raw, "confidence": 0.0, "method": "regex"}


# ── Address parsing (deterministic) ────────────────────────────────────

def _parse_address_deterministic(raw: str) -> dict[str, Any]:
    """Parse an address string using usaddress library."""
    try:
        import usaddress
        tagged, addr_type = usaddress.tag(raw)

        # Map usaddress components to our Address model fields
        address1_parts = []
        for key in ("AddressNumber", "StreetNamePreDirectional", "StreetName",
                     "StreetNamePostType", "StreetNamePostDirectional"):
            if key in tagged:
                address1_parts.append(tagged[key])

        address2_parts = []
        for key in ("OccupancyType", "OccupancyIdentifier", "SubaddressIdentifier", "SubaddressType"):
            if key in tagged:
                address2_parts.append(tagged[key])

        return {
            "address1": " ".join(address1_parts),
            "address2": " ".join(address2_parts),
            "city": tagged.get("PlaceName", ""),
            "state": tagged.get("StateName", ""),
            "zip": tagged.get("ZipCode", ""),
            "country": tagged.get("CountryName", "US"),
            "confidence": 0.85,
            "method": "usaddress",
            "addr_type": addr_type,
        }
    except ImportError:
        logger.warning("usaddress library not installed — using regex fallback")
        return _parse_address_regex(raw)
    except Exception as e:
        logger.debug("usaddress parse failed for '%s': %s", raw, e)
        return _parse_address_regex(raw)


def _parse_address_regex(raw: str) -> dict[str, Any]:
    """Basic regex address parser fallback."""
    # Try common US format: 123 Main St, City, ST 12345
    pattern = re.compile(
        r'(?P<address1>.+?),\s*'
        r'(?P<city>[A-Za-z\s]+),\s*'
        r'(?P<state>[A-Z]{2})\s*'
        r'(?P<zip>\d{5}(?:-\d{4})?)',
        re.IGNORECASE
    )
    match = pattern.match(raw.strip())
    if match:
        return {
            "address1": match.group("address1").strip(),
            "address2": "",
            "city": match.group("city").strip(),
            "state": match.group("state").upper(),
            "zip": match.group("zip"),
            "country": "US",
            "confidence": 0.6,
            "method": "regex",
        }
    return {"raw": raw, "confidence": 0.0, "method": "regex_failed"}


# ── vCard parsing ──────────────────────────────────────────────────────

def _parse_vcard(vcard_text: str) -> dict[str, Any]:
    """Parse a vCard string into structured contact data."""
    try:
        import vobject
        vcard = vobject.readOne(vcard_text)
        result: dict[str, Any] = {"method": "vobject", "confidence": 0.9}

        # Name
        if hasattr(vcard, "fn"):
            result["name"] = vcard.fn.value
        if hasattr(vcard, "n"):
            n = vcard.n.value
            result["first_name"] = n.given or ""
            result["last_name"] = n.family or ""

        # Organization
        if hasattr(vcard, "org"):
            result["organization"] = vcard.org.value[0] if vcard.org.value else ""

        # Emails
        emails = []
        for email in vcard.contents.get("email", []):
            emails.append({
                "address": email.value,
                "type": email.params.get("TYPE", ["work"])[0] if email.params else "work",
            })
        result["emails"] = emails

        # Phones
        phones = []
        for tel in vcard.contents.get("tel", []):
            phones.append({
                "number": tel.value,
                "type": tel.params.get("TYPE", ["work"])[0] if tel.params else "work",
            })
        result["phones"] = phones

        # Addresses
        addresses = []
        for adr in vcard.contents.get("adr", []):
            addr = adr.value
            addresses.append({
                "address1": addr.street or "",
                "city": addr.city or "",
                "state": addr.region or "",
                "zip": addr.code or "",
                "country": addr.country or "",
                "type": adr.params.get("TYPE", ["work"])[0] if adr.params else "work",
            })
        result["addresses"] = addresses

        # Title
        if hasattr(vcard, "title"):
            result["title"] = vcard.title.value

        # URL
        if hasattr(vcard, "url"):
            result["url"] = vcard.url.value

        return result

    except ImportError:
        logger.warning("vobject library not installed — vCard parsing unavailable")
        return {"error": "vobject not installed", "raw": vcard_text, "confidence": 0.0}
    except Exception as e:
        logger.debug("vCard parse failed: %s", e)
        return {"error": str(e), "raw": vcard_text, "confidence": 0.0}


class DataParser:
    """Unified data parsing service with deterministic + LLM fallback."""

    def __init__(self, use_llm: bool = True, confidence_threshold: float = 0.5):
        self.use_llm = use_llm
        self.confidence_threshold = confidence_threshold
        self._client = None

    def _get_client(self):
        if self._client is None and self.use_llm:
            from apps.ai_assistant.services.ollama_client import OllamaClient
            self._client = OllamaClient()
        return self._client

    # ── Public API ─────────────────────────────────────────────────────

    def parse_phone(self, raw: str, region: str = "US") -> dict[str, Any]:
        """Parse a phone number, falling back to LLM for fuzzy inputs."""
        result = _parse_phone_deterministic(raw, region)
        if result.get("confidence", 0) >= self.confidence_threshold:
            return result

        # LLM fallback
        if self.use_llm:
            return self._llm_parse_phone(raw, result)
        return result

    def parse_address(self, raw: str) -> dict[str, Any]:
        """Parse an address string, falling back to LLM for unusual formats."""
        result = _parse_address_deterministic(raw)
        if result.get("confidence", 0) >= self.confidence_threshold:
            return result

        if self.use_llm:
            return self._llm_parse_address(raw, result)
        return result

    def parse_vcard(self, vcard_text: str) -> dict[str, Any]:
        """Parse a vCard string into structured contact data."""
        return _parse_vcard(vcard_text)

    # ── LLM fallbacks ─────────────────────────────────────────────────

    def _llm_parse_phone(self, raw: str, failed_result: dict) -> dict[str, Any]:
        """Use Ollama to interpret a messy phone number."""
        client = self._get_client()
        if not client:
            return failed_result

        try:
            prompt = (
                f"Extract a phone number from this text and return ONLY a JSON object "
                f"with keys: country_code (int), national (string), e164 (string).\n"
                f"Text: {raw}\n"
                f"JSON:"
            )
            response = client.generate(prompt, mode="general")
            import json
            # Try to extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "valid": True,
                    "e164": data.get("e164", ""),
                    "national": data.get("national", ""),
                    "country_code": data.get("country_code", 1),
                    "confidence": 0.5,
                    "method": "llm",
                }
        except Exception as e:
            logger.debug("LLM phone parse failed: %s", e)

        return failed_result

    def _llm_parse_address(self, raw: str, failed_result: dict) -> dict[str, Any]:
        """Use Ollama to interpret a messy/international address."""
        client = self._get_client()
        if not client:
            return failed_result

        try:
            prompt = (
                f"Parse this address into structured components. Return ONLY a JSON object "
                f"with keys: address1, address2, city, state, zip, country.\n"
                f"Address: {raw}\n"
                f"JSON:"
            )
            response = client.generate(prompt, mode="general")
            import json
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "address1": data.get("address1", ""),
                    "address2": data.get("address2", ""),
                    "city": data.get("city", ""),
                    "state": data.get("state", ""),
                    "zip": data.get("zip", ""),
                    "country": data.get("country", "US"),
                    "confidence": 0.5,
                    "method": "llm",
                }
        except Exception as e:
            logger.debug("LLM address parse failed: %s", e)

        return failed_result

    # ── Bulk operations on existing records ────────────────────────────

    def clean_address_record(self, address_id: int) -> dict[str, Any]:
        """Clean and normalize a single Address record."""
        from apps.communications.models.address import Address

        try:
            addr = Address.objects.get(pk=address_id)
        except Address.DoesNotExist:
            return {"error": f"Address {address_id} not found"}

        changes = {}

        # Normalize state to uppercase 2-letter
        if addr.state and len(addr.state) == 2:
            upper = addr.state.upper()
            if upper != addr.state:
                changes["state"] = upper

        # Strip whitespace from all text fields
        for field in ("address1", "address2", "city", "state", "zip", "country"):
            val = getattr(addr, field, "")
            if val and val != val.strip():
                changes[field] = val.strip()

        # Normalize zip to 5 or 5-4 format
        if addr.zip:
            digits = re.sub(r'\D', '', addr.zip)
            if len(digits) == 5:
                normalized = digits
            elif len(digits) == 9:
                normalized = f"{digits[:5]}-{digits[5:]}"
            else:
                normalized = addr.zip.strip()
            if normalized != addr.zip:
                changes["zip"] = normalized

        # Rebuild full address string
        parts = [p for p in (addr.address1, addr.address2) if p]
        city_state_zip = ", ".join(p for p in (addr.city, f"{addr.state} {addr.zip}".strip()) if p)
        if city_state_zip:
            parts.append(city_state_zip)
        full = ", ".join(parts)
        if full != addr.full:
            changes["full"] = full

        if changes:
            Address.objects.filter(pk=address_id).update(**changes)

        return {
            "address_id": address_id,
            "changes": changes,
            "cleaned": bool(changes),
        }

    def bulk_clean_addresses(self, limit: int = 500) -> dict[str, Any]:
        """Clean all Address records, returning a summary."""
        from apps.communications.models.address import Address

        cleaned = 0
        processed = 0
        errors = 0

        qs = Address.objects.filter(is_active=True).order_by("pk")[:limit]
        for addr in qs.iterator(chunk_size=200):
            processed += 1
            try:
                result = self.clean_address_record(addr.pk)
                if result.get("cleaned"):
                    cleaned += 1
            except Exception as e:
                logger.debug("Failed to clean address %s: %s", addr.pk, e)
                errors += 1

        return {
            "processed": processed,
            "cleaned": cleaned,
            "errors": errors,
        }

    def bulk_clean_phones(self, limit: int = 500) -> dict[str, Any]:
        """Normalize phone numbers across Phone records."""
        processed = 0
        cleaned = 0
        errors = 0

        try:
            from apps.communications.models.phone import Phone
        except ImportError:
            return {"error": "Phone model not found"}

        qs = Phone.objects.filter(is_active=True).order_by("pk")[:limit]
        for phone in qs.iterator(chunk_size=200):
            processed += 1
            raw = getattr(phone, "number", "") or getattr(phone, "phone", "") or ""
            if not raw:
                continue

            try:
                result = self.parse_phone(raw)
                if result.get("valid") and result.get("e164"):
                    # Update if different
                    current = getattr(phone, "number", "") or getattr(phone, "phone", "")
                    if result["e164"] != current:
                        Phone.objects.filter(pk=phone.pk).update(
                            **{("number" if hasattr(phone, "number") else "phone"): result["e164"]}
                        )
                        cleaned += 1
            except Exception as e:
                logger.debug("Failed to clean phone %s: %s", phone.pk, e)
                errors += 1

        return {
            "processed": processed,
            "cleaned": cleaned,
            "errors": errors,
        }

    # ── Report ─────────────────────────────────────────────────────────

    def generate_report(self, address_result: dict, phone_result: dict) -> str:
        """Generate a markdown report of data cleaning results."""
        lines = [
            "# Data Parsing & Cleanup Report",
            f"Generated: {timezone.now():%Y-%m-%d %H:%M}",
            "",
            "## Addresses",
            f"- Processed: {address_result.get('processed', 0)}",
            f"- Cleaned: {address_result.get('cleaned', 0)}",
            f"- Errors: {address_result.get('errors', 0)}",
            "",
            "## Phones",
            f"- Processed: {phone_result.get('processed', 0)}",
            f"- Cleaned: {phone_result.get('cleaned', 0)}",
            f"- Errors: {phone_result.get('errors', 0)}",
            "",
        ]
        return "\n".join(lines)
