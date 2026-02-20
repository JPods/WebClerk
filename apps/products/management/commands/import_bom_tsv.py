from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.products.models.bill_of_material import BillOfMaterial
from apps.products.models.item import Item

logger = logging.getLogger(__name__)


@dataclass
class ImportStats:
    created: int = 0
    updated: int = 0
    skipped_missing_parent: int = 0
    skipped_missing_component: int = 0
    skipped_invalid_qty: int = 0
    errors: int = 0


class Command(BaseCommand):
    help = "Import BOM component rows from a tab-delimited file into BillOfMaterial"

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument("path", help="Path to the tab-delimited BOM export")
        parser.add_argument("--limit", type=int, default=None, help="Optional row limit")
        parser.add_argument("--offset", type=int, default=0, help="Rows to skip from the start")
        parser.add_argument("--dry-run", action="store_true", help="Parse and report without saving")

    # ---------- parsing helpers ----------------------------------------
    def _clean_str(self, value: Optional[str]) -> str:
        if value is None:
            return ""
        return " ".join(value.replace("\r", " ").replace("\n", " ").split()).strip()

    def _as_decimal(self, value: Optional[str]) -> Optional[Decimal]:
        raw = self._clean_str(value)
        if not raw:
            return None
        normalized = raw.replace(",", "").replace("$", "")
        try:
            return Decimal(normalized)
        except InvalidOperation:
            return None

    def _as_int(self, value: Optional[str]) -> Optional[int]:
        raw = self._clean_str(value)
        if not raw:
            return None
        try:
            return int(Decimal(raw))
        except (InvalidOperation, ValueError):
            return None

    def _iter_rows(self, path: Path) -> Iterable[Dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if not reader.fieldnames:
                raise CommandError("TSV header missing")
            for row in reader:
                yield row

    def _resolve_item(self, sku: str) -> Optional[Item]:
        if not sku:
            return None
        return Item.objects.filter(sku__iexact=sku).first()

    def _compose_change_reason(self, comment: str, description: str) -> str:
        merged = (comment or description or "").strip()
        if not merged:
            return ""
        return merged[:120]

    def _build_op_payload(self, row: Dict[str, str]) -> Dict[str, object]:
        payload: Dict[str, object] = {}
        comment = self._clean_str(row.get("Comment"))
        description = self._clean_str(row.get("Description"))
        if comment:
            payload["comment"] = comment
        if description:
            payload["description"] = description
        key_text = self._clean_str(row.get("KeyText"))
        if key_text:
            payload["key_text"] = key_text
        uuid = self._clean_str(row.get("UUIDKey"))
        if uuid:
            payload["uuid"] = uuid
        plan_ext = self._as_decimal(row.get("PlanExtCost"))
        if plan_ext is not None:
            payload["plan_ext_cost"] = float(plan_ext)
        dt_last_sync = self._clean_str(row.get("dtLastSync"))
        if dt_last_sync:
            payload["dt_last_sync"] = dt_last_sync
        dt_sync = self._clean_str(row.get("DTSync"))
        if dt_sync:
            payload["dt_sync"] = dt_sync
        return payload

    def _process_row(self, row: Dict[str, str], index: int) -> Tuple[Optional[BillOfMaterial], Optional[str]]:
        parent_sku = self._clean_str(row.get("ItemNum"))
        component_sku = self._clean_str(row.get("ChildItem"))
        if not parent_sku:
            return None, "missing_parent"
        if not component_sku:
            return None, "missing_component"

        parent_item = self._resolve_item(parent_sku)
        if parent_item is None:
            return None, "missing_parent"

        component_item = self._resolve_item(component_sku)
        if component_item is None:
            return None, "missing_component"

        qty = self._as_decimal(row.get("QtyInAssembly"))
        if qty is None or qty <= 0:
            return None, "invalid_qty"

        plan_cost = self._as_decimal(row.get("PlanCost"))
        sequence = self._as_int(row.get("UniqueID"))
        if sequence is None:
            sequence = index

        bom = BillOfMaterial.objects.filter(parent_item=parent_item, child_item=component_item).first()
        created = False
        if bom is None:
            bom = BillOfMaterial(parent_item=parent_item, child_item=component_item)
            created = True

        bom.quantity = qty
        bom.sequence = sequence or 0
        if plan_cost is not None:
            bom.cost_snapshot = plan_cost
        change_reason = self._compose_change_reason(self._clean_str(row.get("Comment")), self._clean_str(row.get("Description")))
        if change_reason:
            bom.change_reason = change_reason

        op_data = bom.op_data if isinstance(bom.op_data, dict) else {}
        op_data.setdefault("legacy", {})
        legacy_bucket = op_data["legacy"]
        if not isinstance(legacy_bucket, dict):
            legacy_bucket = {}
        for key, value in self._build_op_payload(row).items():
            legacy_bucket[key] = value
        op_data["legacy"] = legacy_bucket
        bom.op_data = op_data

        return bom, "created" if created else "updated"

    # ---------- entry point --------------------------------------------
    def handle(self, *args, **options):  # pragma: no cover
        path = Path(options["path"]).expanduser()
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        limit = options.get("limit")
        offset = options.get("offset") or 0
        dry_run = options.get("dry_run", False)

        stats = ImportStats()
        rows_processed = 0

        iterator = self._iter_rows(path)
        for idx, row in enumerate(iterator, start=1):
            if idx <= offset:
                continue
            if limit is not None and rows_processed >= limit:
                break

            try:
                bom, status = self._process_row(row, idx)
            except Exception as exc:  # pragma: no cover
                stats.errors += 1
                logger.exception("Failed processing row %s", idx)
                self.stderr.write(f"Row {idx}: {exc}")
                continue

            if bom is None:
                if status == "missing_parent":
                    stats.skipped_missing_parent += 1
                elif status == "missing_component":
                    stats.skipped_missing_component += 1
                elif status == "invalid_qty":
                    stats.skipped_invalid_qty += 1
                else:
                    stats.errors += 1
                continue

            rows_processed += 1

            if dry_run:
                if status == "created":
                    stats.created += 1
                else:
                    stats.updated += 1
                continue

            with transaction.atomic():
                bom.save()

            if status == "created":
                stats.created += 1
            else:
                stats.updated += 1

        summary = (
            f"Processed {rows_processed} rows (created={stats.created}, updated={stats.updated}, "
            f"missing_parent={stats.skipped_missing_parent}, missing_component={stats.skipped_missing_component}, "
            f"invalid_qty={stats.skipped_invalid_qty}, errors={stats.errors})."
        )
        self.stdout.write(self.style.SUCCESS(summary))