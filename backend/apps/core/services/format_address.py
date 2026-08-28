"""Address formatting and validation service.

Client-side formats for display preview. Server-side is authoritative:
  1. Format address_full from components using destination country template
  2. Optionally validate via external API (USPS CASS, Google Geocoding)
  3. Standardize abbreviations (St→Street, Apt→Apartment)
  4. Add ZIP+4 for US addresses (if USPS configured)

Validation provider configured via Setting: purpose=wc:system, name=address_validation
  config: { provider: "none"|"usps"|"google", api_key: "...", auto_correct: true }
"""
import logging
import re

logger = logging.getLogger(__name__)

# ── Country address templates ────────────────────────────────────────
# Template tokens: {a1}=address1, {a2}=address2, {city}, {state}, {zip}, {country}
# Format follows UPU (Universal Postal Union) conventions per country.

TEMPLATES = {
    'US': '{a1}\n{a2}\n{city}, {state} {zip}',
    'CA': '{a1}\n{a2}\n{city} {state} {zip}',
    'GB': '{a1}\n{a2}\n{city}\n{zip}',
    'UK': '{a1}\n{a2}\n{city}\n{zip}',
    'AU': '{a1}\n{a2}\n{city} {state} {zip}',
    'DE': '{a1}\n{a2}\n{zip} {city}',
    'FR': '{a1}\n{a2}\n{zip} {city}',
    'IT': '{a1}\n{a2}\n{zip} {city} {state}',
    'ES': '{a1}\n{a2}\n{zip} {city}',
    'NL': '{a1}\n{a2}\n{zip} {city}',
    'JP': '〒{zip}\n{state} {city}\n{a1}\n{a2}',
    'CN': '{zip}\n{state} {city}\n{a1}\n{a2}',
    'IN': '{a1}\n{a2}\n{city} {zip}\n{state}',
    'BR': '{a1}\n{a2}\n{city}-{state}\n{zip}',
    'MX': '{a1}\n{a2}\n{zip} {city}, {state}',
    'ZA': '{a1}\n{a2}\n{city}\n{state}\n{zip}',
    'CH': '{a1}\n{a2}\n{zip} {city}',
    'SE': '{a1}\n{a2}\n{zip} {city}',
    'NZ': '{a1}\n{a2}\n{city} {zip}',
    'KR': '{state} {city}\n{a1}\n{a2}\n{zip}',
}

DEFAULT_TEMPLATE = '{a1}\n{a2}\n{city}, {state} {zip}'

# US abbreviation standardization (USPS Publication 28)
US_ABBREVS = {
    'street': 'St', 'st': 'St', 'str': 'St',
    'avenue': 'Ave', 'ave': 'Ave', 'av': 'Ave',
    'boulevard': 'Blvd', 'blvd': 'Blvd',
    'drive': 'Dr', 'dr': 'Dr', 'drv': 'Dr',
    'lane': 'Ln', 'ln': 'Ln',
    'road': 'Rd', 'rd': 'Rd',
    'court': 'Ct', 'ct': 'Ct',
    'circle': 'Cir', 'cir': 'Cir',
    'place': 'Pl', 'pl': 'Pl',
    'terrace': 'Ter', 'ter': 'Ter',
    'trail': 'Trl', 'trl': 'Trl',
    'way': 'Way',
    'highway': 'Hwy', 'hwy': 'Hwy',
    'parkway': 'Pkwy', 'pkwy': 'Pkwy',
    'apartment': 'Apt', 'apt': 'Apt',
    'suite': 'Ste', 'ste': 'Ste',
    'unit': 'Unit',
    'building': 'Bldg', 'bldg': 'Bldg',
    'floor': 'Fl', 'fl': 'Fl',
    'room': 'Rm', 'rm': 'Rm',
    'north': 'N', 'south': 'S', 'east': 'E', 'west': 'W',
    'northeast': 'NE', 'northwest': 'NW', 'southeast': 'SE', 'southwest': 'SW',
}

US_STATES = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
    'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
    'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
    'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
    'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
    'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
    'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
    'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
    'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
    'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
    'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC',
}


def format_address(address1='', address2='', city='', state='', zip_code='',
                   country='US', zip='', **_kwargs) -> str:
    # Accept both zip_code and zip (standardize_us_address returns 'zip')
    zip_code = zip_code or zip
    """Format address components using destination country's postal template.

    Returns multi-line formatted address. Use .replace('\\n', ', ') for single-line.
    """
    cc = (country or 'US').upper()
    template = TEMPLATES.get(cc, DEFAULT_TEMPLATE)

    result = template.format(
        a1=address1 or '',
        a2=address2 or '',
        city=city or '',
        state=state or '',
        zip=zip_code or '',
    )

    # Clean up: remove empty lines, collapse whitespace
    lines = [re.sub(r'\s+', ' ', line).strip() for line in result.split('\n')]
    lines = [line.strip(',').strip() for line in lines if line.strip(',').strip()]
    return '\n'.join(lines)


def format_address_full(address1='', address2='', city='', state='', zip_code='',
                        country='US', zip='', **_kwargs) -> str:
    zip_code = zip_code or zip
    """Format as single-line address_full for storage and search."""
    return format_address(address1, address2, city, state, zip_code, country).replace('\n', ', ')


def standardize_us_address(address1='', address2='', city='', state='', zip_code='', **_kwargs):
    """Standardize US address abbreviations per USPS Publication 28.

    Returns dict with corrected fields.
    """
    def _std_line(line):
        if not line:
            return line
        words = line.split()
        result = []
        for w in words:
            lower = w.lower().rstrip('.,')
            if lower in US_ABBREVS:
                result.append(US_ABBREVS[lower])
            else:
                # Preserve original case, title-case if all lower
                result.append(w.title() if w == w.lower() and w.isalpha() else w)
        return ' '.join(result)

    # Standardize state name → abbreviation
    std_state = state
    if state and len(state) > 2:
        lower = state.lower().strip()
        if lower in US_STATES:
            std_state = US_STATES[lower]

    # Standardize ZIP format — 5 digits, or 5+4 with dash
    std_zip = re.sub(r'[^\d]', '', zip_code or '')
    if len(std_zip) >= 9:
        std_zip = f'{std_zip[:5]}-{std_zip[5:9]}'
    elif len(std_zip) >= 5:
        std_zip = std_zip[:5]
    # Leave shorter zips as-is (partial data)

    return {
        'address1': _std_line(address1),
        'address2': _std_line(address2),
        'city': (city or '').strip().title(),
        'state': std_state.upper() if std_state else '',
        'zip': std_zip,
    }


def validate_and_format(location_record) -> dict:
    """Validate and format a location record.

    Called from the location save signal or manually.
    Returns dict with:
      - corrected fields (address1, address2, city, state, zip)
      - full: formatted single-line address
      - validated: bool (whether external validation was attempted)
      - validation_result: provider response or None
    """
    addr1 = getattr(location_record, 'address1', '') or ''
    addr2 = getattr(location_record, 'address2', '') or ''
    city = getattr(location_record, 'city', '') or ''
    state = getattr(location_record, 'state', '') or ''
    zip_code = getattr(location_record, 'zip', '') or ''
    country = getattr(location_record, 'country', 'US') or 'US'
    cc = country.upper()

    result = {
        'address1': addr1, 'address2': addr2,
        'city': city, 'state': state, 'zip': zip_code,
        'full': '', 'validated': False, 'validation_result': None,
    }

    # Step 1: Standardize (US only for now)
    if cc == 'US':
        std = standardize_us_address(addr1, addr2, city, state, zip_code)
        result.update(std)

    # Step 2: Format full address using country template
    result['full'] = format_address_full(
        result['address1'], result['address2'],
        result['city'], result['state'], result['zip'],
        country=cc,
    )

    # Step 3: External validation (if configured)
    try:
        result = _external_validate(result, cc)
    except Exception as exc:
        logger.debug('Address validation failed: %s', exc)

    return result


def _external_validate(result, country_code):
    """Call external validation API if configured.

    Reads Setting: purpose=wc:system, name=address_validation
    """
    try:
        from apps.core.models import Setting
        setting = Setting.objects.filter(
            purpose='wc:system', name='address_validation'
        ).first()
        if not setting:
            return result

        config = setting.config or {}
        provider = config.get('provider', 'none')
        if provider == 'none':
            return result

        auto_correct = config.get('auto_correct', True)

        if provider == 'usps' and country_code == 'US':
            return _validate_usps(result, config, auto_correct)
        elif provider == 'google':
            return _validate_google(result, config, country_code, auto_correct)
    except Exception:
        pass
    return result


def _validate_usps(result, config, auto_correct):
    """Validate US address via USPS Web Tools API (free, requires registration).

    API: https://secure.shippingapis.com/ShippingAPI.dll
    Registers at: https://www.usps.com/business/web-tools-apis/
    """
    import urllib.request
    import xml.etree.ElementTree as ET

    user_id = config.get('api_key', '')
    if not user_id:
        return result

    xml_req = (
        f'<AddressValidateRequest USERID="{user_id}">'
        f'<Address><Address1>{result["address2"]}</Address1>'
        f'<Address2>{result["address1"]}</Address2>'
        f'<City>{result["city"]}</City>'
        f'<State>{result["state"]}</State>'
        f'<Zip5>{result["zip"][:5]}</Zip5>'
        f'<Zip4></Zip4></Address></AddressValidateRequest>'
    )

    url = f'https://secure.shippingapis.com/ShippingAPI.dll?API=Verify&XML={urllib.request.quote(xml_req)}'
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            tree = ET.fromstring(resp.read())
            addr = tree.find('.//Address')
            if addr is not None and addr.find('Error') is None:
                result['validated'] = True
                result['validation_result'] = {
                    'provider': 'usps',
                    'address1': addr.findtext('Address2', ''),  # USPS swaps 1/2
                    'address2': addr.findtext('Address1', ''),
                    'city': addr.findtext('City', ''),
                    'state': addr.findtext('State', ''),
                    'zip': addr.findtext('Zip5', ''),
                    'zip4': addr.findtext('Zip4', ''),
                }
                if auto_correct:
                    vr = result['validation_result']
                    result['address1'] = vr['address1']
                    result['address2'] = vr['address2']
                    result['city'] = vr['city']
                    result['state'] = vr['state']
                    zip_full = vr['zip']
                    if vr.get('zip4'):
                        zip_full += f'-{vr["zip4"]}'
                    result['zip'] = zip_full
                    result['full'] = format_address_full(
                        result['address1'], result['address2'],
                        result['city'], result['state'], result['zip'],
                        country='US',
                    )
            else:
                error = addr.find('Error') if addr is not None else tree.find('.//Error')
                result['validation_result'] = {
                    'provider': 'usps',
                    'error': error.findtext('Description', 'Unknown error') if error is not None else 'No address returned',
                }
    except Exception as exc:
        result['validation_result'] = {'provider': 'usps', 'error': str(exc)[:200]}

    return result


def _validate_google(result, config, country_code, auto_correct):
    """Validate address via Google Address Validation API.

    API: https://addressvalidation.googleapis.com/v1:validateAddress
    """
    import json
    import urllib.request

    api_key = config.get('api_key', '')
    if not api_key:
        return result

    payload = json.dumps({
        'address': {
            'regionCode': country_code,
            'addressLines': [
                result['address1'],
                result.get('address2', ''),
                f"{result['city']}, {result['state']} {result['zip']}",
            ],
        },
    }).encode()

    req = urllib.request.Request(
        f'https://addressvalidation.googleapis.com/v1:validateAddress?key={api_key}',
        data=payload,
        headers={'Content-Type': 'application/json'},
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            verdict = data.get('result', {}).get('verdict', {})
            result['validated'] = True
            result['validation_result'] = {
                'provider': 'google',
                'granularity': verdict.get('geocodeGranularity', ''),
                'has_unconfirmed': verdict.get('hasUnconfirmedComponents', False),
                'formatted': data.get('result', {}).get('address', {}).get('formattedAddress', ''),
            }
            if auto_correct and result['validation_result'].get('formatted'):
                result['full'] = result['validation_result']['formatted']
    except Exception as exc:
        result['validation_result'] = {'provider': 'google', 'error': str(exc)[:200]}

    return result
