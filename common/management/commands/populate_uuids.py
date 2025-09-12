from __future__ import annotations

import uuid
from typing import Any
import os
import json
from datetime import datetime, timezone
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from django.db import transaction


class Command(BaseCommand):
    help = (
        "Populate UUIDs for a subset of records on a given model. "
        "Default: only fill rows where uuid is NULL using UUIDv4. "
        "Optionally use deterministic UUIDv5 from a namespace+key, and/or overwrite existing UUIDs (with confirmations).\n\n"
        "Examples:\n"
        "  # Fill null UUIDs with v4 for active items (preview)\n"
        "  python manage.py populate_uuids --model products.Item --filter 'is_active=True' --limit 100 --dry-run\n\n"
        "  # Deterministic v5 using DNS namespace and sku field as key (execute with confirmation)\n"
        "  python manage.py populate_uuids --model products.Item --strategy v5 --namespace dns --key-field sku --yes\n\n"
        "  # Overwrite existing UUIDs for a filtered subset only (requires --yes)\n"
        "  python manage.py populate_uuids --model transactions.Proposal --filter 'status=OPEN' --overwrite --yes\n\n"
        "  # Global overwrite requires explicit allow flag\n"
        "  python manage.py populate_uuids --model core.Contact --overwrite --allow-overwrite-all --yes\n"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            required=True,
            help="Dotted app_label.ModelName or app_label.ModelName (e.g., products.Item)",
        )
        parser.add_argument(
            "--filter",
            help="Django ORM filter expression (e.g., 'is_active=True,kind=physical')",
        )
        parser.add_argument(
            "--where-sql",
            help=(
                "Raw SQL WHERE predicate to further restrict rows. Example: "
                "\"status IN ('OPEN','HOLD') AND total > 0\". "
                "This is ANDed with other filters by selecting matching primary keys first."
            ),
        )
        parser.add_argument(
            "--ids",
            help="Comma-separated list of primary key IDs to include (applied after filter if both provided)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Max number of rows to process",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing",
        )
        parser.add_argument(
            "--commit-chunk",
            type=int,
            default=500,
            help="Commit every N rows (default 500)",
        )
        parser.add_argument(
            "--strategy",
            choices=["v4", "v5"],
            default="v4",
            help="UUID generation strategy: v4 (random) or v5 (namespace+key deterministic). Default v4",
        )
        parser.add_argument(
            "--namespace",
            help="Namespace for UUIDv5: one of dns|url|oid|x500 or a UUID string (required when --strategy v5)",
        )
        parser.add_argument(
            "--key-field",
            help="Model field name to use as the v5 key (fallback to pk if omitted and no template)",
        )
        parser.add_argument(
            "--key-template",
            help="Python format template for v5 key; placeholders are model field names, e.g., '{id}:{sku}'",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing UUIDs as well (by default only fills NULLs). USE WITH CARE",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Confirm execution (required for non-dry-run)",
        )
        parser.add_argument(
            "--allow-overwrite-all",
            action="store_true",
            help="Allow overwrite of all rows when no filter/ids provided (dangerous). Requires --overwrite and --yes",
        )
        parser.add_argument(
            "--sample",
            type=int,
            default=10,
            help="How many example IDs to show in dry-run preview (default 10)",
        )
        parser.add_argument(
            "--audit-file",
            help=(
                "Path to write an NDJSON audit log of changes. If omitted, a file will be created under "
                "'local/audit/populate_uuids/{model}_{timestamp}.ndjson'."
            ),
        )

    def _resolve_model(self, model_path: str):
        # Accept formats like 'products.Item' or 'apps.products.models.Item' but prefer app_label.ModelName
        if "." not in model_path:
            raise CommandError("--model must be in the form 'app_label.ModelName'")
        parts = model_path.split(".")
        if len(parts) == 2:
            app_label, model_name = parts
        else:
            # Try last two parts as app_label and model_name
            app_label, model_name = parts[-2], parts[-1]
        try:
            return apps.get_model(app_label, model_name)
        except LookupError:
            raise CommandError(f"Unknown model: {model_path}")

    def _parse_filter(self, filt: str | None) -> dict[str, Any]:
        if not filt:
            return {}
        out: dict[str, Any] = {}
        for clause in filt.split(","):
            clause = clause.strip()
            if not clause:
                continue
            if "=" not in clause:
                raise CommandError(f"Invalid filter clause '{clause}'. Use key=value pairs separated by commas.")
            k, v = clause.split("=", 1)
            k = k.strip()
            v = v.strip()
            # Convert common literals
            if v.lower() in {"true", "false"}:
                v = v.lower() == "true"
            elif v.isdigit():
                v = int(v)
            out[k] = v
        return out

    def _resolve_namespace(self, ns: str | None) -> uuid.UUID | None:
        if not ns:
            return None
        ns_lower = ns.strip().lower()
        if ns_lower == "dns":
            return uuid.NAMESPACE_DNS
        if ns_lower == "url":
            return uuid.NAMESPACE_URL
        if ns_lower == "oid":
            return uuid.NAMESPACE_OID
        if ns_lower == "x500":
            return uuid.NAMESPACE_X500
        # Attempt parse as UUID
        try:
            return uuid.UUID(ns)
        except Exception as e:
            raise CommandError(f"Invalid --namespace value '{ns}': {e}")

    def _row_field_dict(self, obj) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for f in getattr(obj._meta, 'fields', []):
            try:
                data[f.name] = getattr(obj, f.name)
            except Exception:
                data[f.name] = None
        return data

    def handle(self, *args, **options):
        model_path: str = options["model"]
        ids_raw: str | None = options.get("ids")
        filt_raw: str | None = options.get("filter")
        where_sql: str | None = options.get("where_sql")
        limit: int | None = options.get("limit")
        dry_run: bool = bool(options.get("dry_run"))
        commit_chunk: int = int(options.get("commit_chunk") or 500)
        strategy: str = options.get("strategy") or "v4"
        namespace_opt: str | None = options.get("namespace")
        key_field: str | None = options.get("key_field")
        key_template: str | None = options.get("key_template")
        overwrite: bool = bool(options.get("overwrite"))
        confirm_yes: bool = bool(options.get("yes"))
        allow_overwrite_all: bool = bool(options.get("allow_overwrite_all"))
        sample_n: int = int(options.get("sample") or 10)
        audit_file: str | None = options.get("audit_file")

        Model = self._resolve_model(model_path)
        if not hasattr(Model, "uuid"):
            raise CommandError(f"Model {Model.__name__} has no 'uuid' field")

        # Strategy validations
        ns_uuid = None
        if strategy == "v5":
            ns_uuid = self._resolve_namespace(namespace_opt)
            if ns_uuid is None:
                raise CommandError("--namespace is required when --strategy v5 (dns|url|oid|x500 or a UUID)")

        filters = self._parse_filter(filt_raw)
        qs_base = Model.objects.filter(**filters)

        # Apply raw SQL WHERE predicate by selecting PKs first, then AND via pk__in
        if where_sql:
            from django.db import connection

            table = Model._meta.db_table
            pk_field = getattr(Model._meta, "pk", None)
            if pk_field is None:
                pk_col = "id"
            else:
                pk_col = getattr(pk_field, "column", None) or getattr(pk_field, "attname", "id")
            sql = f"SELECT {pk_col} FROM {table} WHERE {where_sql}"
            if limit:
                sql = f"{sql} LIMIT {int(limit)}"
            try:
                with connection.cursor() as cur:
                    cur.execute(sql)
                    rows = cur.fetchall()
                where_ids = [r[0] for r in rows]
            except Exception as e:
                raise CommandError(f"Error executing --where-sql: {e}")
            if not where_ids:
                self.stdout.write(self.style.WARNING("No rows matched --where-sql predicate."))
                return
            qs_base = qs_base.filter(pk__in=where_ids)
        if overwrite:
            qs = qs_base
        else:
            qs = qs_base.filter(uuid__isnull=True)
        if ids_raw:
            try:
                ids = [int(pk.strip()) for pk in ids_raw.split(",") if pk.strip()]
                qs = qs.filter(pk__in=ids)
            except ValueError:
                raise CommandError("--ids must be a comma-separated list of integers")
        if limit and not where_sql:
            # If where_sql was used, we may have already limited via SQL; avoid double-limiting unpredictably
            qs = qs.order_by("pk")[:limit]

        total = qs.count()
        if total == 0:
            msg = "No rows matched the criteria."
            if not overwrite:
                msg = "No rows with NULL uuid matched the criteria."
            self.stdout.write(self.style.WARNING(msg))
            return

        # Summary & warnings
        mode_desc = "overwrite" if overwrite else "fill-null"
        strat_desc = f"{strategy}"
        if strategy == "v5":
            strat_desc += f" ns={namespace_opt or ''} key={'template' if key_template else (key_field or 'pk')}"
        self.stdout.write(
            self.style.WARNING(
                f"About to {mode_desc} UUIDs for {total} {Model.__name__} rows using {strat_desc}."
            )
        )
        # Guardrails
        if not dry_run and not confirm_yes:
            raise CommandError("Refusing to execute without --yes. Re-run with --yes after reviewing the summary above.")
        if overwrite and not (ids_raw or filt_raw or limit) and not allow_overwrite_all:
            raise CommandError(
                "Global overwrite without filters is dangerous. Provide --filter/--ids/--limit or pass --allow-overwrite-all to proceed."
            )
        # Dry-run preview
        example = list(qs.values_list("pk", flat=True)[:sample_n])
        self.stdout.write(self.style.NOTICE(f"Sample IDs: {example}{' (dry-run)' if dry_run else ''}"))
        if dry_run:
            return

        # Prepare audit logging
        run_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc)
        default_dir = os.path.join("local", "audit", "populate_uuids")
        os.makedirs(default_dir, exist_ok=True)
        default_name = f"{Model._meta.label_lower.replace('.', '_')}_{ts.strftime('%Y%m%dT%H%M%SZ')}.ndjson"
        audit_path = audit_file or os.path.join(default_dir, default_name)
        try:
            audit_fh = open(audit_path, "w", encoding="utf-8")
        except Exception as e:
            raise CommandError(f"Unable to open audit file '{audit_path}': {e}")

        # Write run metadata header line
        run_meta = {
            "type": "run",
            "run_id": run_id,
            "ts": ts.isoformat(),
            "model": Model._meta.label,
            "mode": "overwrite" if overwrite else "fill-null",
            "strategy": strategy,
            "namespace": namespace_opt if strategy == "v5" else None,
            "key_field": key_field,
            "key_template": key_template,
            "filters": filters,
            "where_sql": where_sql,
            "ids": ids_raw,
            "limit": limit,
        }
        audit_fh.write(json.dumps(run_meta) + "\n")

        updated = 0
        buf = []
        with transaction.atomic():
            for obj in qs.iterator(chunk_size=commit_chunk):
                # Decide whether this row should be updated in current mode
                cur_uuid = getattr(obj, "uuid", None)
                if not overwrite and cur_uuid is not None:
                    continue
                # Compute new UUID
                if strategy == "v5":
                    # Determine key
                    key: str
                    field_map = self._row_field_dict(obj)
                    if key_template:
                        try:
                            key = str(key_template.format(**field_map))
                        except Exception as e:
                            raise CommandError(f"Error applying --key-template to id={obj.pk}: {e}")
                    elif key_field:
                        try:
                            key = str(getattr(obj, key_field))
                        except Exception:
                            raise CommandError(f"Row id={obj.pk} missing field '{key_field}' for key derivation")
                    else:
                        key = str(getattr(obj, 'pk'))
                    new_uuid = uuid.uuid5(ns_uuid, key)  # type: ignore[arg-type]
                    used_key = key
                else:
                    new_uuid = uuid.uuid4()
                    used_key = None

                setattr(obj, "uuid", new_uuid)
                buf.append(obj)
                # audit row
                row = {
                    "type": "row",
                    "run_id": run_id,
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "model": Model._meta.label,
                    "pk": obj.pk,
                    "old_uuid": str(cur_uuid) if cur_uuid else None,
                    "new_uuid": str(new_uuid),
                    "strategy": strategy,
                    "namespace": namespace_opt if strategy == "v5" else None,
                    "key": used_key,
                    "overwrite": overwrite,
                }
                audit_fh.write(json.dumps(row) + "\n")
                if len(buf) >= commit_chunk:
                    Model.objects.bulk_update(buf, ["uuid"])  # type: ignore[arg-type]
                    updated += len(buf)
                    buf.clear()
            if buf:
                Model.objects.bulk_update(buf, ["uuid"])  # type: ignore[arg-type]
                updated += len(buf)

        try:
            audit_fh.flush()
            audit_fh.close()
        except Exception:
            pass

        self.stdout.write(self.style.SUCCESS(f"Assigned UUIDs to {updated} rows."))
