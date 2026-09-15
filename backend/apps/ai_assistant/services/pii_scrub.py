"""
PII Parser — detect personally identifiable information with two-layer approach.

Layer 1: Structural patterns (regex) — emails, phones, SSNs, addresses, names.
Layer 2: Database lookup — match against known contacts, phones, addresses.

Returns candidates for user review. Each user correction becomes a Small-Sting
that Alice learns from. Over time, installation-specific PII recognition improves.

Usage:
    from apps.ai_assistant.services.pii_scrub import scrub_pii, parse_pii

    # Auto-scrub (backwards compatible)
    cleaned, count = scrub_pii("Email john@example.com or call 555-123-4567")

    # Parse for review (new)
    candidates = parse_pii("Call Bill James at 612-555-1234")
    # [{'start': 5, 'end': 15, 'text': 'Bill James', 'type': 'name',
    #   'confidence': 0.9, 'tag': '<name>', 'source': 'database'}, ...]
"""
import logging
import re
import time
from typing import Any

logger = logging.getLogger('pii_scrub')

# ── Layer 1: Structural Patterns ─────────────────────────────────────

# SSN: 123-45-6789 or 123 45 6789
_SSN_RE = re.compile(r'\b\d{3}[-\s]\d{2}[-\s]\d{4}\b')

# Credit card: 13-19 digits, optionally separated by spaces or dashes
_CARD_RE = re.compile(r'\b(?:\d[ -]*?){13,19}\b')

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

# Street address: number + street name + suffix
_ADDRESS_RE = re.compile(
    r'\b\d{1,6}\s+'
    r'(?:[NSEW]\.?\s+)?'
    r'[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3}\s+'
    r'(?:St(?:reet)?|Ave(?:nue)?|Blvd|Boulevard|Dr(?:ive)?|Rd|Road|Ln|Lane'
    r'|Way|Ct|Court|Pl(?:ace)?|Cir(?:cle)?|Pkwy|Parkway|Ter(?:race)?)\b'
    r'\.?',
    re.IGNORECASE,
)

# Zip codes (US 5 or 5+4)
_ZIP_RE = re.compile(r'\b\d{5}(?:-\d{4})?\b')

# Names preceded by common prefixes (original pattern, kept as high-confidence)
# Prefix match is case-insensitive, but the name capture requires initial uppercase
# to avoid grabbing common words like "about" or "the" as name parts.
_NAME_PREFIX_RE = re.compile(
    r'\b(?:[Cc]ustomer|[Cc]ontact|[Cc]lient|[Uu]ser|Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Miss)\s+'
    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b',
)

# Structural patterns with their types and tags
_PATTERNS = [
    (_SSN_RE, 'ssn', '<ssn>', 0.95),
    (_CARD_RE, 'card', '<card>', 0.90),
    (_EMAIL_RE, 'email', '<email>', 0.95),
    (_PHONE_RE, 'phone', '<phone>', 0.85),
    (_ADDRESS_RE, 'address', '<address>', 0.80),
]


# ── Layer 2: Database Vocabulary Cache ───────────────────────────────

_vocab_cache: dict[str, Any] | None = None
_vocab_cache_time: float = 0
_VOCAB_TTL = 300  # 5 minutes

# Common words that look like names but aren't — prevents false positives
_COMMON_WORDS = frozenset({
    'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
    'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his',
    'how', 'its', 'may', 'new', 'now', 'old', 'see', 'way', 'who', 'did',
    'let', 'say', 'she', 'too', 'use', 'set', 'run', 'add', 'put',
    'also', 'back', 'been', 'call', 'come', 'each', 'find', 'from',
    'give', 'good', 'have', 'help', 'here', 'high', 'home', 'just',
    'keep', 'know', 'last', 'long', 'look', 'made', 'make', 'many',
    'more', 'most', 'much', 'must', 'name', 'need', 'next', 'only',
    'open', 'over', 'part', 'same', 'show', 'side', 'some', 'such',
    'take', 'tell', 'than', 'that', 'them', 'then', 'they', 'this',
    'time', 'turn', 'used', 'very', 'want', 'well', 'went', 'what',
    'when', 'will', 'with', 'work', 'year', 'your',
    'about', 'after', 'again', 'being', 'below', 'between', 'both',
    'could', 'every', 'first', 'found', 'great', 'house', 'large',
    'never', 'other', 'place', 'point', 'right', 'small', 'still',
    'think', 'those', 'three', 'under', 'water', 'where', 'which',
    'world', 'would', 'write', 'check', 'order', 'total', 'price',
    'field', 'value', 'model', 'table', 'query', 'admin', 'panel',
    'report', 'action', 'status', 'active', 'system', 'record',
    'setting', 'invoice', 'payment', 'contact', 'customer', 'vendor',
    'product', 'service', 'account', 'journal', 'balance', 'credit',
    'amount', 'method', 'source', 'target', 'config', 'layout',
    'search', 'filter', 'column', 'detail', 'browse', 'export',
    'import', 'bundle', 'delete', 'create', 'update', 'select',
    'error', 'warning', 'success', 'pending', 'released',
    # WC3-specific terms that could be names
    'alice', 'baker', 'chase', 'delta', 'fisher', 'grant', 'hunter',
    'mason', 'parker', 'taylor', 'walker', 'young',
})


def _build_contact_vocab() -> dict[str, Any]:
    """Build vocabulary of known PII values from the contact database.

    Returns dict with sets of known values by type:
        {
            'names_first': {'bill', 'john', ...},
            'names_last': {'james', 'smith', ...},
            'full_names': {'bill james', 'john smith', ...},
            'emails': {'bill@example.com', ...},
            'phones': {'6125551234', ...},
            'phone_prefixes': {'612', '651', ...},
            'companies': {'acme corp', ...},
            'cities': {'minneapolis', ...},
            'zips': {'55401', ...},
            'addresses': {'123 main st', ...},
        }
    """
    global _vocab_cache, _vocab_cache_time

    now = time.time()
    if _vocab_cache and (now - _vocab_cache_time) < _VOCAB_TTL:
        return _vocab_cache

    vocab: dict[str, set[str]] = {
        'names_first': set(),
        'names_last': set(),
        'full_names': set(),
        'emails': set(),
        'phones': set(),
        'phone_prefixes': set(),
        'companies': set(),
        'cities': set(),
        'zips': set(),
        'addresses': set(),
    }

    try:
        from apps.core.models.contact import Contact
        contacts = Contact.objects.filter(
            is_active=True,
        ).values_list(
            'name_first', 'name_last', 'email', 'company',
        ).iterator(chunk_size=500)

        for first, last, email, company in contacts:
            if first and len(first) > 1:
                vocab['names_first'].add(first.lower())
            if last and len(last) > 1:
                vocab['names_last'].add(last.lower())
            if first and last:
                vocab['full_names'].add(f'{first} {last}'.lower())
            if email:
                vocab['emails'].add(email.lower())
            if company and len(company) > 2:
                vocab['companies'].add(company.lower())
    except Exception:
        logger.debug('Contact query failed for PII vocab', exc_info=True)

    try:
        from apps.communications.models.phone import Phone
        phones = Phone.objects.exclude(
            number='',
        ).values_list('number', flat=True).iterator(chunk_size=500)

        for number in phones:
            if number:
                digits = re.sub(r'\D', '', number)
                if len(digits) >= 7:
                    vocab['phones'].add(digits)
                    if len(digits) >= 10:
                        # area code as prefix
                        vocab['phone_prefixes'].add(digits[:3])
    except Exception:
        logger.debug('Phone query failed for PII vocab', exc_info=True)

    try:
        from apps.communications.models.address import Address
        addresses = Address.objects.exclude(
            address1='',
        ).values_list(
            'address1', 'city', 'zip',
        ).iterator(chunk_size=500)

        for addr1, city, zip_code in addresses:
            if addr1 and len(addr1) > 5:
                vocab['addresses'].add(addr1.lower())
            if city and len(city) > 2:
                vocab['cities'].add(city.lower())
            if zip_code and len(zip_code) >= 5:
                vocab['zips'].add(zip_code[:5])
    except Exception:
        logger.debug('Address query failed for PII vocab', exc_info=True)

    # Load learned corrections from Alice observations
    try:
        from apps.ai_assistant.models.alice import AliceObservation
        corrections = AliceObservation.objects.filter(
            category='pii_correction',
            resolved=False,
        ).values_list('config', flat=True).iterator()

        for config in corrections:
            if not isinstance(config, dict):
                continue
            action = config.get('action')
            text = (config.get('text', '') or '').lower()
            pii_type = config.get('pii_type', '')
            if action == 'confirmed' and text:
                # User confirmed this IS PII — add to vocab
                if pii_type == 'name' and ' ' in text:
                    vocab['full_names'].add(text)
                elif pii_type == 'name':
                    vocab['names_last'].add(text)
            # 'rejected' corrections are handled in _is_known_false_positive
    except Exception:
        logger.debug('Alice corrections query failed', exc_info=True)

    _vocab_cache = vocab
    _vocab_cache_time = now
    return vocab


def invalidate_vocab_cache():
    """Force vocab rebuild on next parse. Call after contact changes."""
    global _vocab_cache, _vocab_cache_time
    _vocab_cache = None
    _vocab_cache_time = 0


def _is_known_false_positive(text: str, pii_type: str) -> bool:
    """Check if Alice has learned this is NOT PII."""
    try:
        from apps.ai_assistant.models.alice import AliceObservation
        return AliceObservation.objects.filter(
            category='pii_correction',
            resolved=False,
            config__action='rejected',
            config__text__iexact=text,
            config__pii_type=pii_type,
        ).exists()
    except Exception:
        return False


# ── Core Parser ──────────────────────────────────────────────────────

def parse_pii(text: str) -> list[dict[str, Any]]:
    """Parse text and return PII candidates with confidence scores.

    Each candidate:
        {
            'start': int,       # character position in text
            'end': int,
            'text': str,        # the matched text
            'type': str,        # ssn, card, email, phone, address, name, zip, company
            'confidence': float,# 0.0–1.0
            'tag': str,         # replacement tag like <email>
            'source': str,      # 'pattern', 'database', 'both'
        }

    Candidates are sorted by position. Overlapping matches are merged
    with the higher-confidence match winning.
    """
    candidates: list[dict[str, Any]] = []
    vocab = _build_contact_vocab()

    # ── Layer 1: Structural patterns ──
    for pattern, pii_type, tag, base_confidence in _PATTERNS:
        for m in pattern.finditer(text):
            matched_text = m.group()
            conf = base_confidence

            # Boost confidence if database confirms
            if pii_type == 'email' and matched_text.lower() in vocab.get('emails', set()):
                conf = min(1.0, conf + 0.05)
                source = 'both'
            elif pii_type == 'phone':
                digits = re.sub(r'\D', '', matched_text)
                if digits in vocab.get('phones', set()):
                    conf = min(1.0, conf + 0.10)
                    source = 'both'
                elif digits[:3] in vocab.get('phone_prefixes', set()):
                    conf = min(1.0, conf + 0.05)
                    source = 'both'
                else:
                    source = 'pattern'
            else:
                source = 'pattern'

            candidates.append({
                'start': m.start(),
                'end': m.end(),
                'text': matched_text,
                'type': pii_type,
                'confidence': conf,
                'tag': tag,
                'source': source,
            })

    # Prefix-based names (high confidence)
    for m in _NAME_PREFIX_RE.finditer(text):
        name_text = m.group(1)
        conf = 0.85
        source = 'pattern'
        if name_text.lower() in vocab.get('full_names', set()):
            conf = 0.95
            source = 'both'
        candidates.append({
            'start': m.start(1),
            'end': m.end(1),
            'text': name_text,
            'type': 'name',
            'confidence': conf,
            'tag': '<name>',
            'source': source,
        })

    # ── Layer 2: Database-driven detection ──

    # Full name matches (first + last from contacts)
    for full_name in vocab.get('full_names', set()):
        if len(full_name) < 4:
            continue
        # Case-insensitive search in text
        pattern = re.compile(re.escape(full_name), re.IGNORECASE)
        for m in pattern.finditer(text):
            matched = m.group()
            # Skip if already covered by a higher-confidence match
            if _overlaps_existing(candidates, m.start(), m.end()):
                continue
            if _is_known_false_positive(matched, 'name'):
                continue
            candidates.append({
                'start': m.start(),
                'end': m.end(),
                'text': matched,
                'type': 'name',
                'confidence': 0.90,
                'tag': '<name>',
                'source': 'database',
            })

    # Individual last names (lower confidence — "James" could be a word)
    for last_name in vocab.get('names_last', set()):
        if len(last_name) < 3 or last_name in _COMMON_WORDS:
            continue
        pattern = re.compile(r'\b' + re.escape(last_name) + r'\b', re.IGNORECASE)
        for m in pattern.finditer(text):
            matched = m.group()
            if _overlaps_existing(candidates, m.start(), m.end()):
                continue
            if _is_known_false_positive(matched, 'name'):
                continue
            # Only flag if it looks like a name (capitalized, not start of sentence)
            if m.start() > 0 and matched[0].isupper():
                candidates.append({
                    'start': m.start(),
                    'end': m.end(),
                    'text': matched,
                    'type': 'name',
                    'confidence': 0.50,
                    'tag': '<name>',
                    'source': 'database',
                })

    # Company names
    for company in vocab.get('companies', set()):
        if len(company) < 4:
            continue
        pattern = re.compile(re.escape(company), re.IGNORECASE)
        for m in pattern.finditer(text):
            if _overlaps_existing(candidates, m.start(), m.end()):
                continue
            if _is_known_false_positive(m.group(), 'company'):
                continue
            candidates.append({
                'start': m.start(),
                'end': m.end(),
                'text': m.group(),
                'type': 'company',
                'confidence': 0.70,
                'tag': '<company>',
                'source': 'database',
            })

    # Known addresses
    for addr in vocab.get('addresses', set()):
        if len(addr) < 8:
            continue
        pattern = re.compile(re.escape(addr), re.IGNORECASE)
        for m in pattern.finditer(text):
            if _overlaps_existing(candidates, m.start(), m.end()):
                continue
            candidates.append({
                'start': m.start(),
                'end': m.end(),
                'text': m.group(),
                'type': 'address',
                'confidence': 0.90,
                'tag': '<address>',
                'source': 'database',
            })

    # Sort by position, resolve overlaps
    candidates.sort(key=lambda c: (c['start'], -c['confidence']))
    candidates = _resolve_overlaps(candidates)

    return candidates


def _overlaps_existing(candidates: list[dict], start: int, end: int) -> bool:
    """Check if a span overlaps with any existing candidate."""
    for c in candidates:
        if start < c['end'] and end > c['start']:
            return True
    return False


def _resolve_overlaps(candidates: list[dict]) -> list[dict]:
    """Remove overlapping candidates, keeping the higher-confidence one."""
    if not candidates:
        return candidates
    result = [candidates[0]]
    for c in candidates[1:]:
        prev = result[-1]
        if c['start'] < prev['end']:
            # Overlap — keep the one with higher confidence
            if c['confidence'] > prev['confidence']:
                result[-1] = c
        else:
            result.append(c)
    return result


# ── Backwards-Compatible Auto-Scrub ──────────────────────────────────

def scrub_pii(text: str) -> tuple[str, int]:
    """Scrub PII from text, returning (scrubbed_text, count_of_replacements).

    Backwards compatible with the original API. Uses parse_pii internally.
    """
    candidates = parse_pii(text)
    if not candidates:
        return text, 0

    # Apply replacements from right to left to preserve positions
    result = text
    for c in reversed(candidates):
        result = result[:c['start']] + c['tag'] + result[c['end']:]

    return result, len(candidates)


# ── Small-Stings Learning Loop ───────────────────────────────────────

def record_pii_correction(
    original_text: str,
    candidate: dict[str, Any],
    action: str,
    corrected_type: str | None = None,
    user_id: int | None = None,
) -> None:
    """Record a user's PII correction as an Alice observation.

    action: 'confirmed' — user agrees this is PII
            'rejected'  — user says this is NOT PII (false positive)
            'corrected' — user changed the type (e.g., name → company)

    Each correction teaches Alice about this installation's data.
    """
    try:
        from apps.ai_assistant.models.alice import AliceObservation

        pii_type = corrected_type or candidate.get('type', 'unknown')

        obs = AliceObservation(
            category='pii_correction',
            source='alice',
            priority=0,
            message=f'PII {action}: "{candidate.get("text", "")}" as {pii_type}',
            detail=f'Original context: ...{original_text[max(0, candidate.get("start", 0) - 30):candidate.get("end", 0) + 30]}...',
            model_name='pii_scrub',
            config={
                'action': action,
                'text': candidate.get('text', ''),
                'pii_type': pii_type,
                'original_type': candidate.get('type', ''),
                'confidence': candidate.get('confidence', 0),
                'source': candidate.get('source', ''),
            },
            dedup_key=f'pii-{action}-{candidate.get("text", "").lower()}-{pii_type}',
        )
        if user_id:
            obs.contact_id = user_id
        obs.save()

        # Invalidate cache so next parse picks up the correction
        invalidate_vocab_cache()

        logger.info('PII correction recorded: %s "%s" as %s',
                     action, candidate.get('text', ''), pii_type)
    except Exception:
        logger.warning('Failed to record PII correction', exc_info=True)
