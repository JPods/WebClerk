from __future__ import annotations

import csv
import logging
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.products.models.item import (
    Item,
    default_cost,
    default_price,
    ensure_item_prefs,
)
from apps.products.uom import normalize_uom

logger = logging.getLogger(__name__)


@dataclass
class ImportStats:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0


class Command(BaseCommand):
    help = "Import TSV item data into Item model, preserving unmapped fields in prefs.import."

    def add_arguments(self, parser):  # pragma: no cover - CLI wiring
        parser.add_argument(
            "path",
            help="Path to the tab-delimited file to import",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Optional limit on rows to process (for testing).",
        )
        parser.add_argument(
            "--offset",
            type=int,
            default=0,
            help="Optional starting row offset (0-indexed).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and log without saving changes.",
        )

    # --------- Helpers -------------------------------------------------
    def _clean_str(self, value: str | None) -> str:
        if value is None:
            return ""
        # Replace control breaks and condense whitespace
        cleaned = " ".join(value.replace("\r", " ").replace("\n", " ").split())
        return cleaned.strip()

    def _clean_str_preserve_breaks(self, value: str | None) -> str:
        if value is None:
            return ""
        value = value.replace("\r", "\n")
        return "\n".join(" ".join(chunk.split()) for chunk in value.split("\n")).strip()

    def _as_decimal(self, value: str | None) -> Decimal | None:
        raw = self._clean_str(value)
        if not raw:
            return None
        normalized = (
            raw.replace(",", "")
            .replace("$", "")
            .replace("%", "")
            .replace("+", "")
        )
        try:
            return Decimal(normalized)
        except InvalidOperation:
            return None

    def _as_float(self, value: str | None) -> float | None:
        dec = self._as_decimal(value)
        if dec is None:
            return None
        return float(dec)

    def _as_int(self, value: str | None) -> int | None:
        dec = self._as_decimal(value)
        if dec is None:
            return None
        try:
            return int(dec)
        except (ValueError, OverflowError):  # pragma: no cover - defensive
            return None

    def _as_bool(self, value: str | None) -> bool | None:
        raw = self._clean_str(value).lower()
        if not raw:
            return None
        if raw in {"1", "true", "t", "yes", "y"}:
            return True
        if raw in {"0", "false", "f", "no", "n"}:
            return False
        return None

    def _iter_rows(self, path: Path) -> Iterable[Dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if not reader.fieldnames:
                raise CommandError("TSV header row missing or unreadable.")
            for row in reader:
                yield row

    def _update_price(self, item: Item, row: Dict[str, str], used_keys: set[str]):
        price = item.price if isinstance(item.price, dict) else default_price()
        tiers: List[Dict[str, Decimal]] = []

        base_price = self._as_decimal(row.get("PriceA"))
        used_keys.add("PriceA")
        if base_price is not None:
            price["base"] = float(base_price)

        msrp = self._as_decimal(row.get("PriceMSR"))
        used_keys.add("PriceMSR")
        if msrp is not None:
            price["msrp"] = float(msrp)

        for column, level in (("PriceB", "B"), ("PriceC", "C"), ("PriceD", "D")):
            used_keys.add(column)
            tier_val = self._as_decimal(row.get(column))
            if tier_val is not None:
                tiers.append({"level": level, "price": float(tier_val)})

        price["tiers"] = tiers
        item.price = price

    def _update_cost(self, item: Item, row: Dict[str, str], used_keys: set[str]):
        cost = item.cost if isinstance(item.cost, dict) else default_cost()
        avg = self._as_decimal(row.get("CostAverage"))
        used_keys.add("CostAverage")
        if avg is not None:
            cost["avg"] = float(avg)
            if cost.get("standard") is None:
                cost["standard"] = float(avg)
        last = self._as_decimal(row.get("CostLastInShip"))
        used_keys.add("CostLastInShip")
        if last is not None:
            cost["last"] = float(last)
        landed = self._as_decimal(row.get("CostMSC"))
        used_keys.add("CostMSC")
        if landed is not None:
            cost["landed"] = float(landed)
        item.cost = cost

    def _update_quantity(self, item: Item, row: Dict[str, str], used_keys: set[str]):
        qty = {} if not isinstance(item.quantity, dict) else dict(item.quantity)
        mapping: List[Tuple[str, str]] = [
            ("on_hand", "QtyOnHand"),
            ("allocated", "QtyAllocated"),
            ("available", "QtyAvailable"),
            ("on_order", "QtyOnPOs"),
        ]
        for key, column in mapping:
            used_keys.add(column)
            val = self._as_float(row.get(column))
            if val is not None:
                qty[key] = val
        item.quantity = qty

    def _update_flags(self, item: Item, row: Dict[str, str], used_keys: set[str]):
        flags = {} if not isinstance(item.flags, dict) else dict(item.flags)
        mapping = {
            "BackOrder": "back_order_allowed",
            "Discountable": "discountable",
            "Linked": "linked",
            "NotTracked": "not_tracked",
            "Pacing": "pacing",
            "Serialized": "serialized",
            "TallyByType": "tally_by_type",
            "PrintNot": "print_suppressed",
        }
        for column, flag_key in mapping.items():
            used_keys.add(column)
            b = self._as_bool(row.get(column))
            if b is not None:
                flags[flag_key] = b
        item.flags = flags

    def _update_gl_accounts(self, item: Item, row: Dict[str, str], used_keys: set[str]):
        gls = {} if not isinstance(item.gls, dict) else dict(item.gls)
        pairs = {
            "InventoryGLAccount": "inventory",
            "CostGLAccount": "cost",
            "CostofSales": "cogs",
            "SalesGLAccount": "revenue",
        }
        for column, key in pairs.items():
            used_keys.add(column)
            value = self._clean_str(row.get(column))
            if value:
                gls[key] = value
        item.gls = gls

    def _update_tax(self, item: Item, row: Dict[str, str], used_keys: set[str]):
        tax_code = {} if not isinstance(item.tax_code, dict) else dict(item.tax_code)
        tax_val = self._clean_str(row.get("TaxID"))
        used_keys.add("TaxID")
        if tax_val:
            tax_code["code"] = tax_val
        item.tax_code = tax_code

    def _compose_description(self, row: Dict[str, str], used_keys: set[str]) -> str:
        parts: List[str] = []
        for column in ("Description", "LIComment", "RelatedDetails"):
            used_keys.add(column)
            text = self._clean_str_preserve_breaks(row.get(column))
            if text:
                parts.append(text)
        combo = "\n\n".join(parts).strip()
        return combo[:2000]  # cap to reasonable length

    def _normalize_name(self, value: str) -> str:
        return value[:160] if len(value) > 160 else value

    def _populate_prefs_import(
        self,
        item: Item,
        row: Dict[str, str],
        used_keys: set[str],
        source_name: str,
    ) -> None:
        prefs = ensure_item_prefs(getattr(item, "prefs", None))
        import_bucket = prefs.setdefault("import", {})
        import_bucket["source"] = source_name
        import_bucket["legacy_item_id"] = row.get("ItemNum")

        # Preserve select fields with canonical keys for downstream reconciliation
        for column, key in (
            ("UUIDKey", "uuid"),
            ("MfrItemNum", "mfr_item"),
            ("MfrName", "mfr_name"),
            ("Menu", "menu"),
            ("Class", "class"),
            ("Division", "division"),
            ("Profile1", "profile1"),
            ("Profile2", "profile2"),
            ("Profile3", "profile3"),
            ("Profile4", "profile4"),
            ("Profile5", "profile5"),
            ("Profile6", "profile6"),
            ("TypeID", "type_id"),
            ("TemplateName", "template"),
            ("Objectives", "objectives"),
        ):
            used_keys.add(column)
            value = self._clean_str(row.get(column))
            if value:
                import_bucket[key] = value

        # Capture paths and media references
        for column, key in (
            ("ImagePath", "image"),
            ("ImagePathTN", "image_thumbnail"),
            ("URL", "url"),
            ("WebPage", "web_page"),
        ):
            used_keys.add(column)
            value = self._clean_str(row.get(column))
            if value:
                import_bucket.setdefault("media", {})[key] = value

        # Collect all remaining unmapped non-empty columns for forensic review
        residual = {
            column: value
            for column, value in row.items()
            if column not in used_keys and self._clean_str(value)
        }
        if residual:
            import_bucket["residual"] = residual

        item.prefs = prefs

    def _process_row(
        self,
        row: Dict[str, str],
        source_name: str,
    ) -> Tuple[Item | None, bool, Iterable[str]]:
        used_keys: set[str] = set()
        sku = self._clean_str(row.get("ItemNum"))
        used_keys.add("ItemNum")
        if not sku:
            return None, False, used_keys

        # Find existing item case-insensitively
        item = Item.objects.filter(sku__iexact=sku).first()
        created = False
        if item is None:
            item = Item(sku=sku, kind=Item.KIND_PHYSICAL)
            created = True
        elif not getattr(item, "kind", None):
            item.kind = Item.KIND_PHYSICAL

        name_value = self._normalize_name(self._clean_str(row.get("Description")) or sku)
        used_keys.add("Description")
        if name_value:
            item.name = name_value

        item.description = self._compose_description(row, used_keys) or item.description

        uom = self._clean_str(row.get("UnitOfMeasure"))
        used_keys.add("UnitOfMeasure")
        if uom:
            normalized_uom = normalize_uom(uom)
            item.uom = normalized_uom
            if not item.base_uom:
                item.base_uom = normalized_uom

        self._update_price(item, row, used_keys)
        self._update_cost(item, row, used_keys)
        self._update_quantity(item, row, used_keys)
        self._update_flags(item, row, used_keys)
        self._update_gl_accounts(item, row, used_keys)
        self._update_tax(item, row, used_keys)

        spec_id = self._as_int(row.get("SpecID"))
        used_keys.add("SpecID")
        if spec_id is not None:
            item.specification_id = spec_id

        self._populate_prefs_import(item, row, used_keys, source_name)

        # Weight hints stored in prefs.import since Item has no direct field
        for column, key in (("WeightAverage", "weight_avg"), ("WeightBulk", "weight_bulk")):
            used_keys.add(column)
            value = self._as_float(row.get(column))
            if value is not None:
                item.prefs.setdefault("import_details", {})[key] = value

        return item, created, used_keys

    # --------- Main pipeline -------------------------------------------
    def handle(self, *args, **options):  # pragma: no cover - CLI entrypoint
        path = Path(options["path"]).expanduser()
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        limit = options.get("limit")
        offset = options.get("offset") or 0
        dry_run = options.get("dry_run", False)
        stats = ImportStats()
        source_name = path.name

        rows_processed = 0
        residual_columns = defaultdict(int)

        try:
            iterator = self._iter_rows(path)
            for index, raw_row in enumerate(iterator):
                if index < offset:
                    continue
                if limit is not None and rows_processed >= limit:
                    break

                try:
                    item, created, used_keys = self._process_row(raw_row, source_name)
                except Exception as exc:  # pragma: no cover - defensive
                    stats.errors += 1
                    logger.exception("Failed processing row %s", index + 1)
                    self.stderr.write(f"Row {index + 1}: {exc}")
                    continue

                if item is None:
                    stats.skipped += 1
                    continue

                for column in raw_row.keys():
                    if column in used_keys:
                        continue
                    if self._clean_str(raw_row.get(column)):
                        residual_columns[column] += 1

                rows_processed += 1

                if dry_run:
                    if created:
                        stats.created += 1
                    else:
                        stats.updated += 1
                    continue

                with transaction.atomic():
                    item.save()
                if created:
                    stats.created += 1
                else:
                    stats.updated += 1

        except csv.Error as exc:
            raise CommandError(f"CSV parsing error: {exc}")

        self.stdout.write(self.style.SUCCESS(
            f"Processed {rows_processed} rows (created={stats.created}, updated={stats.updated}, skipped={stats.skipped}, errors={stats.errors})."
        ))
        if residual_columns:
            top_columns = sorted(residual_columns.items(), key=lambda kv: kv[1], reverse=True)[:15]
            summary = ", ".join(f"{col}:{count}" for col, count in top_columns)
            self.stdout.write(f"Top residual columns: {summary}")