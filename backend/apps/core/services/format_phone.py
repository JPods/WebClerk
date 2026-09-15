"""
core.services.phone_normalizer — Normalize and format phone numbers.

Storage: digits only with country code. "14055551234"
Display: formatted per nation. "(405) 555-1234" or "+27 11 555 1234"
Input:   accept anything, strip to digits, prepend country code if missing.

The user types whatever they want. We normalize on save and show
them the formatted result. After 3 entries they learn the pattern.
That's teaching without lecturing.

Usage:
    from apps.core.services.format_phone import normalize_phone, format_phone

    # On save — store digits only with country code
    normalized = normalize_phone("(405) 555-1234", default_country="US")
    # → "14055551234"

    # On display — format for reading
    formatted = format_phone("14055551234", display_mode="local", default_country="US")
    # → "405.555.1234"

    formatted = format_phone("14055551234", display_mode="international")
    # → "+1 405.555.1234"

    formatted = format_phone("27115551234", display_mode="local", default_country="US")
    # → "+27 11 555 1234"  (foreign number always shows country code)
"""
import re
from typing import Optional, Tuple

# Country code → (digit length without code, format pattern, code digits)
# Format: groups of digits separated by the display separator
COUNTRY_FORMATS = {
    "1":  {"length": 10, "groups": [3, 3, 4], "name": "US/CA"},        # 1 + 10 digits
    "44": {"length": 10, "groups": [2, 4, 4], "name": "UK"},           # 44 + 10 digits
    "27": {"length": 9,  "groups": [2, 3, 4], "name": "ZA"},           # 27 + 9 digits
    "33": {"length": 9,  "groups": [1, 2, 2, 2, 2], "name": "FR"},     # 33 + 9 digits
    "49": {"length": 10, "groups": [3, 3, 4], "name": "DE"},           # 49 + up to 11
    "61": {"length": 9,  "groups": [1, 4, 4], "name": "AU"},           # 61 + 9 digits
    "81": {"length": 10, "groups": [2, 4, 4], "name": "JP"},           # 81 + 10 digits
    "86": {"length": 11, "groups": [3, 4, 4], "name": "CN"},           # 86 + 11 digits
    "91": {"length": 10, "groups": [5, 5], "name": "IN"},              # 91 + 10 digits
    "52": {"length": 10, "groups": [2, 4, 4], "name": "MX"},           # 52 + 10 digits
    "55": {"length": 11, "groups": [2, 5, 4], "name": "BR"},           # 55 + 11 digits
    "971": {"length": 9, "groups": [2, 3, 4], "name": "AE"},           # 971 + 9 digits
    "972": {"length": 9, "groups": [2, 3, 4], "name": "IL"},           # 972 + 9 digits
}

# Map 2-letter country to calling code
COUNTRY_TO_CODE = {
    "US": "1", "CA": "1", "UK": "44", "GB": "44", "ZA": "27",
    "FR": "33", "DE": "49", "AU": "61", "JP": "81", "CN": "86",
    "IN": "91", "MX": "52", "BR": "55", "AE": "971", "IL": "972",
}


def _strip_to_digits(raw: str) -> str:
    """Remove everything except digits from a phone string."""
    return re.sub(r'\D', '', raw or '')


def _detect_country_code(digits: str) -> Tuple[str, str]:
    """
    Detect country code from leading digits.
    Returns (country_code, remaining_digits).
    Tries 3-digit codes first, then 2-digit, then 1-digit.
    """
    for length in (3, 2, 1):
        prefix = digits[:length]
        if prefix in COUNTRY_FORMATS:
            remaining = digits[length:]
            expected = COUNTRY_FORMATS[prefix]["length"]
            # Validate: remaining digits should be close to expected length
            if abs(len(remaining) - expected) <= 2:
                return prefix, remaining
    return "", digits


def normalize_phone(raw: str, default_country: str = "US") -> str:
    """
    Normalize any phone input to digits-only with country code.

    Accepts: "(405) 555-1234", "405.555.1234", "+1-405-555-1234",
             "405-555-1234", "4055551234", "+27 11 555 1234"

    Returns: "14055551234" (digits only, country code prepended)
    Returns empty string if input is not a valid phone number.
    """
    if not raw or not raw.strip():
        return ""

    # Handle + prefix (explicit country code)
    has_plus = raw.strip().startswith('+')

    digits = _strip_to_digits(raw)
    if len(digits) < 7:
        return ""  # too short to be a phone number

    if has_plus:
        # User provided explicit country code — trust it
        code, number = _detect_country_code(digits)
        if code:
            return code + number
        return digits  # couldn't parse but keep what we have

    # No + prefix — user didn't specify country code
    default_code = COUNTRY_TO_CODE.get(default_country.upper(), "1")
    expected_length = COUNTRY_FORMATS.get(default_code, {}).get("length", 10)

    # If the digit count matches the default country's expected length,
    # treat it as a local number — don't try to detect a country code
    # that happens to match the leading digits (e.g., 918... is US area code, not +91 India)
    if len(digits) == expected_length:
        return default_code + digits

    # If it's 11 digits starting with 1, it's a US number with country code
    if default_code == "1" and len(digits) == 11 and digits[0] == "1":
        return digits

    # For other lengths, try to detect country code
    code, number = _detect_country_code(digits)
    if code:
        return code + number

    # Fallback — prepend default code
    return default_code + digits


def format_phone(
    normalized: str,
    display_mode: str = "local",
    default_country: str = "US",
    separator: str = ".",
) -> str:
    """
    Format a normalized phone number for display.

    display_mode:
        "local" — hide country code when it matches default_country
        "international" — always show +country_code

    separator: "." or "-" or " "
    """
    if not normalized:
        return ""

    digits = _strip_to_digits(normalized)
    if len(digits) < 7:
        return normalized  # can't format, return as-is

    code, number = _detect_country_code(digits)
    if not code:
        return normalized  # can't parse

    fmt = COUNTRY_FORMATS.get(code)
    if not fmt:
        return f"+{code} {number}"

    # Group the number digits
    groups = fmt["groups"]
    parts = []
    pos = 0
    for g in groups:
        parts.append(number[pos:pos + g])
        pos += g
    if pos < len(number):
        parts.append(number[pos:])  # remainder

    formatted_number = separator.join(parts)

    # Determine if this is a foreign number
    default_code = COUNTRY_TO_CODE.get(default_country.upper(), "1")
    is_foreign = code != default_code

    if display_mode == "international" or is_foreign:
        return f"+{code} {formatted_number}"
    else:
        return formatted_number


def normalize_all_phones(default_country: str = "US", dry_run: bool = False):
    """
    Normalize all phone numbers in the contacts table.
    Stores original in config.phone_original if changed.

    Returns: {"total": N, "changed": N, "unchanged": N, "invalid": N}
    """
    from django.db import connection
    import json

    connection.ensure_connection()
    connection.connection.autocommit = True
    cur = connection.connection.cursor()

    cur.execute("""SELECT id, phone FROM contacts
        WHERE is_active = true AND is_deleted = false
        AND phone IS NOT NULL AND phone != ''""")

    total, changed, unchanged, invalid = 0, 0, 0, 0

    for cid, phone in cur.fetchall():
        total += 1
        normalized = normalize_phone(phone, default_country)

        if not normalized:
            invalid += 1
            if not dry_run:
                cur.execute("""UPDATE contacts SET
                    config = jsonb_set(COALESCE(config, '{}'::jsonb), '{phone_original}', %s::jsonb)
                    WHERE id = %s""", [json.dumps(phone), cid])
            continue

        if normalized == _strip_to_digits(phone):
            unchanged += 1
            continue

        changed += 1
        if not dry_run:
            cur.execute("""UPDATE contacts SET
                phone = %s,
                config = jsonb_set(COALESCE(config, '{}'::jsonb), '{phone_original}', %s::jsonb)
                WHERE id = %s""", [normalized, json.dumps(phone), cid])

    return {"total": total, "changed": changed, "unchanged": unchanged, "invalid": invalid}
