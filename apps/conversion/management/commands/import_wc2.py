"""
Management command — WC2 (4D) to WC3 data converter.

Reads a folder of JSON files exported by 19Convert_ExportAllData() in 4D
and creates WC3 records. The field mappings are hardcoded because the WC2
schema is known and consistent across all installations.

Usage:
  # Discover: inventory all tables, record counts, audit baseline
  python manage.py import_wc2 discover /path/to/dump/

  # Audit: compute financial checksums from the raw dump
  python manage.py import_wc2 audit /path/to/dump/

  # Import: convert and load data into the current WC3 database
  python manage.py import_wc2 import /path/to/dump/ --dry-run
  python manage.py import_wc2 import /path/to/dump/

  # Verify: compare WC3 totals against the original dump audit
  python manage.py import_wc2 verify /path/to/dump/

Technical notes:
  - All WC2 JSON files have UTF-8 BOM — read with encoding='utf-8-sig'
  - WC2 used plural table names historically, then switched to singular.
    The Ledger table contains both 'Invoice'/'Invoices' and 'Payment'/'Payments'.
    This converter normalizes all to singular.
  - WC2 customerID is the natural key linking Customer, Contact, Order,
    Invoice, Payment, and Ledger tables.
  - WC2 idNum is the document number on transactions.
  - WC2 itemNum is the natural key for items.
"""

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


# ── Helpers ──────────────────────────────────────────────────────────────

def load_wc2(folder, table_name):
    """Load a WC2 JSON file with UTF-8 BOM handling."""
    path = Path(folder) / f"{table_name}.json"
    if not path.exists():
        return []
    with open(path, encoding='utf-8-sig') as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def safe_str(val, max_len=None):
    """Convert to string, strip null bytes and control chars, optionally truncate."""
    if val is None:
        return ''
    s = str(val)
    # Strip null bytes and control characters that PostgreSQL JSONB rejects
    s = s.replace('\x00', '').replace('\u0000', '')
    # Remove other non-printable control chars (keep \n \r \t)
    s = ''.join(c for c in s if c in ('\n', '\r', '\t') or (ord(c) >= 32))
    s = s.strip()
    if max_len:
        s = s[:max_len]
    return s


def safe_decimal(val, default=Decimal('0')):
    """Convert to Decimal safely."""
    if val is None or val == '':
        return default
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError):
        return default


def safe_float(val, default=0.0):
    if val is None or val == '':
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0):
    if val is None or val == '':
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def safe_bool(val, default=False):
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val != 0
    s = str(val).lower().strip()
    return s in ('true', '1', 'yes', 'y')


def wc2_date_to_epoch_ms(val):
    """Convert WC2 date string to UTC epoch milliseconds.
    WC2 dates come as 'YYYY-MM-DD' or 'MM/DD/YYYY' or epoch or empty.
    Returns 0 if unparseable.
    """
    if not val or val == '0' or val == 0:
        return 0
    if isinstance(val, (int, float)) and val > 946684800:
        # Already epoch seconds — convert to ms
        return int(val * 1000)
    s = str(val).strip()
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%dT%H:%M:%S', '%m/%d/%y'):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    # Try ISO format
    try:
        dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
        return int(dt.timestamp() * 1000)
    except (ValueError, TypeError):
        return 0


def now_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def build_config(wc2_row, extract_keys=None, exclude_keys=None):
    """Build config dict with named extractions.

    Extracts meaningful WC2 fields into named config keys so Alice can
    observe which are useful vs junk over time. Profiles get their own
    sub-dict. The entire original row is always preserved in config.original.

    Args:
        wc2_row: The raw WC2 record dict.
        extract_keys: Dict of {config_key: wc2_field_name} to extract.
            e.g. {'rep': 'repID', 'division': 'division'}
        exclude_keys: Set of keys to exclude from config.original.
    """
    exclude = exclude_keys or set()
    original = {}
    for k, v in wc2_row.items():
        if k in exclude or v in (None, '', 0, False, [], {}):
            continue
        # Sanitize strings for PostgreSQL JSONB (no null bytes)
        if isinstance(v, str):
            v = v.replace('\x00', '').replace('\u0000', '')
            v = ''.join(c for c in v if c in ('\n', '\r', '\t') or (ord(c) >= 32))
            if not v:
                continue
        original[k] = v

    config = {}

    def _sanitize(v):
        """Strip null bytes and control chars from any value going into JSONB."""
        if isinstance(v, str):
            v = v.replace('\x00', '').replace('\u0000', '')
            v = ''.join(c for c in v if c in ('\n', '\r', '\t') or (ord(c) >= 32))
            return v if v else None
        if isinstance(v, dict):
            return {k: _sanitize(vv) for k, vv in v.items() if _sanitize(vv) is not None}
        if isinstance(v, list):
            return [_sanitize(vv) for vv in v if _sanitize(vv) is not None]
        return v

    # Extract profile fields into config.profiles
    profiles = {}
    for i in range(1, 8):
        key = f'profile{i}'
        val = _sanitize(wc2_row.get(key))
        if val not in (None, '', 0):
            profiles[str(i)] = val
    if profiles:
        config['profiles'] = profiles

    # Extract named fields — Alice watches which are useful over time
    if extract_keys:
        for config_key, wc2_field in extract_keys.items():
            val = _sanitize(wc2_row.get(wc2_field))
            if val not in (None, '', 0):
                config[config_key] = val

    # Original always last — full preservation
    config['original'] = original
    return config


# Named field extractions per WC2 table.
# These surface meaningful WC2 fields as named config keys.
# Alice observes which get used vs ignored and learns over time.

CUSTOMER_EXTRACT = {
    'rep': 'repID',
    'sales_name': 'salesNameID',
    'ad_source': 'adSource',
    'zone': 'zone',
    'division': 'division',
    'sic_code': 'sICCode',
    'ship_via': 'shipVia',
    'ship_instructions': 'shipInstruct',
    'territory': 'territoryid',
    'duns': 'dunsNumber',
    'sector': 'sector',
}

VENDOR_EXTRACT = {
    'sic_code': 'sICCode',
    'division': 'division',
    'ship_via': 'shipVia',
    'ship_instructions': 'shipInstruct',
    'zone': 'zone',
    'buyer': 'buyer',
    'duns': 'dunsNumber',
    'customer_id_at_vendor': 'customerIDAtVend',
}

ITEM_EXTRACT = {
    'mfr_item_num': 'mfrItemNum',
    'vendor_item_num': 'vendorItemNum',
    'bar_code': 'barCode',
    'type': 'type',
    'class': 'class',
    'division': 'division',
    'spec_id': 'specid',
    'mfr_name': 'mfrName',
    'location': 'location',
    'location_bin': 'locationBin',
    'storage_location': 'storageLocation',
    'hazard_class': 'hazardClassification',
    'lead_time_sales': 'leadTimeSales',
    'lead_time_po': 'leadTimePo',
    'warranty_days': 'warrantyDays',
}

TRANSACTION_EXTRACT = {
    'customer_po': 'customerPO',
    'division': 'division',
    'doc_type': 'docType',
    'doc_reference': 'docReference',
    'ad_source': 'adSource',
    'rep': 'repID',
    'sales_name': 'salesNameID',
    'fob': 'fob',
    'exchange_rate': 'exchangeRate',
    'currency': 'currency',
}

PAYMENT_EXTRACT = {
    'payment_type': 'typePayment',
    'check_num': 'checkNum',
    'bank_deposit': 'bankDeposit',
    'bank_from': 'bankFrom',
    'deposit_account': 'depositAccount',
    'tender_class': 'tenderClass',
    'division': 'division',
    'batch_id': 'batchid',
}


# ── Mapping Tables ──────────────────────────────────────────────────────

# Tables to skip during import (system, cache, utility)
SKIP_TABLES = {
    'TallyResult', 'TallySummary', 'TallyChange', 'TallyMaster',
    'CashD', 'CashJournal', 'SalesJournal', 'PurchaseJournal',
    'zzzWord', 'zzzTrackKeyField', 'zzzCarrierWeight', 'zzzCarrierZone',
    'zzzWebTempRec', 'zzzSyncJob', 'zzzSyncMap', 'zzzCommunicationDevice',
    'zzzDialingInfo', 'zzzEDISetID', 'zzzFieldConfig', 'zzzGenericChild1',
    'zzzGenericChild2', 'zzzGenericPC1', 'zzzGenericPC2', 'zzzHistoricalRecord',
    'zzzHoliday', 'zzzLogReport', 'zzzManufacturerTerm', 'zzzRepContact',
    'zzzTemplateline', 'zzzTempRec', 'zzzUUIDConnection', 'zzzWorkOrderEvent',
    'zzzWOTemplate', 'zzzWOTemplateTask', 'zzzzDSync',
    'EventLog', 'Log', 'CounterPending', 'Counter', 'Archive',
    'FC', 'SyncRecord', 'SyncRelation', 'ZipCode', 'PopUp', 'PopupChoice',
    'Menu', 'Script', 'Template', 'CronJob', 'Admin', 'DefaultSetup',
    'DivisionDefault', 'Default', 'DefaultAccount', 'WebClerk', 'WebClerkDevice',
    'Map', 'Generic', 'Process', 'Profile', 'Forum', 'Discussion', 'Letter',
    'Marketing', 'Message', 'Objective', 'Result', 'Time', 'TimeAvailable',
    'RemoteUser', 'zzzChangeLog',
}

# Core tables and their import order (dependencies first)
IMPORT_ORDER = [
    'GLAccount',
    'Customer',    # → OrgBase (org_type=customer)
    'Vendor',      # → OrgBase (org_type=vendor)
    'Rep',         # → OrgBase (org_type=rep)
    'Employee',    # → OrgBase (org_type=employee) — skip if empty
    'Contact',     # → Contact (linked to OrgBase via customerID)
    'Item',        # → Item
    'Proposal',    # → Proposal header
    'ProposalLine',
    'Order',       # → Order header
    'OrderLine',
    'Invoice',     # → Invoice header
    'InvoiceLine',
    'PO',          # → Purchase header
    'POLine',      # → PurchaseLine
    'Payment',     # → Payment
    'Ledger',      # → LedgerEntry
]


# ── Converters (one function per WC2 table) ──────────────────────────────

def convert_gl_accounts(wc2_rows, stats, dry_run=False):
    """GLAccount → apps.accounts.models.GLAccount"""
    from apps.accounts.models import GlAccount
    created = 0
    for row in wc2_rows:
        account = safe_str(row.get('account'), 20)
        if not account:
            continue
        defaults = {
            'name': safe_str(row.get('name'), 200),
            'type': safe_str(row.get('typeAcct'), 50),
            'ida': account,
            'config': build_config(row),
            'is_active': True,
        }
        if not dry_run:
            obj, was_created = GlAccount.objects.update_or_create(
                ida=account, defaults=defaults
            )
            if was_created:
                created += 1
        else:
            created += 1
    stats['GLAccount'] = {'total': len(wc2_rows), 'created': created}


def convert_customers(wc2_rows, lookup, stats, dry_run=False):
    """Customer → OrgBase (org_type='customer')"""
    from apps.orgs.models import OrgBase
    created = 0
    for row in wc2_rows:
        cid = safe_str(row.get('customerID'))
        company = safe_str(row.get('company'), 255)
        if not cid:
            continue
        # Build financial snapshot from WC2 aging fields
        financial = {
            'credit': {
                'limit': safe_float(row.get('creditLimit')),
                'used': safe_float(row.get('highCredit')),
                'approved': safe_str(row.get('creditApproval')),
            },
            'aging': {
                'current': safe_float(row.get('balanceCurrent')),
                'period_1': safe_float(row.get('balPastPeriod1')),
                'period_2': safe_float(row.get('balPastPeriod2')),
                'period_3': safe_float(row.get('balPastPeriod3')),
                'balance_due': safe_float(row.get('balanceDue')),
                'future_due': safe_float(row.get('futureDue')),
            },
            'sales': {
                'mtd': safe_float(row.get('salesMTD')),
                'ytd': safe_float(row.get('salesYTD')),
                'last_yr': safe_float(row.get('salesLastYr')),
                'all_time': safe_float(row.get('salesAllTime')),
                'last_date': safe_str(row.get('lastSaleDate')),
                'last_amount': safe_float(row.get('lastSaleAmount')),
            },
            'payments': {
                'last_date': safe_str(row.get('lastPayDate')),
                'last_amount': safe_float(row.get('lastPayAmount')),
                'days_avg_paid': safe_float(row.get('daysAvgPaid')),
            },
            'costs': {
                'mtd': safe_float(row.get('costsMTD')),
                'ytd': safe_float(row.get('costsYTD')),
                'all_time': safe_float(row.get('costsAllTime')),
            },
        }
        defaults = {
            'display_name': company or cid,
            'org_type': 'customer',
            'status': 'retired' if row.get('dateRetired') else 'active',
            'ida': cid,
            'phone': safe_str(row.get('phone'), 50),
            'email': safe_str(row.get('email'), 254) or None,
            'address_full': ', '.join(filter(None, [
                safe_str(row.get('address1')),
                safe_str(row.get('address2')),
                safe_str(row.get('city')),
                safe_str(row.get('state')),
                safe_str(row.get('zip')),
            ])) or None,
            'domain': safe_str(row.get('domain'), 255) or None,
            'terms': safe_str(row.get('terms'), 30) or None,
            'price_level': safe_str(row.get('typeSale'), 30) or None,
            'financial': financial,
            'config': build_config(row, extract_keys=CUSTOMER_EXTRACT),
            'is_active': not bool(row.get('dateRetired')),
            'tax_exempt_code': safe_str(row.get('taxExemptid'), 80),
        }
        if not dry_run:
            obj, was_created = OrgBase.objects.update_or_create(
                ida=cid, org_type='customer', defaults=defaults
            )
            if was_created:
                created += 1
            lookup['customer'][cid] = obj.pk
        else:
            created += 1
    stats['Customer'] = {'total': len(wc2_rows), 'created': created}


def convert_vendors(wc2_rows, lookup, stats, dry_run=False):
    """Vendor → OrgBase (org_type='vendor')"""
    from apps.orgs.models import OrgBase
    created = 0
    for row in wc2_rows:
        vid = safe_str(row.get('vendorID'))
        company = safe_str(row.get('company'), 255)
        if not vid:
            continue
        financial = {
            'payables': {
                'total_due': safe_float(row.get('totalDue')),
                'ytd_purchases': safe_float(row.get('ytdPurchases')),
                'last_yr_purchases': safe_float(row.get('lYPurchases')),
                'last_purchase_date': safe_str(row.get('dateLastPur')),
                'last_purchase_amount': safe_float(row.get('amountLastPur')),
                'last_payment_date': safe_str(row.get('dateLastPayment')),
                'last_payment_amount': safe_float(row.get('amountLastPay')),
            },
            'credit': {
                'limit': safe_float(row.get('creditLimit')),
                'high': safe_float(row.get('highCredit')),
            },
        }
        defaults = {
            'display_name': company or vid,
            'org_type': 'vendor',
            'status': 'retired' if row.get('dateRetired') else 'active',
            'ida': vid,
            'phone': safe_str(row.get('phone'), 50),
            'email': safe_str(row.get('email'), 254) or None,
            'address_full': ', '.join(filter(None, [
                safe_str(row.get('address1')),
                safe_str(row.get('address2')),
                safe_str(row.get('city')),
                safe_str(row.get('state')),
                safe_str(row.get('zip')),
            ])) or None,
            'domain': safe_str(row.get('domain'), 255) or None,
            'terms': safe_str(row.get('terms'), 30) or None,
            'financial': financial,
            'config': build_config(row, extract_keys=VENDOR_EXTRACT),
            'is_active': not bool(row.get('dateRetired')),
        }
        if not dry_run:
            obj, was_created = OrgBase.objects.update_or_create(
                ida=vid, org_type='vendor', defaults=defaults
            )
            if was_created:
                created += 1
            lookup['vendor'][vid] = obj.pk
        else:
            created += 1
    stats['Vendor'] = {'total': len(wc2_rows), 'created': created}


def convert_reps(wc2_rows, lookup, stats, dry_run=False):
    """Rep → OrgBase (org_type='rep')"""
    from apps.orgs.models import OrgBase
    created = 0
    for row in wc2_rows:
        rid = safe_str(row.get('repID') or row.get('idNum'))
        name = safe_str(row.get('company') or row.get('nameFirst', '') + ' ' + safe_str(row.get('nameLast', '')), 255).strip()
        if not rid:
            continue
        defaults = {
            'display_name': name or rid,
            'org_type': 'rep',
            'ida': rid,
            'phone': safe_str(row.get('phone'), 50),
            'email': safe_str(row.get('email'), 254) or None,
            'config': build_config(row),
            'is_active': True,
        }
        if not dry_run:
            obj, was_created = OrgBase.objects.update_or_create(
                ida=rid, org_type='rep', defaults=defaults
            )
            if was_created:
                created += 1
            lookup['rep'][rid] = obj.pk
        else:
            created += 1
    stats['Rep'] = {'total': len(wc2_rows), 'created': created}


def convert_contacts(wc2_rows, lookup, stats, dry_run=False):
    """Contact → core.Contact (linked to customer OrgBase)"""
    from apps.core.models import Contact
    created = 0
    for row in wc2_rows:
        cid = safe_str(row.get('customerID'))
        email = safe_str(row.get('email') or row.get('emailAddress'), 254) or None
        name_first = safe_str(row.get('nameFirst'), 100)
        name_last = safe_str(row.get('nameLast'), 100)
        if not name_first and not name_last and not email:
            continue
        # Find linked customer org
        customer_pk = lookup['customer'].get(cid) if cid else None
        defaults = {
            'name_first': name_first,
            'name_last': name_last,
            'name_middle': safe_str(row.get('nameMiddle'), 100),
            'name_prefix': safe_str(row.get('title'), 20),
            'phone': safe_str(row.get('phone'), 50) or None,
            'company': safe_str(row.get('company'), 200),
            'title': safe_str(row.get('title'), 100),
            'address_full': ', '.join(filter(None, [
                safe_str(row.get('address1')),
                safe_str(row.get('address2')),
                safe_str(row.get('city')),
                safe_str(row.get('state')),
                safe_str(row.get('zip')),
            ])) or None,
            'customer_id': customer_pk,
            'is_active': True,
            'config': build_config(row),
        }
        if not dry_run:
            if email:
                obj, was_created = Contact.objects.update_or_create(
                    email=email, defaults=defaults
                )
            else:
                # No email — create without dedup
                obj = Contact.objects.create(email=None, **defaults)
                was_created = True
            if was_created:
                created += 1
        else:
            created += 1
    stats['Contact'] = {'total': len(wc2_rows), 'created': created}


def convert_items(wc2_rows, lookup, stats, dry_run=False):
    """Item → products.Item"""
    from apps.products.models import Item
    created = 0
    for row in wc2_rows:
        item_num = safe_str(row.get('itemNum'), 80)
        if not item_num:
            continue
        description = safe_str(row.get('description'), 160)
        vendor_id = safe_str(row.get('vendorID'))
        mfr_id = safe_str(row.get('mfrID'))
        price = {
            'base': safe_float(row.get('priceA')) or None,
            'msrp': safe_float(row.get('priceMSR')) or None,
            'retail': safe_float(row.get('priceA')) or None,
            'wholesale': safe_float(row.get('priceB')) or None,
            'distributor': safe_float(row.get('priceC')) or None,
            'sample': safe_float(row.get('priceD')) or None,
            'qty_breaks': [],
            'currency': 'USD',
            'history': [],
        }
        cost = {
            'standard': None,
            'last': safe_float(row.get('costLastInShip')) or None,
            'avg': safe_float(row.get('costAverage')) or None,
            'landed': None,
            'currency': 'USD',
            'components': {},
            'qty_breaks': [],
            'history': [],
        }
        quantity = {
            'on_hand': safe_float(row.get('qtyOnHand')),
            'on_so': safe_float(row.get('qtyOnSalesOrder')),
            'on_po': safe_float(row.get('qtyOnPo')),
            'allocated': safe_float(row.get('qtyAllocated')),
            'available': safe_float(row.get('qtyAvailable')),
            'on_wo': safe_float(row.get('qtyOnWO')),
        }
        flags = {
            'back_order_allowed': safe_bool(row.get('backOrder')),
            'discountable': safe_bool(row.get('discountable')),
            'linked': safe_bool(row.get('linked')),
            'not_tracked': safe_bool(row.get('notTracked')),
            'pacing': safe_bool(row.get('pacing')),
            'print_suppressed': safe_bool(row.get('printNot')),
            'serialized': safe_bool(row.get('serialized')),
            'tally_by_type': safe_bool(row.get('tallyByType')),
        }
        gls = {}
        if row.get('salesGlAccount'):
            gls['revenue'] = safe_str(row.get('salesGlAccount'))
        if row.get('costGLAccount'):
            gls['cogs'] = safe_str(row.get('costGLAccount'))
        if row.get('inventoryGlAccount'):
            gls['inventory'] = safe_str(row.get('inventoryGlAccount'))

        defaults = {
            'name': description or item_num,
            'sku': item_num,
            'description': safe_str(row.get('descriptionDetail') or row.get('description')),
            'uom': safe_str(row.get('unitOfMeasure'), 20),
            'kind': 'physical',
            'price': price,
            'cost': cost,
            'quantity': quantity,
            'flags': flags,
            'gls': gls,
            'is_active': not safe_bool(row.get('retired')),
            'vendor_id': lookup['vendor'].get(vendor_id),
            'manufacturer_id': lookup['vendor'].get(mfr_id),  # mfr often in vendor table
            'config': build_config(row, extract_keys=ITEM_EXTRACT),
        }
        if not dry_run:
            # Case-insensitive SKU lookup
            existing = Item.objects.filter(sku__iexact=item_num).first()
            if existing:
                for k, v in defaults.items():
                    setattr(existing, k, v)
                existing.save()
            else:
                obj = Item(**defaults)
                obj.save()
                created += 1
            lookup['item'][item_num] = (existing or obj).pk
        else:
            created += 1
    stats['Item'] = {'total': len(wc2_rows), 'created': created}


def _convert_transaction_header(wc2_row, model_class, lookup, ida_field='idNum'):
    """Build common transaction header defaults from a WC2 row."""
    cid = safe_str(wc2_row.get('customerID'))
    vid = safe_str(wc2_row.get('vendorID'))
    rep_id = safe_str(wc2_row.get('repID'))
    ida = safe_str(wc2_row.get(ida_field))

    totals = {
        'subtotal': safe_float(wc2_row.get('amount')),
        'tax': safe_float(wc2_row.get('salesTax')),
        'shipping': safe_float(wc2_row.get('shipTotal') or wc2_row.get('shipFreightCost')),
        'total': safe_float(wc2_row.get('total')),
        'balance': safe_float(wc2_row.get('balanceDue')),
        'cost': safe_float(wc2_row.get('totalCost')),
        'discount': 0,
        'taxable': 0,
        'other': 0,
        'margin': 0,
        'margin_pc': 0,
        'received': 0,
    }
    # Compute received from total - balance
    if totals['total'] and totals['balance'] is not None:
        totals['received'] = totals['total'] - totals['balance']

    # Map WC2 status to WC3
    wc2_status = safe_str(wc2_row.get('status')).lower()
    complete = safe_bool(wc2_row.get('complete'))
    if complete or wc2_status in ('complete', 'completed', 'closed'):
        status = 'complete'
    elif wc2_status in ('cancel', 'cancelled', 'canceled'):
        status = 'canceled'
    elif wc2_status in ('hold', 'on hold'):
        status = 'hold'
    else:
        status = 'released'

    return {
        'ida': ida,
        'customer_id': lookup['customer'].get(cid),
        'vendor_id': lookup['vendor'].get(vid),
        'company': safe_str(wc2_row.get('company'), 255),
        'attention': safe_str(wc2_row.get('attention'), 255),
        'address_full': ', '.join(filter(None, [
            safe_str(wc2_row.get('address1')),
            safe_str(wc2_row.get('address2')),
            safe_str(wc2_row.get('city')),
            safe_str(wc2_row.get('state')),
            safe_str(wc2_row.get('zip')),
        ])) or None,
        'email': safe_str(wc2_row.get('email'), 254) or None,
        'phone': safe_str(wc2_row.get('phone'), 50) or None,
        'terms': safe_str(wc2_row.get('terms'), 30) or None,
        'ship_via': safe_str(wc2_row.get('shipVia'), 50) or None,
        'status': status,
        'total': safe_decimal(wc2_row.get('total')),
        'balance': safe_decimal(wc2_row.get('balanceDue')),
        'totals': totals,
        'dt_created': wc2_date_to_epoch_ms(wc2_row.get('dateDocument')),
        'dt_modified': now_ms(),
        'is_active': True,
        'config': build_config(wc2_row, extract_keys=TRANSACTION_EXTRACT),
    }


def _convert_line(wc2_row, parent_pk, lookup, line_type='order'):
    """Build common line defaults from a WC2 line row."""
    item_num = safe_str(wc2_row.get('itemNum'))
    item_pk = lookup['item'].get(item_num)
    qty = safe_float(wc2_row.get('qty'))
    unit_price = safe_float(wc2_row.get('unitPrice') or wc2_row.get('price'))
    unit_cost = safe_float(wc2_row.get('unitCost') or wc2_row.get('costEach'))
    extended = safe_float(wc2_row.get('extendedSell') or wc2_row.get('amount'))
    discount_pct = safe_float(wc2_row.get('discount'))

    item_json = {
        'item_id': item_pk,
        'ida_item': item_num,
        'description': safe_str(wc2_row.get('description'), 500),
        'unit_measure': safe_str(wc2_row.get('unitOfMeasure'), 20),
        'line_number': safe_int(wc2_row.get('lineNum')),
        'is_deleted': False,
        'is_active': True,
    }
    quantity_json = {
        'active': qty,
        'staged': qty,
        'remaining': safe_float(wc2_row.get('qtyBackLogged') or wc2_row.get('qtyRemain')),
        'is_fixed': False,
        'precision': 2,
    }
    price_json = {
        'unit': unit_price,
        'unit_base': unit_price,
        'discount_percent': discount_pct,
        'discount_amount': 0.0,
        'extended': extended or (qty * unit_price),
        'is_fixed': False,
        'precision': 2,
    }
    cost_json = {
        'unit': unit_cost,
        'unit_base': unit_cost,
        'extended': safe_float(wc2_row.get('extendedCost')) or (qty * unit_cost),
        'discount_percent': 0.0,
        'discount_amount': 0.0,
        'shipping': 0.0,
        'handling': 0.0,
        'freight': 0.0,
        'commissions': 0.0,
        'tax_rate': 0.0,
        'tax': 0.0,
        'is_fixed': False,
        'precision': 2,
    }

    return {
        'parent_id': parent_pk,
        'item_fk_id': item_pk,
        'line_number': safe_int(wc2_row.get('lineNum')),
        'item': item_json,
        'quantity': quantity_json,
        'price': price_json,
        'cost': cost_json,
        'ida': safe_str(wc2_row.get('idNum')),
        'dt_created': now_ms(),
        'dt_modified': now_ms(),
        'is_active': True,
        'config': build_config(wc2_row),  # lines get basic config (profiles + original)
    }


def convert_proposals(wc2_rows, lookup, stats, dry_run=False):
    from apps.transactions.models import Proposal
    created = 0
    for row in wc2_rows:
        defaults = _convert_transaction_header(row, Proposal, lookup)
        ida = defaults['ida']
        if not ida:
            continue
        if not dry_run:
            obj, was_created = Proposal.objects.update_or_create(
                ida=ida, defaults=defaults
            )
            if was_created:
                created += 1
            lookup['proposal'][ida] = obj.pk
        else:
            created += 1
    stats['Proposal'] = {'total': len(wc2_rows), 'created': created}


def convert_proposal_lines(wc2_rows, lookup, stats, dry_run=False):
    from apps.transactions.models import ProposalLine
    created = 0
    for row in wc2_rows:
        parent_ida = safe_str(row.get('idNumProposal'))
        parent_pk = lookup['proposal'].get(parent_ida)
        if not parent_pk:
            continue
        defaults = _convert_line(row, parent_pk, lookup, line_type='proposal')
        if not dry_run:
            obj = ProposalLine.objects.create(**defaults)
            created += 1
        else:
            created += 1
    stats['ProposalLine'] = {'total': len(wc2_rows), 'created': created}


def convert_orders(wc2_rows, lookup, stats, dry_run=False):
    from apps.transactions.models import Order
    created = 0
    for row in wc2_rows:
        defaults = _convert_transaction_header(row, Order, lookup)
        ida = defaults['ida']
        if not ida:
            continue
        if not dry_run:
            obj, was_created = Order.objects.update_or_create(
                ida=ida, defaults=defaults
            )
            if was_created:
                created += 1
            lookup['order'][ida] = obj.pk
        else:
            created += 1
    stats['Order'] = {'total': len(wc2_rows), 'created': created}


def convert_order_lines(wc2_rows, lookup, stats, dry_run=False):
    from apps.transactions.models import OrderLine
    created = 0
    for row in wc2_rows:
        parent_ida = safe_str(row.get('idNumOrder'))
        parent_pk = lookup['order'].get(parent_ida)
        if not parent_pk:
            continue
        defaults = _convert_line(row, parent_pk, lookup, line_type='order')
        if not dry_run:
            obj = OrderLine.objects.create(**defaults)
            created += 1
        else:
            created += 1
    stats['OrderLine'] = {'total': len(wc2_rows), 'created': created}


def convert_invoices(wc2_rows, lookup, stats, dry_run=False):
    from apps.transactions.models import Invoice
    created = 0
    for row in wc2_rows:
        defaults = _convert_transaction_header(row, Invoice, lookup)
        ida = defaults['ida']
        if not ida:
            continue
        # Link to parent order if exists
        order_ida = safe_str(row.get('idNumOrder'))
        if order_ida and order_ida in lookup['order']:
            defaults['parent_id'] = lookup['order'][order_ida]
            defaults['parent_model'] = 'order'
        if not dry_run:
            obj, was_created = Invoice.objects.update_or_create(
                ida=ida, defaults=defaults
            )
            if was_created:
                created += 1
            lookup['invoice'][ida] = obj.pk
        else:
            created += 1
    stats['Invoice'] = {'total': len(wc2_rows), 'created': created}


def convert_invoice_lines(wc2_rows, lookup, stats, dry_run=False):
    from apps.transactions.models import InvoiceLine
    created = 0
    for row in wc2_rows:
        parent_ida = safe_str(row.get('idNumInvoice'))
        parent_pk = lookup['invoice'].get(parent_ida)
        if not parent_pk:
            continue
        defaults = _convert_line(row, parent_pk, lookup, line_type='invoice')
        if not dry_run:
            obj = InvoiceLine.objects.create(**defaults)
            created += 1
        else:
            created += 1
    stats['InvoiceLine'] = {'total': len(wc2_rows), 'created': created}


def convert_purchases(wc2_rows, lookup, stats, dry_run=False):
    from apps.transactions.models import Purchase
    created = 0
    for row in wc2_rows:
        defaults = _convert_transaction_header(row, Purchase, lookup, ida_field='idNum')
        ida = defaults['ida']
        if not ida:
            continue
        # PO-specific: vendor is primary
        vid = safe_str(row.get('vendorID'))
        defaults['vendor_id'] = lookup['vendor'].get(vid)
        defaults['company'] = safe_str(row.get('vendorCompany') or row.get('company'), 255)
        if not dry_run:
            obj, was_created = Purchase.objects.update_or_create(
                ida=ida, defaults=defaults
            )
            if was_created:
                created += 1
            lookup['purchase'][ida] = obj.pk
        else:
            created += 1
    stats['Purchase'] = {'total': len(wc2_rows), 'created': created}


def convert_purchase_lines(wc2_rows, lookup, stats, dry_run=False):
    from apps.transactions.models import PurchaseLine
    created = 0
    for row in wc2_rows:
        parent_ida = safe_str(row.get('idNumPO'))
        parent_pk = lookup['purchase'].get(parent_ida)
        if not parent_pk:
            continue
        defaults = _convert_line(row, parent_pk, lookup, line_type='purchase')
        # PurchaseLine uses cost, not price — remove price key
        defaults.pop('price', None)
        if not dry_run:
            obj = PurchaseLine.objects.create(**defaults)
            created += 1
        else:
            created += 1
    stats['PurchaseLine'] = {'total': len(wc2_rows), 'created': created}


def convert_payments(wc2_rows, lookup, stats, dry_run=False):
    from apps.transactions.models import Payment
    created = 0
    for row in wc2_rows:
        ida = safe_str(row.get('idNum'))
        if not ida:
            continue
        cid = safe_str(row.get('customerID'))
        inv_ida = safe_str(row.get('idNumInvoice'))
        order_ida = safe_str(row.get('idNumOrder'))

        defaults = {
            'ida': ida,
            'customer_id': lookup['customer'].get(cid),
            'total': safe_decimal(row.get('amount')),
            'balance': safe_decimal(row.get('amountAvailable')),
            'status': 'complete' if safe_bool(row.get('complete')) else 'released',
            'totals': {
                'subtotal': safe_float(row.get('amount')),
                'total': safe_float(row.get('amount')),
                'balance': safe_float(row.get('amountAvailable')),
                'received': safe_float(row.get('amount')) - safe_float(row.get('amountAvailable')),
                'tax': safe_float(row.get('salesTax')),
                'discount': 0, 'taxable': 0, 'shipping': 0,
                'other': 0, 'cost': 0, 'margin': 0, 'margin_pc': 0,
            },
            'company': safe_str(row.get('company'), 255),
            'dt_created': wc2_date_to_epoch_ms(row.get('dateDocument')),
            'dt_modified': now_ms(),
            'is_active': True,
            'config': build_config(row, extract_keys=PAYMENT_EXTRACT),
        }
        # Link to invoice/order if exists
        if inv_ida and inv_ida in lookup['invoice']:
            defaults['parent_id'] = lookup['invoice'][inv_ida]
            defaults['parent_model'] = 'invoice'
        elif order_ida and order_ida in lookup['order']:
            defaults['parent_id'] = lookup['order'][order_ida]
            defaults['parent_model'] = 'order'

        if not dry_run:
            obj, was_created = Payment.objects.update_or_create(
                ida=ida, defaults=defaults
            )
            if was_created:
                created += 1
            lookup['payment'][ida] = obj.pk
        else:
            created += 1
    stats['Payment'] = {'total': len(wc2_rows), 'created': created}


def convert_ledger(wc2_rows, lookup, stats, dry_run=False):
    from apps.accounts.models import Ledger
    created = 0
    for row in wc2_rows:
        # Normalize plural → singular table names
        table_name = safe_str(row.get('tableName'))
        if table_name == 'Invoices':
            table_name = 'Invoice'
        elif table_name == 'Payments':
            table_name = 'Payment'
        elif table_name == '00/00/00':
            continue  # garbage data

        cid = safe_str(row.get('customerID'))
        defaults = {
            'ida': safe_str(row.get('idNum')),
            'config': {
                **build_config(row),
                'wc2_table_name': table_name,
                'wc2_table_num': safe_int(row.get('tableNum')),
                'customer_id': cid,
                'doc_ref': safe_str(row.get('docRefid')),
                'terms': safe_str(row.get('terms')),
                'unapplied_value': safe_float(row.get('unAppliedValue')),
                'original_value': safe_float(row.get('origValue')),
                'discount_potential': safe_float(row.get('discntPotential')),
            },
            'dt_created': wc2_date_to_epoch_ms(row.get('dateDocument')),
            'dt_modified': now_ms(),
            'is_active': True,
        }
        if not dry_run:
            obj = Ledger.objects.create(**defaults)
            created += 1
        else:
            created += 1
    stats['Ledger'] = {'total': len(wc2_rows), 'created': created}


# ── Audit functions ──────────────────────────────────────────────────────

def compute_audit(folder):
    """Compute financial checksums from the raw WC2 dump."""
    audit = {}

    # Open orders
    orders = load_wc2(folder, 'Order')
    open_orders = [o for o in orders if safe_float(o.get('amountBackLog', 0)) > 0]
    audit['orders'] = {
        'total_count': len(orders),
        'open_count': len(open_orders),
        'open_backlog': round(sum(safe_float(o.get('amountBackLog', 0)) for o in open_orders), 2),
    }

    # Unpaid invoices
    invoices = load_wc2(folder, 'Invoice')
    unpaid = [i for i in invoices if safe_float(i.get('balanceDue', 0)) != 0]
    audit['invoices'] = {
        'total_count': len(invoices),
        'unpaid_count': len(unpaid),
        'unpaid_balance': round(sum(safe_float(i.get('balanceDue', 0)) for i in unpaid), 2),
        'total_invoiced': round(sum(safe_float(i.get('total', 0)) for i in invoices), 2),
    }

    # Unapplied payments
    payments = load_wc2(folder, 'Payment')
    unapplied = [p for p in payments if safe_float(p.get('amountAvailable', 0)) != 0]
    audit['payments'] = {
        'total_count': len(payments),
        'unapplied_count': len(unapplied),
        'unapplied_total': round(sum(safe_float(p.get('amountAvailable', 0)) for p in unapplied), 2),
        'total_paid': round(sum(safe_float(p.get('amount', 0)) for p in payments), 2),
    }

    # Open POs
    pos = load_wc2(folder, 'PO')
    open_pos = [p for p in pos if safe_float(p.get('amountBackLog', 0)) > 0]
    audit['purchases'] = {
        'total_count': len(pos),
        'open_count': len(open_pos),
        'open_backlog': round(sum(safe_float(p.get('amountBackLog', 0)) for p in open_pos), 2),
    }

    # Inventory
    items = load_wc2(folder, 'Item')
    audit['inventory'] = {
        'total_items': len(items),
        'items_with_qty': sum(1 for i in items if safe_float(i.get('qtyOnHand', 0)) != 0),
        'total_on_hand': round(sum(safe_float(i.get('qtyOnHand', 0)) for i in items), 2),
        'total_on_so': round(sum(safe_float(i.get('qtyOnSalesOrder', 0)) for i in items), 2),
        'total_on_po': round(sum(safe_float(i.get('qtyOnPo', 0)) for i in items), 2),
    }

    # Record counts
    audit['counts'] = {
        'customers': len(load_wc2(folder, 'Customer')),
        'contacts': len(load_wc2(folder, 'Contact')),
        'vendors': len(load_wc2(folder, 'Vendor')),
        'gl_accounts': len(load_wc2(folder, 'GLAccount')),
        'items': len(items),
        'proposals': len(load_wc2(folder, 'Proposal')),
        'orders': len(orders),
        'invoices': len(invoices),
        'payments': len(payments),
        'purchases': len(pos),
    }

    return audit


# ── Command ──────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Import WC2 (4D) data dump into WC3"

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest='action')

        # discover
        p_discover = sub.add_parser('discover', help='Inventory all tables in a dump folder')
        p_discover.add_argument('folder', type=str)

        # audit
        p_audit = sub.add_parser('audit', help='Compute financial checksums from dump')
        p_audit.add_argument('folder', type=str)

        # import
        p_import = sub.add_parser('import', help='Convert and load WC2 data into WC3')
        p_import.add_argument('folder', type=str)
        p_import.add_argument('--dry-run', action='store_true', help='Show what would be imported without writing')
        p_import.add_argument('--tables', type=str, help='Comma-separated list of tables to import (default: all)')
        p_import.add_argument('--fast', action='store_true', help='Use bulk_create (skips save hooks, much faster)')

        # verify
        p_verify = sub.add_parser('verify', help='Compare WC3 totals against dump audit')
        p_verify.add_argument('folder', type=str)

    def handle(self, *args, **options):
        action = options.get('action')
        if action == 'discover':
            self._discover(options['folder'])
        elif action == 'audit':
            self._audit(options['folder'])
        elif action == 'import':
            self._import(options['folder'], options.get('dry_run', False),
                         options.get('tables'), options.get('fast', False))
        elif action == 'verify':
            self._verify(options['folder'])
        else:
            self.stderr.write("Usage: import_wc2 {discover|audit|import|verify} <folder>")

    def _discover(self, folder):
        folder = Path(folder)
        if not folder.is_dir():
            raise CommandError(f"Not a directory: {folder}")

        results = []
        for f in sorted(folder.glob('*.json')):
            name = f.stem
            try:
                data = load_wc2(folder, name)
                count = len(data)
                fields = list(data[0].keys())[:6] if data else []
                skip = name in SKIP_TABLES
                results.append((name, count, fields, skip))
            except Exception as e:
                results.append((name, -1, [str(e)[:60]], False))

        self.stdout.write(f"\n{'Table':<30} {'Records':>10}  {'Status':<8}  Sample Fields")
        self.stdout.write('─' * 90)
        for name, count, fields, skip in sorted(results, key=lambda x: -x[1]):
            status = 'SKIP' if skip else ('IMPORT' if name in [t for t in IMPORT_ORDER] else 'other')
            self.stdout.write(f"{name:<30} {count:>10,}  {status:<8}  {fields}")

        total = sum(c for _, c, _, _ in results if c > 0)
        skip_total = sum(c for _, c, _, skip in results if c > 0 and skip)
        self.stdout.write(f"\nTotal records: {total:,}  |  Skip: {skip_total:,}  |  Import: {total - skip_total:,}")

    def _audit(self, folder):
        audit = compute_audit(folder)
        self.stdout.write(json.dumps(audit, indent=2))

    def _import(self, folder, dry_run=False, tables_filter=None, fast=False):
        folder = Path(folder)
        if not folder.is_dir():
            raise CommandError(f"Not a directory: {folder}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no data will be written"))
        if fast:
            self.stdout.write(self.style.WARNING("FAST MODE — bulk_create, no save hooks"))
            return self._import_fast(folder, dry_run, tables_filter)

        # Filter tables if specified
        import_tables = IMPORT_ORDER
        if tables_filter:
            requested = [t.strip() for t in tables_filter.split(',')]
            import_tables = [t for t in IMPORT_ORDER if t in requested]

        # Lookup tables for FK resolution (WC2 natural key → WC3 pk)
        lookup = {
            'customer': {},  # customerID → OrgBase.pk
            'vendor': {},    # vendorID → OrgBase.pk
            'rep': {},       # repID → OrgBase.pk
            'item': {},      # itemNum → Item.pk
            'proposal': {},  # idNum → Proposal.pk
            'order': {},     # idNum → Order.pk
            'invoice': {},   # idNum → Invoice.pk
            'purchase': {},  # idNum → Purchase.pk
            'payment': {},   # idNum → Payment.pk
        }
        stats = {}

        # Converter dispatch
        converters = {
            'GLAccount': lambda rows: convert_gl_accounts(rows, stats, dry_run),
            'Customer': lambda rows: convert_customers(rows, lookup, stats, dry_run),
            'Vendor': lambda rows: convert_vendors(rows, lookup, stats, dry_run),
            'Rep': lambda rows: convert_reps(rows, lookup, stats, dry_run),
            'Employee': lambda rows: None,  # TODO: map to OrgBase employee
            'Contact': lambda rows: convert_contacts(rows, lookup, stats, dry_run),
            'Item': lambda rows: convert_items(rows, lookup, stats, dry_run),
            'Proposal': lambda rows: convert_proposals(rows, lookup, stats, dry_run),
            'ProposalLine': lambda rows: convert_proposal_lines(rows, lookup, stats, dry_run),
            'Order': lambda rows: convert_orders(rows, lookup, stats, dry_run),
            'OrderLine': lambda rows: convert_order_lines(rows, lookup, stats, dry_run),
            'Invoice': lambda rows: convert_invoices(rows, lookup, stats, dry_run),
            'InvoiceLine': lambda rows: convert_invoice_lines(rows, lookup, stats, dry_run),
            'PO': lambda rows: convert_purchases(rows, lookup, stats, dry_run),
            'POLine': lambda rows: convert_purchase_lines(rows, lookup, stats, dry_run),
            'Payment': lambda rows: convert_payments(rows, lookup, stats, dry_run),
            'Ledger': lambda rows: convert_ledger(rows, lookup, stats, dry_run),
        }

        for table in import_tables:
            if table not in converters:
                continue
            wc2_rows = load_wc2(folder, table)
            if not wc2_rows:
                self.stdout.write(f"  {table}: empty — skipping")
                continue
            self.stdout.write(f"  {table}: {len(wc2_rows):,} rows ... ", ending='')
            try:
                if not dry_run:
                    with transaction.atomic():
                        converters[table](wc2_rows)
                else:
                    converters[table](wc2_rows)
                s = stats.get(table, {})
                self.stdout.write(self.style.SUCCESS(f"OK ({s.get('created', 0):,} created)"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"FAILED: {e}"))

        # Summary
        self.stdout.write(f"\n{'Table':<20} {'Total':>10} {'Created':>10}")
        self.stdout.write('─' * 42)
        for table in import_tables:
            s = stats.get(table, {})
            if s:
                self.stdout.write(f"{table:<20} {s.get('total', 0):>10,} {s.get('created', 0):>10,}")

    def _import_fast(self, folder, dry_run=False, tables_filter=None):
        """Fast import using bulk_create — skips save hooks, much faster.

        Builds all model instances in memory, resolves FKs via ida lookups
        after bulk_create (which assigns PKs), then bulk_creates dependent tables.
        """
        from apps.accounts.models import GlAccount
        from apps.orgs.models import OrgBase
        from apps.core.models import Contact
        from apps.products.models import Item
        from apps.transactions.models import (
            Proposal, ProposalLine, Order, OrderLine,
            Invoice, InvoiceLine, Purchase, PurchaseLine, Payment,
        )

        BATCH = 2000

        def _bulk(Model, instances, label):
            if dry_run:
                self.stdout.write(self.style.SUCCESS(f"  {label}: {len(instances):,} (dry run)"))
                return instances
            created = []
            for i in range(0, len(instances), BATCH):
                batch = instances[i:i + BATCH]
                created.extend(Model.objects.bulk_create(batch, ignore_conflicts=False))
            self.stdout.write(self.style.SUCCESS(f"  {label}: {len(created):,} created"))
            return created

        filter_set = None
        if tables_filter:
            filter_set = set(t.strip() for t in tables_filter.split(','))

        def _skip(table):
            return filter_set and table not in filter_set

        # ── GL Accounts ──
        if not _skip('GLAccount'):
            rows = load_wc2(folder, 'GLAccount')
            objs = []
            for r in rows:
                account = safe_str(r.get('account'), 20)
                if not account:
                    continue
                objs.append(GlAccount(
                    ida=account,
                    name=safe_str(r.get('name'), 200),
                    type=safe_str(r.get('typeAcct'), 50),
                    config=build_config(r),
                    is_active=True,
                ))
            _bulk(GlAccount, objs, 'GLAccount')

        # ── Orgs (Customer, Vendor, Rep) ──
        org_instances = []
        customer_ida_map = {}  # ida → index in org_instances
        vendor_ida_map = {}
        rep_ida_map = {}

        if not _skip('Customer'):
            rows = load_wc2(folder, 'Customer')
            for r in rows:
                cid = safe_str(r.get('customerID'))
                if not cid:
                    continue
                financial = {
                    'credit': {'limit': safe_float(r.get('creditLimit')), 'used': safe_float(r.get('highCredit')), 'approved': safe_str(r.get('creditApproval'))},
                    'aging': {'current': safe_float(r.get('balanceCurrent')), 'period_1': safe_float(r.get('balPastPeriod1')), 'period_2': safe_float(r.get('balPastPeriod2')), 'period_3': safe_float(r.get('balPastPeriod3')), 'balance_due': safe_float(r.get('balanceDue')), 'future_due': safe_float(r.get('futureDue'))},
                    'sales': {'mtd': safe_float(r.get('salesMTD')), 'ytd': safe_float(r.get('salesYTD')), 'last_yr': safe_float(r.get('salesLastYr')), 'all_time': safe_float(r.get('salesAllTime')), 'last_date': safe_str(r.get('lastSaleDate')), 'last_amount': safe_float(r.get('lastSaleAmount'))},
                    'payments': {'last_date': safe_str(r.get('lastPayDate')), 'last_amount': safe_float(r.get('lastPayAmount')), 'days_avg_paid': safe_float(r.get('daysAvgPaid'))},
                    'costs': {'mtd': safe_float(r.get('costsMTD')), 'ytd': safe_float(r.get('costsYTD')), 'all_time': safe_float(r.get('costsAllTime'))},
                }
                obj = OrgBase(
                    ida=cid,
                    display_name=safe_str(r.get('company'), 255) or cid,
                    org_type='customer',
                    status='retired' if r.get('dateRetired') else 'active',
                    phone=safe_str(r.get('phone'), 50),
                    email=safe_str(r.get('email'), 254) or None,
                    address_full=', '.join(filter(None, [safe_str(r.get('address1')), safe_str(r.get('address2')), safe_str(r.get('city')), safe_str(r.get('state')), safe_str(r.get('zip'))])) or None,
                    domain=safe_str(r.get('domain'), 255) or None,
                    terms=safe_str(r.get('terms'), 30) or None,
                    price_level=safe_str(r.get('typeSale'), 30) or None,
                    financial=financial,
                    config=build_config(r, extract_keys=CUSTOMER_EXTRACT),
                    is_active=not bool(r.get('dateRetired')),
                    tax_exempt_code=safe_str(r.get('taxExemptid'), 80),
                )
                customer_ida_map[cid] = len(org_instances)
                org_instances.append(obj)

        if not _skip('Vendor'):
            rows = load_wc2(folder, 'Vendor')
            for r in rows:
                vid = safe_str(r.get('vendorID'))
                if not vid:
                    continue
                financial = {
                    'payables': {'total_due': safe_float(r.get('totalDue')), 'ytd_purchases': safe_float(r.get('ytdPurchases')), 'last_yr_purchases': safe_float(r.get('lYPurchases'))},
                    'credit': {'limit': safe_float(r.get('creditLimit')), 'high': safe_float(r.get('highCredit'))},
                }
                obj = OrgBase(
                    ida=vid,
                    display_name=safe_str(r.get('company'), 255) or vid,
                    org_type='vendor',
                    status='retired' if r.get('dateRetired') else 'active',
                    phone=safe_str(r.get('phone'), 50),
                    email=safe_str(r.get('email'), 254) or None,
                    address_full=', '.join(filter(None, [safe_str(r.get('address1')), safe_str(r.get('address2')), safe_str(r.get('city')), safe_str(r.get('state')), safe_str(r.get('zip'))])) or None,
                    domain=safe_str(r.get('domain'), 255) or None,
                    terms=safe_str(r.get('terms'), 30) or None,
                    financial=financial,
                    config=build_config(r, extract_keys=VENDOR_EXTRACT),
                    is_active=not bool(r.get('dateRetired')),
                )
                vendor_ida_map[vid] = len(org_instances)
                org_instances.append(obj)

        if not _skip('Rep'):
            rows = load_wc2(folder, 'Rep')
            for r in rows:
                rid = safe_str(r.get('repID') or r.get('idNum'))
                if not rid:
                    continue
                name = safe_str(r.get('company') or (safe_str(r.get('nameFirst', '')) + ' ' + safe_str(r.get('nameLast', ''))), 255).strip()
                obj = OrgBase(
                    ida=rid,
                    display_name=name or rid,
                    org_type='rep',
                    phone=safe_str(r.get('phone'), 50),
                    email=safe_str(r.get('email'), 254) or None,
                    config=build_config(r),
                    is_active=True,
                )
                rep_ida_map[rid] = len(org_instances)
                org_instances.append(obj)

        # Bulk create all orgs
        if org_instances:
            created_orgs = _bulk(OrgBase, org_instances, f'OrgBase ({len(customer_ida_map)} cust + {len(vendor_ida_map)} vend + {len(rep_ida_map)} rep)')
            # Build ida→pk lookups from created objects
            customer_pk = {}
            vendor_pk = {}
            for ida, idx in customer_ida_map.items():
                customer_pk[ida] = created_orgs[idx].pk if not dry_run else 0
            for ida, idx in vendor_ida_map.items():
                vendor_pk[ida] = created_orgs[idx].pk if not dry_run else 0
            rep_pk = {}
            for ida, idx in rep_ida_map.items():
                rep_pk[ida] = created_orgs[idx].pk if not dry_run else 0
        else:
            customer_pk = {}
            vendor_pk = {}
            rep_pk = {}

        # ── Contacts ──
        if not _skip('Contact'):
            rows = load_wc2(folder, 'Contact')
            objs = []
            for r in rows:
                name_first = safe_str(r.get('nameFirst'), 100)
                name_last = safe_str(r.get('nameLast'), 100)
                email = safe_str(r.get('email') or r.get('emailAddress'), 254) or None
                if not name_first and not name_last and not email:
                    continue
                cid = safe_str(r.get('customerID'))
                objs.append(Contact(
                    name_first=name_first,
                    name_last=name_last,
                    name_middle=safe_str(r.get('nameMiddle'), 100),
                    name_prefix=safe_str(r.get('title'), 20),
                    email=email,
                    phone=safe_str(r.get('phone'), 50) or None,
                    company=safe_str(r.get('company'), 200),
                    title=safe_str(r.get('title'), 100),
                    address_full=', '.join(filter(None, [safe_str(r.get('address1')), safe_str(r.get('address2')), safe_str(r.get('city')), safe_str(r.get('state')), safe_str(r.get('zip'))])) or None,
                    customer_id=customer_pk.get(cid),
                    is_active=True,
                    config=build_config(r),
                ))
            # Contacts may have duplicate emails — use ignore_conflicts
            if objs and not dry_run:
                created = []
                for i in range(0, len(objs), BATCH):
                    batch = objs[i:i + BATCH]
                    created.extend(Contact.objects.bulk_create(batch, ignore_conflicts=True))
                self.stdout.write(self.style.SUCCESS(f"  Contact: {len(created):,} created (dupes skipped)"))
            elif objs:
                self.stdout.write(self.style.SUCCESS(f"  Contact: {len(objs):,} (dry run)"))

        # ── Items ──
        item_pk = {}
        if not _skip('Item'):
            rows = load_wc2(folder, 'Item')
            objs = []
            item_ida_map = {}
            for r in rows:
                item_num = safe_str(r.get('itemNum'), 80)
                if not item_num:
                    continue
                vid = safe_str(r.get('vendorID'))
                mfr = safe_str(r.get('mfrID'))
                obj = Item(
                    ida=item_num,
                    sku=item_num,
                    name=safe_str(r.get('description'), 160) or item_num,
                    description=safe_str(r.get('descriptionDetail') or r.get('description')),
                    uom=safe_str(r.get('unitOfMeasure'), 20),
                    kind='physical',
                    price={'base': safe_float(r.get('priceA')) or None, 'msrp': safe_float(r.get('priceMSR')) or None, 'retail': safe_float(r.get('priceA')) or None, 'wholesale': safe_float(r.get('priceB')) or None, 'distributor': safe_float(r.get('priceC')) or None, 'sample': safe_float(r.get('priceD')) or None, 'qty_breaks': [], 'currency': 'USD', 'history': []},
                    cost={'standard': None, 'last': safe_float(r.get('costLastInShip')) or None, 'avg': safe_float(r.get('costAverage')) or None, 'landed': None, 'currency': 'USD', 'components': {}, 'qty_breaks': [], 'history': []},
                    quantity={'on_hand': safe_float(r.get('qtyOnHand')), 'on_so': safe_float(r.get('qtyOnSalesOrder')), 'on_po': safe_float(r.get('qtyOnPo')), 'allocated': safe_float(r.get('qtyAllocated')), 'available': safe_float(r.get('qtyAvailable')), 'on_wo': safe_float(r.get('qtyOnWO'))},
                    flags={'back_order_allowed': safe_bool(r.get('backOrder')), 'discountable': safe_bool(r.get('discountable')), 'linked': safe_bool(r.get('linked')), 'not_tracked': safe_bool(r.get('notTracked')), 'pacing': safe_bool(r.get('pacing')), 'print_suppressed': safe_bool(r.get('printNot')), 'serialized': safe_bool(r.get('serialized')), 'tally_by_type': safe_bool(r.get('tallyByType'))},
                    gls={k: v for k, v in [('revenue', safe_str(r.get('salesGlAccount'))), ('cogs', safe_str(r.get('costGLAccount'))), ('inventory', safe_str(r.get('inventoryGlAccount')))] if v},
                    is_active=not safe_bool(r.get('retired')),
                    vendor_id=vendor_pk.get(vid),
                    manufacturer_id=vendor_pk.get(mfr),
                    config=build_config(r, extract_keys=ITEM_EXTRACT),
                )
                item_ida_map[item_num] = len(objs)
                objs.append(obj)
            created_items = _bulk(Item, objs, 'Item')
            for ida, idx in item_ida_map.items():
                item_pk[ida] = created_items[idx].pk if not dry_run else 0

        # ── Transaction helper ──
        def _make_header(Model, r, customer_pk, vendor_pk, extract=TRANSACTION_EXTRACT):
            cid = safe_str(r.get('customerID'))
            vid = safe_str(r.get('vendorID'))
            ida = safe_str(r.get('idNum'))
            wc2_status = safe_str(r.get('status')).lower()
            complete = safe_bool(r.get('complete'))
            if complete or wc2_status in ('complete', 'completed', 'closed'):
                status = 'complete'
            elif wc2_status in ('cancel', 'cancelled', 'canceled'):
                status = 'canceled'
            elif wc2_status in ('hold', 'on hold'):
                status = 'hold'
            else:
                status = 'released'
            totals = {
                'subtotal': safe_float(r.get('amount')), 'tax': safe_float(r.get('salesTax')),
                'shipping': safe_float(r.get('shipTotal') or r.get('shipFreightCost')),
                'total': safe_float(r.get('total')), 'balance': safe_float(r.get('balanceDue')),
                'cost': safe_float(r.get('totalCost')), 'discount': 0, 'taxable': 0,
                'other': 0, 'margin': 0, 'margin_pc': 0, 'received': 0,
            }
            if totals['total'] and totals['balance'] is not None:
                totals['received'] = totals['total'] - totals['balance']
            return Model(
                ida=ida,
                customer_id=customer_pk.get(cid),
                vendor_id=vendor_pk.get(vid),
                company=safe_str(r.get('company'), 255),
                attention=safe_str(r.get('attention'), 255),
                address_full=', '.join(filter(None, [safe_str(r.get('address1')), safe_str(r.get('address2')), safe_str(r.get('city')), safe_str(r.get('state')), safe_str(r.get('zip'))])) or None,
                email=safe_str(r.get('email'), 254) or None,
                phone=safe_str(r.get('phone'), 50) or None,
                terms=safe_str(r.get('terms'), 30) or None,
                ship_via=safe_str(r.get('shipVia'), 50) or None,
                status=status,
                total=safe_decimal(r.get('total')),
                balance=safe_decimal(r.get('balanceDue')),
                totals=totals,
                dt_created=wc2_date_to_epoch_ms(r.get('dateDocument')),
                dt_modified=now_ms(),
                is_active=True,
                config=build_config(r, extract_keys=extract),
            )

        # FK name per line model
        LINE_FK = {
            ProposalLine: 'proposal_id',
            OrderLine: 'order_id',
            InvoiceLine: 'invoice_id',
            PurchaseLine: 'purchase_id',
        }

        def _make_line(Model, r, parent_pk, item_pk_map):
            item_num = safe_str(r.get('itemNum'))
            i_pk = item_pk_map.get(item_num)
            qty = safe_float(r.get('qty'))
            unit_price = safe_float(r.get('unitPrice') or r.get('price'))
            unit_cost = safe_float(r.get('unitCost') or r.get('costEach'))
            extended = safe_float(r.get('extendedSell') or r.get('amount'))
            fk_name = LINE_FK.get(Model, 'parent_id')
            kwargs = {fk_name: parent_pk}
            # PurchaseLine (BaseExecLineModel) has no price field
            is_sell = hasattr(Model, 'price')
            line_kwargs = {
                **kwargs,
                'item_fk_id': i_pk,
                'line_number': safe_int(r.get('lineNum')),
                'item': {'item_id': i_pk, 'ida_item': item_num, 'description': safe_str(r.get('description'), 500), 'unit_measure': safe_str(r.get('unitOfMeasure'), 20), 'line_number': safe_int(r.get('lineNum')), 'is_deleted': False, 'is_active': True},
                'quantity': {'active': qty, 'staged': qty, 'remaining': safe_float(r.get('qtyBackLogged') or r.get('qtyRemain')), 'is_fixed': False, 'precision': 2},
                'cost': {'unit': unit_cost, 'unit_base': unit_cost, 'extended': safe_float(r.get('extendedCost')) or (qty * unit_cost), 'discount_percent': 0.0, 'discount_amount': 0.0, 'shipping': 0.0, 'handling': 0.0, 'freight': 0.0, 'commissions': 0.0, 'tax_rate': 0.0, 'tax': 0.0, 'is_fixed': False, 'precision': 2},
                'ida': safe_str(r.get('idNum')),
                'dt_created': now_ms(),
                'dt_modified': now_ms(),
                'is_active': True,
                'config': build_config(r),
            }
            if is_sell:
                line_kwargs['price'] = {'unit': unit_price, 'unit_base': unit_price, 'discount_percent': safe_float(r.get('discount')), 'discount_amount': 0.0, 'extended': extended or (qty * unit_price), 'is_fixed': False, 'precision': 2}
            return Model(**line_kwargs)

        # ── Proposals + Lines ──
        proposal_pk = {}
        if not _skip('Proposal'):
            rows = load_wc2(folder, 'Proposal')
            objs = []
            ida_map = {}
            for r in rows:
                ida = safe_str(r.get('idNum'))
                if not ida:
                    continue
                ida_map[ida] = len(objs)
                objs.append(_make_header(Proposal, r, customer_pk, vendor_pk))
            created = _bulk(Proposal, objs, 'Proposal')
            for ida, idx in ida_map.items():
                proposal_pk[ida] = created[idx].pk if not dry_run else 0

        if not _skip('ProposalLine'):
            rows = load_wc2(folder, 'ProposalLine')
            objs = []
            for r in rows:
                parent_ida = safe_str(r.get('idNumProposal'))
                ppk = proposal_pk.get(parent_ida)
                if not ppk:
                    continue
                objs.append(_make_line(ProposalLine, r, ppk, item_pk))
            _bulk(ProposalLine, objs, 'ProposalLine')

        # ── Orders + Lines ──
        order_pk = {}
        if not _skip('Order'):
            rows = load_wc2(folder, 'Order')
            objs = []
            ida_map = {}
            for r in rows:
                ida = safe_str(r.get('idNum'))
                if not ida:
                    continue
                ida_map[ida] = len(objs)
                objs.append(_make_header(Order, r, customer_pk, vendor_pk))
            created = _bulk(Order, objs, 'Order')
            for ida, idx in ida_map.items():
                order_pk[ida] = created[idx].pk if not dry_run else 0

        if not _skip('OrderLine'):
            rows = load_wc2(folder, 'OrderLine')
            objs = []
            for r in rows:
                parent_ida = safe_str(r.get('idNumOrder'))
                ppk = order_pk.get(parent_ida)
                if not ppk:
                    continue
                objs.append(_make_line(OrderLine, r, ppk, item_pk))
            _bulk(OrderLine, objs, 'OrderLine')

        # ── Invoices + Lines ──
        invoice_pk = {}
        if not _skip('Invoice'):
            rows = load_wc2(folder, 'Invoice')
            objs = []
            ida_map = {}
            for r in rows:
                ida = safe_str(r.get('idNum'))
                if not ida:
                    continue
                ida_map[ida] = len(objs)
                obj = _make_header(Invoice, r, customer_pk, vendor_pk)
                order_ida = safe_str(r.get('idNumOrder'))
                if order_ida and order_ida in order_pk:
                    obj.parent_id = order_pk[order_ida]
                    obj.parent_model = 'order'
                objs.append(obj)
            created = _bulk(Invoice, objs, 'Invoice')
            for ida, idx in ida_map.items():
                invoice_pk[ida] = created[idx].pk if not dry_run else 0

        if not _skip('InvoiceLine'):
            rows = load_wc2(folder, 'InvoiceLine')
            objs = []
            for r in rows:
                parent_ida = safe_str(r.get('idNumInvoice'))
                ppk = invoice_pk.get(parent_ida)
                if not ppk:
                    continue
                objs.append(_make_line(InvoiceLine, r, ppk, item_pk))
            _bulk(InvoiceLine, objs, 'InvoiceLine')

        # ── Purchases + Lines ──
        purchase_pk = {}
        if not _skip('PO'):
            rows = load_wc2(folder, 'PO')
            objs = []
            ida_map = {}
            for r in rows:
                ida = safe_str(r.get('idNum'))
                if not ida:
                    continue
                ida_map[ida] = len(objs)
                obj = _make_header(Purchase, r, customer_pk, vendor_pk)
                vid = safe_str(r.get('vendorID'))
                obj.vendor_id = vendor_pk.get(vid)
                obj.company = safe_str(r.get('vendorCompany') or r.get('company'), 255)
                objs.append(obj)
            created = _bulk(Purchase, objs, 'Purchase')
            for ida, idx in ida_map.items():
                purchase_pk[ida] = created[idx].pk if not dry_run else 0

        if not _skip('POLine'):
            rows = load_wc2(folder, 'POLine')
            objs = []
            for r in rows:
                parent_ida = safe_str(r.get('idNumPO'))
                ppk = purchase_pk.get(parent_ida)
                if not ppk:
                    continue
                obj = _make_line(PurchaseLine, r, ppk, item_pk)
                # PurchaseLine has no price field
                if hasattr(obj, 'price'):
                    obj.price = None
                objs.append(obj)
            _bulk(PurchaseLine, objs, 'PurchaseLine')

        # ── Payments ──
        # Payment model uses: amount, available, method, invoice_id, customer_id
        # NOT TransactionBaseModel fields (total, balance, totals, company)
        if not _skip('Payment'):
            rows = load_wc2(folder, 'Payment')
            objs = []
            for r in rows:
                ida = safe_str(r.get('idNum'))
                if not ida:
                    continue
                cid = safe_str(r.get('customerID'))
                inv_ida = safe_str(r.get('idNumInvoice'))
                obj = Payment(
                    ida=ida,
                    customer_id=customer_pk.get(cid),
                    invoice_id=invoice_pk.get(inv_ida),
                    amount=safe_decimal(r.get('amount')),
                    available=safe_decimal(r.get('amountAvailable')),
                    method=safe_str(r.get('typePayment'), 50),
                    is_active=True,
                    dt_created=wc2_date_to_epoch_ms(r.get('dateDocument')),
                    dt_modified=now_ms(),
                    config=build_config(r, extract_keys=PAYMENT_EXTRACT),
                )
                objs.append(obj)
            _bulk(Payment, objs, 'Payment')

        self.stdout.write(self.style.SUCCESS("\nFast import complete."))

    def _verify(self, folder):
        """Compare WC3 database totals against the raw dump audit."""
        dump_audit = compute_audit(folder)

        from apps.transactions.models import Invoice, Payment, Order, Purchase
        from apps.products.models import Item
        from apps.orgs.models import OrgBase

        wc3 = {}
        # Invoice balance
        from django.db.models import Sum
        inv_agg = Invoice.objects.filter(balance__isnull=False).exclude(balance=0).aggregate(
            count=models.Count('id'), total=Sum('balance')
        )
        wc3['invoices_unpaid'] = {
            'count': inv_agg['count'] or 0,
            'balance': float(inv_agg['total'] or 0),
        }
        # Payment unapplied
        pay_agg = Payment.objects.filter(balance__isnull=False).exclude(balance=0).aggregate(
            count=models.Count('id'), total=Sum('balance')
        )
        wc3['payments_unapplied'] = {
            'count': pay_agg['count'] or 0,
            'balance': float(pay_agg['total'] or 0),
        }

        self.stdout.write("\n=== VERIFICATION ===")
        self.stdout.write(f"{'Metric':<35} {'WC2 Dump':>15} {'WC3 DB':>15} {'Match':>8}")
        self.stdout.write('─' * 75)

        checks = [
            ('Unpaid invoices (count)',
             dump_audit['invoices']['unpaid_count'],
             wc3['invoices_unpaid']['count']),
            ('Unpaid invoices ($)',
             dump_audit['invoices']['unpaid_balance'],
             wc3['invoices_unpaid']['balance']),
            ('Unapplied payments (count)',
             dump_audit['payments']['unapplied_count'],
             wc3['payments_unapplied']['count']),
            ('Unapplied payments ($)',
             dump_audit['payments']['unapplied_total'],
             wc3['payments_unapplied']['balance']),
        ]
        for label, dump_val, wc3_val in checks:
            match = '✓' if abs(float(dump_val) - float(wc3_val)) < 0.01 else '✗'
            style = self.style.SUCCESS if match == '✓' else self.style.ERROR
            self.stdout.write(f"{label:<35} {dump_val:>15,.2f} {wc3_val:>15,.2f} {style(match):>8}")
