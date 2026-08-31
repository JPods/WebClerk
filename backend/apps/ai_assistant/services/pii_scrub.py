"""
PII Scrubber — strip personally identifiable information before WCHQ escalation.

Runs before any question leaves the local installation. Regex-based, no ML
dependencies. Patterns are deliberately conservative — better to over-scrub
than to leak a customer's SSN to an upstream server.

Usage:
    from apps.ai_assistant.services.pii_scrub import scrub_pii

    cleaned, count = scrub_pii("Email john@example.com or call 555-123-4567")
    # cleaned == "Email <email> or call <phone>"
    # count == 2
"""
import re

# ── Patterns (order matters — more specific patterns first) ─────────

# SSN: 123-45-6789 or 123 45 6789
_SSN_RE = re.compile(r'\b\d{3}[-\s]\d{2}[-\s]\d{4}\b')

# Credit card: 13-19 digits, optionally separated by spaces or dashes
_CARD_RE = re.compile(
    r'\b(?:\d[ -]*?){13,19}\b'
)

# Email
_EMAIL_RE = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
)

# US phone: (555) 123-4567, 555-123-4567, 555.123.4567, +1 555 123 4567,
# 5551234567 (10 digits)
_PHONE_RE = re.compile(
    r'(?:\+?1[-.\s]?)?'             # optional country code
    r'(?:\(\d{3}\)|\d{3})'          # area code
    r'[-.\s]?'
    r'\d{3}'                        # exchange
    r'[-.\s]?'
    r'\d{4}\b'                      # subscriber
)

# Street address: number + street name (e.g. "123 Main St", "4500 N Elm Avenue")
_ADDRESS_RE = re.compile(
    r'\b\d{1,6}\s+'                                       # house number
    r'(?:[NSEW]\.?\s+)?'                                  # optional direction
    r'[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3}\s+'       # street name words
    r'(?:St(?:reet)?|Ave(?:nue)?|Blvd|Boulevard|Dr(?:ive)?|Rd|Road|Ln|Lane'
    r'|Way|Ct|Court|Pl(?:ace)?|Cir(?:cle)?|Pkwy|Parkway|Ter(?:race)?)\b'
    r'\.?',
    re.IGNORECASE,
)

# Names preceded by common prefixes
_NAME_PREFIX_RE = re.compile(
    r'\b(?:customer|contact|client|user|Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Miss)\s+'
    r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})\b',
    re.IGNORECASE,
)


def scrub_pii(text: str) -> tuple[str, int]:
    """Scrub PII from text, returning (scrubbed_text, count_of_replacements).

    Applies patterns in specificity order so that an SSN is not partially
    matched as a phone number, etc.
    """
    count = 0

    def _replace(pattern, tag, s):
        nonlocal count
        matches = pattern.findall(s)
        count += len(matches)
        return pattern.sub(tag, s)

    # Order: SSN before phone (SSN is more specific digit pattern),
    # card before phone (longer digit runs), email, address, names last.
    text = _replace(_SSN_RE, '<ssn>', text)
    text = _replace(_CARD_RE, '<card>', text)
    text = _replace(_EMAIL_RE, '<email>', text)
    text = _replace(_PHONE_RE, '<phone>', text)
    text = _replace(_ADDRESS_RE, '<address>', text)

    # Names: replace the name portion, keep the prefix for readability
    name_matches = _NAME_PREFIX_RE.findall(text)
    count += len(name_matches)
    text = _NAME_PREFIX_RE.sub(
        lambda m: m.group(0).replace(m.group(1), '<name>'), text
    )

    return text, count
