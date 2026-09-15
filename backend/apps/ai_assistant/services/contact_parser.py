"""
Contact Parser — tokenize pasted text into a grid of field-mapped chips.

Takes raw pasted text (email signatures, business cards, lists, etc.) and
splits it into rows (one per contact) and columns (PII fields). Works for
single or batch paste.

The UI presents this as a spreadsheet-style grid where each cell is a
draggable chip. Drag a chip from one column to another = Small-Sting.

Usage:
    from apps.ai_assistant.services.contact_parser import parse_contact_text

    result = parse_contact_text('''
        Bill James, CEO, JPods Inc, 612-555-1234, bill@jpods.com
        Jane Smith, VP Sales, Acme Corp, 651-555-9876, jane@acme.com
    ''')
    # {
    #   'columns': ['name_first', 'name_last', 'title', 'company', ...],
    #   'rows': [
    #     {'row': 1, 'chips': {'name_first': {...}, 'name_last': {...}, ...},
    #      'unassigned': [...], 'matches': [...]},
    #     ...
    #   ],
    # }
"""
import logging
import re
from typing import Any

logger = logging.getLogger('contact_parser')

# ── Column definitions (display order) ───────────────────────────────

COLUMNS = [
    {'field': 'name_prefix', 'label': 'prefix', 'width': 60},
    {'field': 'name_first', 'label': 'first', 'width': 100},
    {'field': 'name_last', 'label': 'last', 'width': 100},
    {'field': 'name_suffix', 'label': 'suffix', 'width': 60},
    {'field': 'title', 'label': 'title', 'width': 120},
    {'field': 'company', 'label': 'company', 'width': 140},
    {'field': 'department', 'label': 'dept', 'width': 100},
    {'field': 'email', 'label': 'email', 'width': 180},
    {'field': 'phone', 'label': 'phone', 'width': 130},
    {'field': 'phone2', 'label': 'phone2', 'width': 130},
    {'field': 'address1', 'label': 'address', 'width': 160},
    {'field': 'address2', 'label': 'addr2', 'width': 100},
    {'field': 'city', 'label': 'city', 'width': 100},
    {'field': 'state', 'label': 'st', 'width': 50},
    {'field': 'zip', 'label': 'zip', 'width': 70},
    {'field': 'country', 'label': 'country', 'width': 60},
    {'field': 'website', 'label': 'website', 'width': 160},
    {'field': 'birthdate', 'label': 'birthdate', 'width': 100},
    {'field': 'account_number', 'label': 'account #', 'width': 100},
]

FIELD_NAMES = [c['field'] for c in COLUMNS]

# ── Structural patterns ─────────────────────────────────────────────

_EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')

_PHONE_RE = re.compile(
    r'(?:\+?1[-.\s]?)?'
    r'(?:\(\d{3}\)|\d{3})'
    r'[-.\s]?'
    r'\d{3}'
    r'[-.\s]?'
    r'\d{4}'
)

_ZIP_RE = re.compile(r'^\d{5}(?:-\d{4})?$')

# Website: http(s)://... or www.something.com
_URL_RE = re.compile(
    r'(?:https?://)?(?:www\.)?[A-Za-z0-9][-A-Za-z0-9]*\.[A-Za-z]{2,}(?:/\S*)?'
)

# Birthdate: MM/DD/YYYY, MM-DD-YYYY, YYYY-MM-DD, Month DD YYYY
_DATE_RE = re.compile(
    r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
    r'|\d{4}[/-]\d{1,2}[/-]\d{1,2}'
    r'|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b',
    re.IGNORECASE,
)

# Account number: "Acct", "Account", "A/C", "#" followed by digits/alphanumeric
_ACCOUNT_RE = re.compile(
    r'(?:acct|account|a/c|cust(?:omer)?)\s*#?\s*[:\s]?\s*([A-Za-z0-9-]{3,20})',
    re.IGNORECASE,
)

_STREET_SUFFIXES = frozenset({
    'st', 'street', 'ave', 'avenue', 'blvd', 'boulevard', 'dr', 'drive',
    'rd', 'road', 'ln', 'lane', 'way', 'ct', 'court', 'pl', 'place',
    'cir', 'circle', 'pkwy', 'parkway', 'ter', 'terrace', 'hwy', 'highway',
})

_US_STATES = frozenset({
    'al', 'ak', 'az', 'ar', 'ca', 'co', 'ct', 'de', 'fl', 'ga',
    'hi', 'id', 'il', 'in', 'ia', 'ks', 'ky', 'la', 'me', 'md',
    'ma', 'mi', 'mn', 'ms', 'mo', 'mt', 'ne', 'nv', 'nh', 'nj',
    'nm', 'ny', 'nc', 'nd', 'oh', 'ok', 'or', 'pa', 'ri', 'sc',
    'sd', 'tn', 'tx', 'ut', 'vt', 'va', 'wa', 'wv', 'wi', 'wy',
    'dc',
})

_NAME_PREFIXES = frozenset({
    'mr', 'mrs', 'ms', 'dr', 'miss', 'prof', 'rev',
})

_NAME_SUFFIXES = frozenset({
    'jr', 'sr', 'ii', 'iii', 'iv', 'esq', 'phd', 'md', 'dds', 'dvm',
})

_TITLE_KEYWORDS = frozenset({
    'ceo', 'cfo', 'cto', 'coo', 'cio', 'cmo', 'chro',
    'president', 'vp', 'director', 'manager', 'supervisor',
    'coordinator', 'engineer', 'developer', 'designer', 'analyst',
    'architect', 'consultant', 'specialist', 'associate', 'assistant',
    'administrator', 'executive', 'officer', 'partner',
    'founder', 'owner', 'principal', 'chairman', 'chairwoman',
    'secretary', 'treasurer', 'buyer', 'purchasing agent',
})

_TITLE_PHRASES = frozenset({
    'vice president', 'general manager', 'account manager',
    'sales rep', 'sales manager', 'vp sales', 'vp marketing',
    'vp engineering', 'vp operations', 'chief executive',
})

# Corporate suffixes — if a token ends with one of these, it's a company
_COMPANY_SUFFIXES = frozenset({
    'inc', 'inc.', 'llc', 'llc.', 'ltd', 'ltd.', 'corp', 'corp.',
    'corporation', 'company', 'co', 'co.', 'lp', 'l.p.',
    'plc', 'gmbh', 'ag', 'sa', 'sarl', 'bv', 'nv',
    'pllc', 'llp', 'pc', 'p.c.', 'pa', 'p.a.',
    'foundation', 'association', 'assoc', 'assoc.',
    'group', 'partners', 'holdings', 'enterprises', 'services',
})

_DEPT_KEYWORDS = frozenset({
    'sales', 'marketing', 'engineering', 'finance', 'accounting',
    'human resources', 'it', 'operations', 'legal',
    'purchasing', 'procurement', 'logistics', 'shipping',
    'customer service', 'support', 'research',
})

# Labels that precede a value — strip and use as field hint
_LABEL_RE = re.compile(
    r'^(?:phone|ph|tel|fax|cell|mobile|work|home|office|direct'
    r'|email|e-mail|mail'
    r'|address|addr'
    r'|name|company|org|title|dept|department'
    r'|ext|extension'
    r')\s*[:.]\s*',
    re.IGNORECASE,
)

_LABEL_FIELD_MAP = {
    'phone': 'phone', 'ph': 'phone', 'tel': 'phone', 'cell': 'phone',
    'mobile': 'phone', 'work': 'phone', 'home': 'phone', 'office': 'phone',
    'direct': 'phone', 'fax': 'phone2',
    'email': 'email', 'e-mail': 'email', 'mail': 'email',
    'address': 'address1', 'addr': 'address1',
    'name': 'name_first', 'company': 'company', 'org': 'company',
    'title': 'title', 'dept': 'department', 'department': 'department',
}


# ── Name parsing (via nameparser library) ────────────────────────────

def _parse_name(text: str) -> dict[str, str] | None:
    """Parse a human name string into components using nameparser.

    Returns dict with keys: title, first, middle, last, suffix.
    Returns None if the text doesn't look like a name.
    """
    try:
        from nameparser import HumanName
        name = HumanName(text)
        # Reject if no last name parsed (likely not a name)
        if not name.last:
            return None
        return {
            'title': str(name.title).strip(),
            'first': str(name.first).strip(),
            'middle': str(name.middle).strip(),
            'last': str(name.last).strip(),
            'suffix': str(name.suffix).strip(),
        }
    except ImportError:
        # Fallback: simple first/last split
        words = text.split()
        if len(words) >= 2:
            return {'title': '', 'first': words[0], 'middle': '', 'last': words[-1], 'suffix': ''}
        return None
    except Exception:
        return None


# ── Tokenizer ────────────────────────────────────────────────────────

def _tokenize_line(line: str) -> list[str]:
    """Split a single line into tokens on commas/pipes/tabs."""
    tokens = []
    parts = re.split(r'[|\t]', line)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if _EMAIL_RE.fullmatch(part) or _PHONE_RE.fullmatch(part):
            tokens.append(part)
            continue
        comma_parts = [p.strip() for p in part.split(',') if p.strip()]
        i = 0
        while i < len(comma_parts):
            cp = comma_parts[i]
            # Rejoin "City, ST" or "City, ST ZIP"
            if (i + 1 < len(comma_parts)
                    and len(comma_parts[i + 1].split()[0]) <= 2
                    and comma_parts[i + 1].split()[0].upper() in _US_STATES):
                cp = cp + ', ' + comma_parts[i + 1]
                i += 1
            tokens.append(cp)
            i += 1
    return tokens


def _split_into_rows(text: str) -> list[list[str]]:
    """Split pasted text into rows of tokens. Each row = one contact.

    Row boundaries:
    - Blank lines
    - Lines that start a new name pattern after address/phone/email
    """
    lines = [ln.strip() for ln in text.strip().split('\n')]
    rows: list[list[str]] = []
    current_tokens: list[str] = []

    blank_count = 0
    for line in lines:
        if not line:
            blank_count += 1
            continue

        line_tokens = _tokenize_line(line)
        if not line_tokens:
            continue

        # Two+ blank lines = definite row boundary
        # One blank line = possible boundary, check if next line looks like new contact
        if current_tokens:
            if blank_count >= 2:
                rows.append(current_tokens)
                current_tokens = []
            elif blank_count >= 1 and _looks_like_new_contact(line_tokens, current_tokens):
                rows.append(current_tokens)
                current_tokens = []
            elif blank_count == 0 and _looks_like_new_contact(line_tokens, current_tokens):
                rows.append(current_tokens)
                current_tokens = []

        blank_count = 0
        current_tokens.extend(line_tokens)

    if current_tokens:
        rows.append(current_tokens)

    return rows


def _looks_like_new_contact(new_tokens: list[str], existing_tokens: list[str]) -> bool:
    """Check if new tokens look like they start a new contact."""
    if not new_tokens:
        return False
    first = new_tokens[0]

    # If we already have an email and this line has a new email, new contact
    has_email = any(_EMAIL_RE.fullmatch(t) for t in existing_tokens)
    new_email = any(_EMAIL_RE.fullmatch(t) for t in new_tokens)
    if has_email and new_email:
        return True

    # If first token is a capitalized word pair (looks like a name)
    # and we already assigned a name
    words = first.split()
    has_name = any(
        w[0].isupper() and w.isalpha() and len(w) > 1
        for t in existing_tokens[:2]
        for w in t.split()[:1]
    )
    # Exclude tokens with company suffixes (Inc, LLC, Corp, etc.)
    last_word = words[-1].lower().rstrip('.') if words else ''
    is_company = last_word in {s.rstrip('.') for s in _COMPANY_SUFFIXES}
    looks_like_name = (
        len(words) >= 2
        and all(w[0].isupper() and w.isalpha() for w in words[:2])
        and not _EMAIL_RE.fullmatch(first)
        and not _PHONE_RE.fullmatch(first)
        and not is_company
    )
    if has_name and looks_like_name:
        return True

    return False


# ── Classifier ───────────────────────────────────────────────────────

def _classify_token(token: str, vocab: dict, position: int,
                    assigned: dict[str, bool], learned: dict[str, str]) -> tuple[str, float, str]:
    """Classify a token into a field.

    Returns (field_name, confidence, source).
    """
    clean = token.strip()
    lower = clean.lower()
    bare = lower.rstrip('.')

    # Learned corrections (highest priority)
    if lower in learned:
        return learned[lower], 0.95, 'learned'

    # ── Structural (high confidence) ──

    if _EMAIL_RE.fullmatch(clean):
        return 'email', 0.95, 'pattern'

    # Website (check before phone — URLs can contain digits)
    if _URL_RE.fullmatch(clean) and not _EMAIL_RE.fullmatch(clean):
        return 'website', 0.90, 'pattern'

    if _PHONE_RE.fullmatch(clean):
        field = 'phone2' if assigned.get('phone') else 'phone'
        return field, 0.90, 'pattern'

    # Birthdate
    if _DATE_RE.fullmatch(clean):
        return 'birthdate', 0.80, 'pattern'

    # Account number (with label)
    acct_match = _ACCOUNT_RE.match(clean)
    if acct_match:
        return 'account_number', 0.85, 'pattern'

    if _ZIP_RE.match(clean):
        return 'zip', 0.90, 'pattern'

    if len(clean) == 2 and clean.upper() in _US_STATES:
        return 'state', 0.85, 'pattern'

    if bare in _NAME_PREFIXES:
        return 'name_prefix', 0.90, 'pattern'

    if bare in _NAME_SUFFIXES:
        return 'name_suffix', 0.90, 'pattern'

    # Street address
    words = clean.split()
    if len(words) >= 2 and words[0].isdigit():
        last_word = words[-1].lower().rstrip('.')
        if last_word in _STREET_SUFFIXES:
            return 'address1', 0.85, 'pattern'
        if len(words) >= 3:
            return 'address1', 0.60, 'heuristic'

    # Suite/Apt line
    if re.match(r'^(?:suite|ste|apt|unit|#)\s', lower):
        return 'address2', 0.85, 'pattern'

    # City, ST ZIP combined
    city_st_zip = re.match(r'^(.+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$', clean)
    if city_st_zip:
        return 'city', 0.85, 'pattern'  # UI will need to split this

    # ── Company suffix (Inc, LLC, Corp, etc.) — highest priority for multi-word tokens ──
    if len(words) >= 2:
        last_word = words[-1].lower().rstrip('.')
        if last_word in {s.rstrip('.') for s in _COMPANY_SUFFIXES}:
            return 'company', 0.90, 'pattern'

    # ── Keywords (check before database to avoid "CEO" → company) ──

    if lower in _TITLE_KEYWORDS:
        return 'title', 0.80, 'pattern'

    for phrase in _TITLE_PHRASES:
        if phrase in lower:
            return 'title', 0.75, 'pattern'

    if lower in _DEPT_KEYWORDS:
        return 'department', 0.75, 'pattern'

    # ── Database (medium-high confidence) ──

    if lower in vocab.get('companies', set()):
        return 'company', 0.85, 'database'

    # Fuzzy company: token contains a known company name (min 4 chars),
    # or known company starts with the token (min 4 chars)
    if len(lower) >= 4:
        for known_co in vocab.get('companies', set()):
            if len(known_co) >= 4:
                # "JPods Inc" contains "jpods" — match
                # But "CEO" should NOT match "ceo & co-founder"
                if known_co in lower or (lower.startswith(known_co) and len(lower) - len(known_co) <= 5):
                    return 'company', 0.75, 'database'

    if lower in vocab.get('full_names', set()):
        if not assigned.get('name_first'):
            return 'name_first', 0.85, 'database'
        return 'name_last', 0.80, 'database'

    if lower in vocab.get('names_first', set()) and not assigned.get('name_first'):
        return 'name_first', 0.80, 'database'

    if lower in vocab.get('names_last', set()) and not assigned.get('name_last'):
        return 'name_last', 0.80, 'database'

    if lower in vocab.get('cities', set()):
        return 'city', 0.70, 'database'

    # All-caps single word after address fields — likely a city
    if (clean.isupper() and len(clean) >= 3 and clean.isalpha()
            and assigned.get('address1') and not assigned.get('city')):
        return 'city', 0.60, 'heuristic'

    # ── Positional heuristics ──

    if len(words) == 1 and clean[0].isupper() and clean.isalpha() and len(clean) > 1:
        if not assigned.get('name_first') and position == 0:
            return 'name_first', 0.50, 'heuristic'
        if not assigned.get('name_last') and position == 1:
            return 'name_last', 0.50, 'heuristic'

    if clean.isupper() and len(words) >= 2 and not assigned.get('company'):
        return 'company', 0.45, 'heuristic'

    return 'unassigned', 0.20, 'heuristic'


def _load_learned_corrections() -> dict[str, str]:
    """Load Alice's learned field mappings from correction observations."""
    learned: dict[str, str] = {}
    try:
        from apps.ai_assistant.models.alice import AliceObservation
        corrections = AliceObservation.objects.filter(
            category='pii_correction',
            model_name='contact_parser',
            resolved=False,
        ).values_list('config', flat=True).iterator()

        for config in corrections:
            if not isinstance(config, dict):
                continue
            text = (config.get('text', '') or '').lower()
            field = config.get('corrected_field', '')
            if text and field and field in FIELD_NAMES:
                learned[text] = field
    except Exception:
        pass
    return learned


# ── Structured Data Detection + Column Mapper ────────────────────────

# Header synonyms → WC3 field. Lowercase, stripped.
_HEADER_MAP: dict[str, str] = {
    # Name
    'first name': 'name_first', 'first': 'name_first', 'firstname': 'name_first',
    'fname': 'name_first', 'given name': 'name_first', 'given': 'name_first',
    'last name': 'name_last', 'last': 'name_last', 'lastname': 'name_last',
    'lname': 'name_last', 'surname': 'name_last', 'family name': 'name_last',
    'name': 'name_first',  # single "name" column — will split later
    'full name': 'name_first',  # will split
    'prefix': 'name_prefix', 'title prefix': 'name_prefix', 'salutation': 'name_prefix',
    'suffix': 'name_suffix', 'name suffix': 'name_suffix',
    'middle name': 'name_middle', 'middle': 'name_middle', 'mi': 'name_middle',
    # Title / role
    'title': 'title', 'job title': 'title', 'position': 'title', 'role': 'title',
    'occupation': 'title',
    # Company / org
    'company': 'company', 'organization': 'company', 'org': 'company',
    'company name': 'company', 'employer': 'company', 'business': 'company',
    'firm': 'company', 'institution': 'company',
    # Department
    'department': 'department', 'dept': 'department', 'division': 'department',
    # Email
    'email': 'email', 'e-mail': 'email', 'email address': 'email',
    'e-mail address': 'email', 'mail': 'email',
    # Phone
    'phone': 'phone', 'phone number': 'phone', 'telephone': 'phone',
    'tel': 'phone', 'mobile': 'phone', 'cell': 'phone', 'cell phone': 'phone',
    'work phone': 'phone', 'office phone': 'phone', 'direct': 'phone',
    'phone2': 'phone2', 'fax': 'phone2', 'home phone': 'phone2', 'alt phone': 'phone2',
    # Address
    'address': 'address1', 'address1': 'address1', 'address 1': 'address1',
    'street': 'address1', 'street address': 'address1', 'mailing address': 'address1',
    'address2': 'address2', 'address 2': 'address2', 'suite': 'address2',
    'apt': 'address2', 'unit': 'address2',
    'city': 'city', 'town': 'city',
    'state': 'state', 'st': 'state', 'province': 'state', 'region': 'state',
    'zip': 'zip', 'zip code': 'zip', 'zipcode': 'zip', 'postal code': 'zip',
    'postal': 'zip', 'postcode': 'zip',
    'country': 'country', 'nation': 'country',
    # Web
    'website': 'website', 'web': 'website', 'url': 'website', 'homepage': 'website',
    # Dates
    'birthday': 'birthdate', 'birthdate': 'birthdate', 'dob': 'birthdate',
    'date of birth': 'birthdate', 'birth date': 'birthdate',
    # Account
    'account': 'account_number', 'account number': 'account_number',
    'acct': 'account_number', 'account #': 'account_number', 'customer #': 'account_number',
    'id': 'account_number', 'member id': 'account_number',
    # Unmapped but common — go to unassigned with label
    'district': '_district', 'party': '_party', 'room': '_room',
    'ward': '_district', 'precinct': '_district',
    'affiliation': '_party', 'political party': '_party',
    'office': '_room', 'room number': '_room',
}


def _detect_delimiter(text: str) -> str | None:
    """Detect the primary delimiter in structured text.

    Priority: tab > pipe > semicolon > comma > multi-space.
    Returns the delimiter string, or None if not structured.
    """
    lines = [ln for ln in text.strip().split('\n') if ln.strip()]
    if len(lines) < 2:
        return None

    # Count delimiters per line
    candidates = [
        ('\t', 'tab'),
        ('|', 'pipe'),
        (';', 'semi'),
    ]

    for delim, _name in candidates:
        # Only count lines that actually contain the delimiter (skip short/noise lines)
        counts = [ln.count(delim) for ln in lines[:20] if ln.count(delim) >= 2]
        if len(counts) < 2:
            # Also try: majority of lines have the delimiter
            all_counts = [ln.count(delim) for ln in lines[:20]]
            has_delim = [c for c in all_counts if c >= 2]
            if len(has_delim) >= len(all_counts) * 0.4:
                counts = has_delim
            else:
                continue
        # Structured = consistent count across delimiter-containing lines (±2), and at least 2
        min_c, max_c = min(counts), max(counts)
        avg_c = sum(counts) / len(counts)
        if avg_c >= 2 and (max_c - min_c) <= 3:
            return delim

    # Comma — trickier because addresses contain commas.
    # Only use if count is very consistent.
    comma_counts = [ln.count(',') for ln in lines[:10]]
    if comma_counts:
        avg_c = sum(comma_counts) / len(comma_counts)
        min_c, max_c = min(comma_counts), max(comma_counts)
        if avg_c >= 3 and (max_c - min_c) <= 1:
            return ','

    # Multi-space (2+) — common in fixed-width or space-padded exports
    import re as _re
    space_counts = [len(_re.findall(r'  +', ln)) for ln in lines[:10]]
    if space_counts:
        avg_s = sum(space_counts) / len(space_counts)
        min_s, max_s = min(space_counts), max(space_counts)
        if avg_s >= 2 and (max_s - min_s) <= 2:
            return '  '  # double-space sentinel

    return None


def _is_header_row(cells: list[str]) -> bool:
    """Check if a row of cells looks like a header (column labels, not data)."""
    if not cells:
        return False
    matched = 0
    for cell in cells:
        clean = cell.strip().lower().rstrip(':')
        if clean in _HEADER_MAP or clean in ('follow', 'photo', 'legislator photo',
            'follow in my legislature', 'follow in legislature'):
            matched += 1
    # At least 30% of cells match known headers
    return matched >= max(2, len(cells) * 0.3)


def _map_headers(cells: list[str]) -> list[str]:
    """Map header cell text to WC3 field names.

    Returns list of field names (same length as cells).
    Unknown headers get '_unknown_N' prefix so they go to unassigned.
    """
    fields = []
    seen: set[str] = set()
    unknown_idx = 0

    for cell in cells:
        clean = cell.strip().lower().rstrip(':')
        # Try exact match
        field = _HEADER_MAP.get(clean)
        # Try without common prefixes
        if not field:
            for prefix in ('follow ', 'legislator ', 'contact '):
                if clean.startswith(prefix):
                    field = _HEADER_MAP.get(clean[len(prefix):])
                    if field:
                        break
        # Try partial match
        if not field:
            for header_key, header_field in _HEADER_MAP.items():
                if header_key in clean or clean in header_key:
                    field = header_field
                    break

        if not field:
            unknown_idx += 1
            field = f'_unknown_{unknown_idx}'

        # Handle duplicate fields (e.g., two phone columns)
        if field in seen and not field.startswith('_'):
            if field == 'phone':
                field = 'phone2'
            elif field == 'email':
                field = f'_email2'
            else:
                field = f'_{field}_dup'
        seen.add(field)
        fields.append(field)

    return fields


def detect_structure(text: str) -> dict[str, Any] | None:
    """Step 1: Detect if text is structured, find header, propose column mapping.

    Scans forward past noise/empty rows to find the header row.
    Returns mapping proposal for user confirmation, or None if not structured.

    Response:
        {
            'structured': True,
            'delimiter': '\\t',
            'delimiter_name': 'tab',
            'header_row': 3,           # line number where header was found
            'skipped_rows': 2,         # noise rows discarded before header
            'columns': [
                {'index': 0, 'header': 'First Name', 'mapped_to': 'name_first', 'confidence': 1.0},
                {'index': 1, 'header': 'Last Name', 'mapped_to': 'name_last', 'confidence': 1.0},
                {'index': 2, 'header': 'District', 'mapped_to': '_district', 'confidence': 0.5},
                ...
            ],
            'sample_rows': [first 3 data rows for preview],
            'total_data_rows': 160,
        }
    """
    delimiter = _detect_delimiter(text)
    if not delimiter:
        return None

    lines = text.strip().split('\n')
    lines = [ln.strip('\r') for ln in lines]

    delimiter_names = {'\t': 'tab', ',': 'comma', '|': 'pipe', ';': 'semicolon', '  ': 'spaces'}

    # Scan forward to find the header row — skip empty/noise lines
    header_idx = None
    header_cells = None
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if delimiter == '  ':
            cells = re.split(r'  +', line)
        else:
            cells = line.split(delimiter)
        cells = [c.strip() for c in cells]
        if _is_header_row(cells):
            header_idx = i
            header_cells = cells
            break

    if header_idx is None or header_cells is None:
        return None

    # Find most common data column count (lines after header)
    data_lines = lines[header_idx + 1:]
    data_col_counts: dict[int, int] = {}
    for ln in data_lines:
        if not ln.strip():
            continue
        if delimiter == '  ':
            cells = re.split(r'  +', ln)
        else:
            cells = ln.split(delimiter)
        n = len(cells)
        if n >= 2:
            data_col_counts[n] = data_col_counts.get(n, 0) + 1

    most_common_cols = max(data_col_counts, key=data_col_counts.get) if data_col_counts else len(header_cells)

    # Trim header if it has more columns than data
    header_count = len(header_cells)
    if header_count > most_common_cols:
        excess = header_count - most_common_cols
        header_cells = header_cells[excess:]

    # Map headers
    field_map = _map_headers(header_cells)

    # Build column proposals
    columns = []
    for idx, (header, field) in enumerate(zip(header_cells, field_map)):
        mapped = not field.startswith('_')
        columns.append({
            'index': idx,
            'header': header,
            'mapped_to': field if mapped else '',
            'unmapped_label': field.lstrip('_').replace('_', ' ') if not mapped else '',
            'confidence': 0.95 if mapped else 0.0,
        })

    # Sample data rows (first 3, skip noise lines)
    sample_rows = []
    total_data = 0
    for ln in data_lines:
        if not ln.strip():
            continue
        if delimiter == '  ':
            cells = re.split(r'  +', ln)
        else:
            cells = ln.split(delimiter)
        cells = [c.strip() for c in cells]
        # Skip short noise lines
        if len(cells) < most_common_cols - 1:
            continue
        total_data += 1
        if len(sample_rows) < 3:
            sample_rows.append(cells[:len(field_map)])

    return {
        'structured': True,
        'delimiter': delimiter,
        'delimiter_name': delimiter_names.get(delimiter, delimiter),
        'header_row': header_idx,
        'skipped_rows': header_idx,
        'columns': columns,
        'sample_rows': sample_rows,
        'total_data_rows': total_data,
        'available_fields': [{'field': c['field'], 'label': c['label']} for c in COLUMNS],
    }


def parse_structured_confirmed(text: str, delimiter: str, column_map: list[dict],
                                header_row: int = 0) -> dict[str, Any]:
    """Step 2: Parse structured text using user-confirmed column mapping.

    column_map: list of {'index': N, 'mapped_to': 'name_first'} — user-confirmed mapping.
    Unmapped columns (mapped_to == '' or starts with '_') go to prefs.userdefined.

    Returns same grid format as parse_contact_text.
    """
    from .pii_scrub import _build_contact_vocab
    vocab = _build_contact_vocab()

    lines = text.strip().split('\n')
    lines = [ln.strip('\r') for ln in lines]
    data_lines = lines[header_row + 1:]

    # Build field list from confirmed map
    field_list = []
    unmapped_labels = {}
    for col in column_map:
        field = col.get('mapped_to', '')
        if field and not field.startswith('_'):
            field_list.append(field)
        else:
            label = col.get('unmapped_label', col.get('header', f'col_{col["index"]}'))
            field_list.append(f'_ud_{col["index"]}')
            unmapped_labels[f'_ud_{col["index"]}'] = label

    # Find most common column count to filter noise lines
    col_counts: dict[int, int] = {}
    for ln in data_lines:
        if not ln.strip():
            continue
        if delimiter == '  ':
            cells = re.split(r'  +', ln)
        else:
            cells = ln.split(delimiter)
        n = len(cells)
        if n >= 2:
            col_counts[n] = col_counts.get(n, 0) + 1
    expected_cols = max(col_counts, key=col_counts.get) if col_counts else len(field_list)

    rows = []
    chip_id = 0

    for line in data_lines:
        if not line.strip():
            continue

        if delimiter == '  ':
            cells = re.split(r'  +', line)
        else:
            cells = line.split(delimiter)
        cells = [c.strip() for c in cells]

        # Skip noise lines (too few columns)
        if len(cells) < expected_cols - 1:
            continue

        # Build JSON record from column map
        record: dict[str, str] = {}
        userdefined: dict[str, str] = {}

        for col_idx, cell_val in enumerate(cells):
            if not cell_val or col_idx >= len(field_list):
                continue
            field = field_list[col_idx]

            if field.startswith('_ud_'):
                label = unmapped_labels.get(field, field)
                userdefined[label] = cell_val
            else:
                record[field] = cell_val

        # Skip vacant / empty records
        first = record.get('name_first', '').lower()
        if first in ('vacant', ''):
            if not record.get('name_last') and not record.get('email'):
                continue

        # Handle "Name" column that contains "First Last" — split with nameparser
        if 'name_first' in record and ' ' in record['name_first'] and 'name_last' not in record:
            parsed = _parse_name(record['name_first'])
            if parsed and parsed.get('last'):
                record['name_first'] = parsed['first']
                record['name_last'] = parsed['last']
                if parsed.get('suffix'):
                    record['name_suffix'] = parsed['suffix']
                if parsed.get('title'):
                    record['name_prefix'] = parsed['title']

        # Build chips from JSON record
        chips: dict[str, dict] = {}
        unassigned: list[dict] = []

        for field, val in record.items():
            if not val:
                continue
            chip_id += 1
            conf = 0.90
            src = 'column_map'

            # Boost from database
            lower = val.lower()
            if field == 'name_first' and lower in vocab.get('names_first', set()):
                conf = 0.95; src = 'column_map+db'
            elif field == 'name_last' and lower in vocab.get('names_last', set()):
                conf = 0.95; src = 'column_map+db'
            elif field == 'company' and lower in vocab.get('companies', set()):
                conf = 0.95; src = 'column_map+db'

            chips[field] = {'id': chip_id, 'text': val, 'confidence': conf, 'source': src}

        # Userdefined values shown in staging for now, saved to prefs.userdefined on commit
        for label, val in userdefined.items():
            chip_id += 1
            unassigned.append({
                'id': chip_id, 'text': f'{label}: {val}',
                'confidence': 0.50, 'source': 'unmapped',
                '_userdefined_key': label, '_userdefined_val': val,
            })

        if chips:
            matches = _find_contact_matches(chips)
            rows.append({
                'row': len(rows) + 1,
                'chips': chips,
                'unassigned': unassigned,
                'matches': matches,
                'raw': line,
                '_userdefined': userdefined,
            })

    return {
        'columns': COLUMNS,
        'rows': rows,
        'detected_delimiter': delimiter,
        'mode': 'structured',
    }


def _parse_structured_no_header(text: str, delimiter: str) -> dict[str, Any] | None:
    """Parse structured data without a header row.

    Uses content-based guessing: emails → email column, phones → phone column,
    names → first columns, etc. Warns the user that no header was found.
    """
    from .pii_scrub import _build_contact_vocab
    vocab = _build_contact_vocab()
    learned = _load_learned_corrections()

    lines = text.strip().split('\n')
    lines = [ln.strip('\r').strip() for ln in lines if ln.strip()]

    if len(lines) < 1:
        return None

    rows = []
    chip_id = 0

    for line in lines:
        if delimiter == '  ':
            cells = re.split(r'  +', line)
        else:
            cells = line.split(delimiter)
        cells = [c.strip() for c in cells]

        if len([c for c in cells if c]) < 2:
            continue

        chips: dict[str, dict] = {}
        unassigned: list[dict] = []
        assigned: dict[str, bool] = {}

        for cell_val in cells:
            if not cell_val:
                continue

            # Classify each cell by content
            field, conf, src = _classify_token(cell_val, vocab, 0, assigned, learned)

            chip_id += 1
            chip = {'id': chip_id, 'text': cell_val, 'confidence': conf, 'source': src}

            if field == 'unassigned' or field in assigned:
                unassigned.append(chip)
            else:
                chips[field] = chip
                assigned[field] = True

        if chips:
            first_val = (chips.get('name_first', {}).get('text', '') or '').lower()
            if first_val == 'vacant':
                continue
            matches = _find_contact_matches(chips)
            rows.append({
                'row': len(rows) + 1,
                'chips': chips,
                'unassigned': unassigned,
                'matches': matches,
                'raw': line,
            })

    if not rows:
        return None

    return {
        'columns': COLUMNS,
        'rows': rows,
        'detected_delimiter': delimiter,
        'mode': 'structured_no_header',
        '_warning': 'No header row detected. Fields mapped by content. Review carefully.',
    }


# ── Main Entry Point ─────────────────────────────────────────────────

def parse_contact_text(text: str) -> dict[str, Any]:
    """Parse pasted text into a grid of rows and columns.

    Returns:
        {
            'columns': [{'field': 'name_first', 'label': 'first', 'width': 100}, ...],
            'rows': [
                {
                    'row': 1,
                    'chips': {
                        'name_first': {'id': 1, 'text': 'Bill', 'confidence': 0.85, 'source': 'database'},
                        'name_last': {'id': 2, 'text': 'James', ...},
                        ...
                    },
                    'unassigned': [{'id': 9, 'text': 'something', ...}],
                    'matches': [{'id': 42, 'display_name': 'Bill James', 'confidence': 0.95}],
                    'raw': 'Bill James, CEO, JPods Inc, ...',
                },
                ...
            ],
        }
    """
    # Try structured parsing first (tab/csv/pipe delimited)
    delimiter = _detect_delimiter(text)
    if delimiter:
        # Try with header
        detection = detect_structure(text)
        if detection:
            # Auto-parse with detected mapping (UI will confirm in step 2)
            result = parse_structured_confirmed(
                text, delimiter,
                detection['columns'],
                header_row=detection['header_row'],
            )
            if result and result.get('rows'):
                result['_detection'] = detection  # pass detection to UI
                return result

        # No header found — still structured, do best-effort positional mapping
        result = _parse_structured_no_header(text, delimiter)
        if result and result.get('rows'):
            result['_no_header'] = True
            return result

    # Fall back to free-form parsing
    from .pii_scrub import _build_contact_vocab

    vocab = _build_contact_vocab()
    learned = _load_learned_corrections()
    token_rows = _split_into_rows(text)

    rows = []
    chip_id = 0

    for row_idx, tokens in enumerate(token_rows):
        assigned: dict[str, bool] = {}
        chips: dict[str, dict] = {}
        unassigned: list[dict] = []

        for tok_idx, token in enumerate(tokens):
            # Strip labels
            label_hint = None
            label_match = _LABEL_RE.match(token)
            if label_match:
                label_word = label_match.group().split(':')[0].split('.')[0].strip().lower()
                label_hint = _LABEL_FIELD_MAP.get(label_word)
                token = token[label_match.end():].strip()
                if not token:
                    continue

            # Company suffix check — before nameparser so "Wyoming Registered Agent Inc"
            # goes to company, not through name parsing
            words = token.split()
            if len(words) >= 2:
                last_word = words[-1].lower().rstrip('.')
                if last_word in {s.rstrip('.') for s in _COMPANY_SUFFIXES}:
                    chip_id += 1
                    chips['company'] = {
                        'id': chip_id, 'text': token,
                        'confidence': 0.90, 'source': 'pattern',
                    }
                    assigned['company'] = True
                    continue

            # Try nameparser for multi-word tokens that might be names
            if (len(words) >= 2
                    and not assigned.get('name_first')
                    and not _EMAIL_RE.fullmatch(token)
                    and not _PHONE_RE.fullmatch(token)
                    and not _PHONE_RE.search(token)
                    and any(w[0].isupper() for w in words[:2] if w)):
                parsed_name = _parse_name(token)
                if parsed_name and parsed_name.get('last'):
                    # Check database for confidence boost
                    full_lower = f"{parsed_name.get('first', '')} {parsed_name['last']}".lower().strip()
                    is_known = (
                        full_lower in vocab.get('full_names', set())
                        or parsed_name.get('first', '').lower() in vocab.get('names_first', set())
                        or parsed_name['last'].lower() in vocab.get('names_last', set())
                    )
                    conf = 0.85 if is_known else 0.65
                    src = 'database' if is_known else 'nameparser'

                    if parsed_name.get('title'):
                        chip_id += 1
                        chips['name_prefix'] = {
                            'id': chip_id, 'text': parsed_name['title'],
                            'confidence': 0.90, 'source': 'nameparser',
                        }
                        assigned['name_prefix'] = True
                    if parsed_name.get('first'):
                        chip_id += 1
                        chips['name_first'] = {
                            'id': chip_id, 'text': parsed_name['first'],
                            'confidence': conf, 'source': src,
                        }
                        assigned['name_first'] = True
                    if parsed_name.get('last'):
                        chip_id += 1
                        chips['name_last'] = {
                            'id': chip_id, 'text': parsed_name['last'],
                            'confidence': conf, 'source': src,
                        }
                        assigned['name_last'] = True
                    if parsed_name.get('suffix'):
                        chip_id += 1
                        chips['name_suffix'] = {
                            'id': chip_id, 'text': parsed_name['suffix'],
                            'confidence': 0.90, 'source': 'nameparser',
                        }
                        assigned['name_suffix'] = True
                    continue

            # Split "ST ZIP" (no city)
            st_zip = re.match(r'^([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$', token)
            if st_zip:
                state_val, zip_val = st_zip.groups()
                if state_val.lower() in _US_STATES:
                    chip_id += 1
                    chips['state'] = {
                        'id': chip_id, 'text': state_val,
                        'confidence': 0.90, 'source': 'pattern',
                    }
                    assigned['state'] = True
                    chip_id += 1
                    chips['zip'] = {
                        'id': chip_id, 'text': zip_val,
                        'confidence': 0.90, 'source': 'pattern',
                    }
                    assigned['zip'] = True
                    continue

            # Split "City, ST ZIP"
            city_st_zip = re.match(r'^(.+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$', token)
            if city_st_zip:
                city_val, state_val, zip_val = city_st_zip.groups()
                chip_id += 1
                chips['city'] = {
                    'id': chip_id, 'text': city_val.strip(),
                    'confidence': 0.85, 'source': 'pattern',
                }
                assigned['city'] = True
                chip_id += 1
                chips['state'] = {
                    'id': chip_id, 'text': state_val,
                    'confidence': 0.90, 'source': 'pattern',
                }
                assigned['state'] = True
                chip_id += 1
                chips['zip'] = {
                    'id': chip_id, 'text': zip_val,
                    'confidence': 0.90, 'source': 'pattern',
                }
                assigned['zip'] = True
                continue

            # Classify
            if label_hint and label_hint != 'unassigned':
                field, conf, src = label_hint, 0.90, 'pattern'
            else:
                field, conf, src = _classify_token(
                    token, vocab, tok_idx, assigned, learned,
                )

            chip_id += 1
            chip = {'id': chip_id, 'text': token, 'confidence': conf, 'source': src}

            if field == 'unassigned' or field in assigned:
                unassigned.append(chip)
            else:
                chips[field] = chip
                assigned[field] = True

        # Find matching contacts
        matches = _find_contact_matches(chips)

        rows.append({
            'row': row_idx + 1,
            'chips': chips,
            'unassigned': unassigned,
            'matches': matches,
            'raw': ', '.join(tokens),
        })

    return {
        'columns': COLUMNS,
        'rows': rows,
    }


def _find_contact_matches(chips: dict[str, dict]) -> list[dict[str, Any]]:
    """Find existing contacts matching the parsed chips.

    Returns field-level data so the UI can show each match as a full row
    with the same columns as the incoming data for side-by-side comparison.
    """
    matches = []
    first = chips.get('name_first', {}).get('text', '')
    last = chips.get('name_last', {}).get('text', '')
    email = chips.get('email', {}).get('text', '')

    try:
        from apps.core.models.contact import Contact
        from django.db.models import Q

        q = Q()
        if email:
            q |= Q(email__iexact=email)
        if first and last:
            q |= Q(name_first__iexact=first, name_last__iexact=last)
        elif last:
            q |= Q(name_last__iexact=last)

        if q:
            for c in Contact.objects.filter(q, is_active=True)[:5]:
                conf = 0.0
                if email and c.email and c.email.lower() == email.lower():
                    conf = 0.95
                elif (first and last
                      and c.name_first.lower() == first.lower()
                      and c.name_last.lower() == last.lower()):
                    conf = 0.90
                elif last and c.name_last.lower() == last.lower():
                    conf = 0.60

                # Build field-level data for this match
                fields = {
                    'name_prefix': c.name_prefix or '',
                    'name_first': c.name_first or '',
                    'name_last': c.name_last or '',
                    'name_suffix': c.name_suffix or '',
                    'title': c.title or '',
                    'company': c.company or '',
                    'department': c.department or '',
                    'email': c.email or '',
                }

                # Get phone
                try:
                    from apps.communications.models.phone import Phone
                    phone = Phone.objects.filter(contact_id=c.id).order_by('id').first()
                    if phone:
                        fields['phone'] = phone.number or ''
                except Exception:
                    pass

                # Get address
                try:
                    from apps.communications.models.address import Address
                    addr = Address.objects.filter(contact_id=c.id).order_by('id').first()
                    if addr:
                        fields['address1'] = addr.address1 or ''
                        fields['address2'] = addr.address2 or ''
                        fields['city'] = addr.city or ''
                        fields['state'] = addr.state or ''
                        fields['zip'] = addr.zip or ''
                        fields['country'] = addr.country or ''
                except Exception:
                    pass

                matches.append({
                    'id': c.id,
                    'display_name': f'{c.name_first} {c.name_last}'.strip(),
                    'confidence': conf,
                    'fields': fields,
                })
    except Exception:
        logger.debug('Contact match failed', exc_info=True)

    matches.sort(key=lambda m: -m['confidence'])
    return matches


# ── Load Existing Contacts (search + cleanup mode) ──────────────────

def load_contacts(query: str, limit: int = 20) -> dict[str, Any]:
    """Search existing contacts and return them in the same grid format.

    Each contact becomes a row with editable chips. Cross-row duplicate
    scores show which contacts might be the same person.
    """
    from apps.core.models.contact import Contact
    from django.db.models import Q

    q = Q()
    if query:
        q = (
            Q(name_first__icontains=query)
            | Q(name_last__icontains=query)
            | Q(company__icontains=query)
            | Q(email__icontains=query)
        )

    contacts = Contact.objects.filter(q, is_active=True).order_by('name_last', 'name_first')[:limit]

    rows = []
    chip_id = 0
    for idx, c in enumerate(contacts):
        chips = {}

        # Build chips from contact fields
        field_map = {
            'name_prefix': c.name_prefix or '',
            'name_first': c.name_first or '',
            'name_last': c.name_last or '',
            'name_suffix': c.name_suffix or '',
            'title': c.title or '',
            'company': c.company or '',
            'department': c.department or '',
            'email': c.email or '',
        }

        for field, val in field_map.items():
            if val:
                chip_id += 1
                chips[field] = {
                    'id': chip_id, 'text': val,
                    'confidence': 1.0, 'source': 'database',
                }

        # Phone
        try:
            from apps.communications.models.phone import Phone
            phone = Phone.objects.filter(contact_id=c.id).order_by('id').first()
            if phone and phone.number:
                chip_id += 1
                chips['phone'] = {
                    'id': chip_id, 'text': phone.number,
                    'confidence': 1.0, 'source': 'database',
                }
        except Exception:
            pass

        # Address
        try:
            from apps.communications.models.address import Address
            addr = Address.objects.filter(contact_id=c.id).order_by('id').first()
            if addr:
                for af, av in [
                    ('address1', addr.address1), ('address2', addr.address2),
                    ('city', addr.city), ('state', addr.state),
                    ('zip', addr.zip), ('country', addr.country),
                ]:
                    if av:
                        chip_id += 1
                        chips[af] = {
                            'id': chip_id, 'text': av,
                            'confidence': 1.0, 'source': 'database',
                        }
        except Exception:
            pass

        rows.append({
            'row': idx + 1,
            'contact_id': c.id,
            'chips': chips,
            'unassigned': [],
            'matches': [],
        })

    # Score cross-row duplicates
    duplicate_scores = _score_cross_duplicates(rows)

    return {
        'columns': COLUMNS,
        'rows': rows,
        'duplicate_scores': duplicate_scores,
    }


def _score_cross_duplicates(rows: list[dict]) -> list[dict[str, Any]]:
    """Score pairs of rows for potential duplicates.

    Returns list of {row_a, row_b, score, reasons} sorted by score desc.
    Only includes pairs with score > 0.3.
    """
    scores = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            score, reasons = _pair_score(rows[i], rows[j])
            if score > 0.3:
                scores.append({
                    'row_a': i,
                    'row_b': j,
                    'contact_a': rows[i].get('contact_id'),
                    'contact_b': rows[j].get('contact_id'),
                    'score': round(score, 2),
                    'reasons': reasons,
                })
    scores.sort(key=lambda s: -s['score'])
    return scores


def _pair_score(row_a: dict, row_b: dict) -> tuple[float, list[str]]:
    """Score how likely two rows are duplicates. Returns (0.0-1.0, reasons)."""
    chips_a = row_a.get('chips', {})
    chips_b = row_b.get('chips', {})
    score = 0.0
    reasons = []

    def _val(chips, field):
        return (chips.get(field, {}).get('text', '') or '').lower().strip()

    # Email match — strongest signal
    ea, eb = _val(chips_a, 'email'), _val(chips_b, 'email')
    if ea and eb:
        if ea == eb:
            score += 0.50
            reasons.append('same email')
        elif ea.split('@')[1:] == eb.split('@')[1:]:
            score += 0.10
            reasons.append('same email domain')

    # Name match
    fa, fb = _val(chips_a, 'name_first'), _val(chips_b, 'name_first')
    la, lb = _val(chips_a, 'name_last'), _val(chips_b, 'name_last')
    if la and lb and la == lb:
        score += 0.20
        reasons.append('same last name')
        if fa and fb and fa == fb:
            score += 0.15
            reasons.append('same first name')
        elif fa and fb and (fa in fb or fb in fa):
            score += 0.08
            reasons.append('similar first name')

    # Phone match
    pa, pb = _val(chips_a, 'phone'), _val(chips_b, 'phone')
    if pa and pb:
        da = re.sub(r'\D', '', pa)
        db = re.sub(r'\D', '', pb)
        if da and db and da == db:
            score += 0.30
            reasons.append('same phone')

    # Company match
    ca, cb = _val(chips_a, 'company'), _val(chips_b, 'company')
    if ca and cb:
        if ca == cb:
            score += 0.10
            reasons.append('same company')
        elif ca in cb or cb in ca:
            score += 0.05
            reasons.append('similar company')

    # Address match
    aa, ab = _val(chips_a, 'address1'), _val(chips_b, 'address1')
    if aa and ab and aa == ab:
        score += 0.10
        reasons.append('same address')

    return min(score, 1.0), reasons


# ── Backup Cleanup (Alice nightly) ───────────────────────────────────

def clean_merge_backups(max_age_hours: int = 24, dry_run: bool = False) -> dict[str, Any]:
    """Remove config.backup entries older than max_age_hours.

    Called by Alice nightly. Backups are a safety net for accidental merges,
    not permanent storage. One day is enough time to catch a mistake.

    Returns {'cleaned': N, 'skipped': N}.
    """
    import datetime
    from apps.core.models.contact import Contact

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=max_age_hours)
    cutoff_iso = cutoff.isoformat()

    # Find contacts with config.backup
    contacts = Contact.objects.filter(
        config__has_key='backup',
    ).exclude(config__backup={})

    cleaned = 0
    skipped = 0

    for c in contacts.iterator(chunk_size=100):
        config = c.config or {}
        backup = config.get('backup', {})
        dt_backup = backup.get('dt_backup', '')

        if not dt_backup:
            # No timestamp — clean it (legacy)
            if not dry_run:
                del config['backup']
                c.config = config
                c._setting_update_authorized = True
                c.save(update_fields=['config'])
            cleaned += 1
            continue

        if dt_backup < cutoff_iso:
            if not dry_run:
                del config['backup']
                c.config = config
                c.save(update_fields=['config'])
            cleaned += 1
        else:
            skipped += 1

    logger.info('Merge backup cleanup: %d cleaned, %d skipped (< %dh old)',
                cleaned, skipped, max_age_hours)
    return {'cleaned': cleaned, 'skipped': skipped}


# ── Alice Episode Logging ────────────────────────────────────────────

def log_import_episode(result: dict[str, Any], source_label: str = '') -> None:
    """Log an import batch as an Alice episode.

    Called after parsing completes. Creates an episode record that Alice
    can recall when a similar import pattern appears later.

    Over time, Alice learns:
    - What sources produce what column layouts
    - Which columns are commonly unmapped
    - What corrections users make on data from each source
    - Typical duplicate rates per source
    """
    try:
        from apps.ai_assistant.models.alice import AliceObservation

        rows = result.get('rows', [])
        if not rows:
            return

        mode = result.get('mode', 'free_form')
        delimiter = result.get('detected_delimiter', '')
        detection = result.get('_detection', {})
        no_header = result.get('_no_header', False)
        warning = result.get('_warning', '')

        # Gather stats
        total_rows = len(rows)
        total_matches = sum(1 for r in rows if r.get('matches'))
        total_unassigned = sum(len(r.get('unassigned', [])) for r in rows)
        has_userdefined = sum(1 for r in rows if r.get('_userdefined'))

        # Column summary
        mapped_fields = detection.get('mapped_fields', []) if detection else []
        unmapped_fields = detection.get('unmapped_fields', []) if detection else []
        columns_detected = detection.get('columns', []) if detection else []

        # Header fingerprint — the column headers in order (for source recognition)
        header_fingerprint = '|'.join(
            c.get('header', '') for c in columns_detected
        ) if columns_detected else ''

        # Build narrative
        parts = [f'Import batch: {total_rows} contacts parsed.']
        if mode == 'structured':
            delim_name = {'\\t': 'tab', ',': 'comma', '|': 'pipe'}.get(delimiter, delimiter)
            parts.append(f'Structured data detected ({delim_name} delimited).')
            if detection:
                parts.append(f'Header found at row {detection.get("header_row", 0)}.')
                parts.append(f'Skipped {detection.get("skipped_rows", 0)} noise rows.')
                parts.append(f'{len(mapped_fields)} columns mapped: {", ".join(mapped_fields)}.')
                if unmapped_fields:
                    labels = [f.lstrip("_").replace("_", " ") for f in unmapped_fields]
                    parts.append(f'{len(unmapped_fields)} unmapped → userdefined: {", ".join(labels)}.')
        elif mode == 'structured_no_header':
            parts.append('Structured but NO header row. Fields guessed from content.')
        else:
            parts.append('Free-form text parsed (not tabular).')

        if no_header:
            parts.append('WARNING: No header row detected.')
        if warning:
            parts.append(f'Warning: {warning}')

        parts.append(f'{total_matches} contacts matched existing records.')
        parts.append(f'{total_unassigned} values unassigned (in staging).')
        if has_userdefined:
            parts.append(f'{has_userdefined} rows have userdefined data.')

        if source_label:
            parts.append(f'Source label: {source_label}')

        narrative = ' '.join(parts)

        # Determine principle
        if no_header:
            principle = 'Headerless structured data requires content-based guessing. Ask user to confirm field mapping.'
        elif unmapped_fields:
            unmapped_str = ', '.join(f.lstrip('_').replace('_', ' ') for f in unmapped_fields)
            principle = f'Source has columns not in WC3 schema ({unmapped_str}). Save to prefs.userdefined.'
        elif total_matches > total_rows * 0.5:
            principle = f'High duplicate rate ({total_matches}/{total_rows}). Source likely re-exports existing contacts.'
        else:
            principle = 'Clean import — most contacts are new.'

        # Create episode via AliceObservation (lightweight — no MCP dependency)
        AliceObservation.objects.create(
            category='pattern',
            source='alice',
            priority=0,
            message=f'Import: {total_rows} contacts, {mode}, {len(mapped_fields)} mapped',
            detail=narrative,
            model_name='contact_import',
            config={
                'episode_type': 'import_batch',
                'mode': mode,
                'delimiter': delimiter,
                'header_fingerprint': header_fingerprint,
                'total_rows': total_rows,
                'total_matches': total_matches,
                'total_unassigned': total_unassigned,
                'mapped_fields': mapped_fields,
                'unmapped_fields': unmapped_fields,
                'has_userdefined': has_userdefined,
                'no_header': no_header,
                'source_label': source_label,
                'principle': principle,
            },
            dedup_key=f'import-{header_fingerprint[:100]}-{total_rows}' if header_fingerprint else '',
        )

        logger.info('Import episode logged: %d rows, mode=%s, %d mapped, %d unmapped',
                     total_rows, mode, len(mapped_fields), len(unmapped_fields))

    except Exception:
        logger.warning('Failed to log import episode', exc_info=True)


def recall_import_pattern(header_fingerprint: str = '', delimiter: str = '',
                           column_headers: list[str] | None = None) -> dict[str, Any] | None:
    """Recall a previous import that had a similar column pattern.

    Alice uses this to pre-map columns when she recognizes the source.
    Returns the previous episode's config (including column_map) or None.
    """
    try:
        from apps.ai_assistant.models.alice import AliceObservation

        # Try exact fingerprint match first
        if header_fingerprint:
            episode = AliceObservation.objects.filter(
                category='pattern',
                model_name='contact_import',
                config__header_fingerprint=header_fingerprint,
            ).order_by('-dt_created').first()
            if episode:
                return episode.config

        # Try fuzzy match on column headers
        if column_headers:
            # Search for episodes that mapped similar headers
            candidates = AliceObservation.objects.filter(
                category='pattern',
                model_name='contact_import',
            ).order_by('-dt_created')[:20]

            best_match = None
            best_score = 0
            for c in candidates:
                config = c.config or {}
                prev_fp = config.get('header_fingerprint', '')
                if not prev_fp:
                    continue
                prev_headers = prev_fp.split('|')
                # Score by overlap
                overlap = len(set(h.lower() for h in column_headers) & set(h.lower() for h in prev_headers))
                score = overlap / max(len(column_headers), len(prev_headers), 1)
                if score > best_score and score > 0.5:
                    best_score = score
                    best_match = config

            return best_match

    except Exception:
        logger.debug('Failed to recall import pattern', exc_info=True)

    return None


def record_field_correction(
    text: str,
    original_field: str,
    corrected_field: str,
    user_id: int | None = None,
) -> None:
    """Record a chip drag as a Small-Sting. Alice learns the mapping."""
    try:
        from apps.ai_assistant.models.alice import AliceObservation

        AliceObservation.objects.update_or_create(
            category='pii_correction',
            model_name='contact_parser',
            dedup_key=f'cp-{text.lower()}-{corrected_field}',
            defaults={
                'source': 'alice',
                'priority': 0,
                'message': f'Field correction: "{text}" → {corrected_field}',
                'config': {
                    'action': 'field_correction',
                    'text': text,
                    'original_field': original_field,
                    'corrected_field': corrected_field,
                },
                'contact_id': user_id,
            },
        )
    except Exception:
        logger.warning('Failed to record field correction', exc_info=True)
