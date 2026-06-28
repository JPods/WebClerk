"""Item cross-reference lookup service.

Find items by external identifiers: barcode, GTIN, UPC, EAN, MPN,
manufacturer SKU, or any external_sku in the ItemXRef table.
Also searches refs.codes JSON on xref records for structured code lookups.
"""
import logging
from typing import Any, Dict, List, Optional

from django.db.models import Q

logger = logging.getLogger(__name__)


def lookup_by_external_sku(
    sku: str,
    source: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Find items by external SKU (manufacturer part number, vendor SKU, etc).

    Args:
        sku: The external SKU to search for (exact match)
        source: Optional filter by source type ('manufacturer', 'wholesaler', 'other')

    Returns:
        List of dicts with item_id, item_ida, external_sku, source, source_name, is_preferred, cost
    """
    from apps.products.models import ItemXRef

    filters = Q(external_sku=sku, is_active=True, is_deleted=False)
    if source:
        filters &= Q(source=source)

    xrefs = ItemXRef.objects.filter(filters).select_related('item')

    results = []
    for xref in xrefs:
        item = xref.item
        results.append({
            'xref_id': xref.pk,
            'item_id': item.pk if item else None,
            'item_ida': getattr(item, 'ida', '') if item else '',
            'item_description': getattr(item, 'description', '') if item else '',
            'external_sku': xref.external_sku,
            'source': xref.source,
            'source_name': xref.source_name,
            'is_preferred': xref.is_preferred,
            'cost': xref.cost,
        })

    return results


def lookup_by_code(
    code: str,
    code_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Find items by structured code (GTIN, UPC, EAN, MPN, barcode).

    Searches ItemXRef.refs.codes JSON field and external_sku.

    Args:
        code: The code value to search for
        code_type: Optional — 'gtin', 'upc', 'ean', 'mpn'. If None, searches all.

    Returns:
        List of dicts with item_id, item_ida, code_type, matched_value
    """
    from apps.products.models import ItemXRef

    base_q = Q(is_active=True, is_deleted=False)

    if code_type:
        # Search specific code type in refs.codes JSON
        json_lookup = {f'refs__codes__{code_type}': code}
        xrefs = ItemXRef.objects.filter(base_q, **json_lookup).select_related('item')
    else:
        # Search all code types + external_sku
        xrefs = ItemXRef.objects.filter(
            base_q
        ).filter(
            Q(external_sku=code) |
            Q(refs__codes__gtin=code) |
            Q(refs__codes__upc=code) |
            Q(refs__codes__ean=code) |
            Q(refs__codes__mpn=code)
        ).select_related('item')

    results = []
    for xref in xrefs:
        item = xref.item
        codes = xref.get_codes()

        # Determine which code matched
        matched_type = 'external_sku'
        if code_type:
            matched_type = code_type
        else:
            for ct in ('gtin', 'upc', 'ean', 'mpn'):
                if codes.get(ct) == code:
                    matched_type = ct
                    break

        results.append({
            'xref_id': xref.pk,
            'item_id': item.pk if item else None,
            'item_ida': getattr(item, 'ida', '') if item else '',
            'item_description': getattr(item, 'description', '') if item else '',
            'code_type': matched_type,
            'matched_value': code,
            'all_codes': codes,
            'source': xref.source,
            'source_name': xref.source_name,
        })

    return results


def find_item_by_any_identifier(identifier: str) -> Optional[Dict[str, Any]]:
    """Try to find a single item by any identifier — SKU, barcode, GTIN, UPC, etc.

    Searches in order: Item.ida, ItemXRef.external_sku, ItemXRef.refs.codes.
    Returns the first match, preferring is_preferred xrefs.

    Args:
        identifier: Any product identifier string

    Returns:
        Dict with item_id, item_ida, matched_via, or None if not found
    """
    from apps.products.models import Item

    # 1. Try Item.ida directly
    item = Item.objects.filter(ida=identifier, is_active=True, is_deleted=False).first()
    if item:
        return {
            'item_id': item.pk,
            'item_ida': item.ida,
            'item_description': getattr(item, 'description', ''),
            'matched_via': 'ida',
        }

    # 2. Try external_sku
    sku_results = lookup_by_external_sku(identifier)
    if sku_results:
        preferred = next((r for r in sku_results if r['is_preferred']), sku_results[0])
        preferred['matched_via'] = f"xref:{preferred['source']}"
        return preferred

    # 3. Try structured codes
    code_results = lookup_by_code(identifier)
    if code_results:
        result = code_results[0]
        result['matched_via'] = f"code:{result['code_type']}"
        return result

    return None
