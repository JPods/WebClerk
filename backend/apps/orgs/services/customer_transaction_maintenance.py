from __future__ import annotations

import random
from typing import Any

from django.apps import apps

from apps.orgs.models import OrgBase


def maintain_customer_transaction_links(
    *,
    target_customer_ids: list[int] | None = None,
    assign_missing: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Reconcile customer links between transactions and customer refs.

    Behavior:
    - For transaction models that have a `customer` FK, ensure each row has
      `refs.links.customer` containing its customer id.
    - For each linked row, ensure the customer record has `refs.links.<model>`
      containing the transaction id.
    - Optionally assign missing `customer_id` randomly from target ids.
    """
    targets = target_customer_ids or [82, 84, 86]
    customers = {o.id: o for o in OrgBase.objects.filter(id__in=targets)}
    missing_target_customers = [cid for cid in targets if cid not in customers]
    if missing_target_customers:
        raise ValueError(f"Missing required customer ids: {missing_target_customers}")

    summary: dict[str, Any] = {
        "models_scanned": 0,
        "rows_missing_assigned": 0,
        "rows_existing_customer": 0,
        "tx_refs_updated": 0,
        "customer_refs_updated": 0,
        "per_model": {},
    }

    tx_app = apps.get_app_config("transactions")
    for model in tx_app.get_models():
        field_names = {f.name for f in model._meta.get_fields()}
        if "customer" not in field_names:
            continue

        summary["models_scanned"] += 1
        model_name = model._meta.model_name

        model_missing = 0
        model_existing = 0
        model_tx_refs = 0
        model_customer_refs = 0

        for obj in model.objects.all().only("id", "customer_id", "refs").iterator(chunk_size=500):
            cid = getattr(obj, "customer_id", None)
            assigned = False

            if not cid:
                if assign_missing:
                    cid = random.choice(targets)
                    obj.customer_id = cid
                    assigned = True
                    model_missing += 1
                else:
                    continue
            else:
                model_existing += 1

            refs = obj.refs if isinstance(obj.refs, dict) else {}
            links = refs.get("links") if isinstance(refs.get("links"), dict) else {}
            bucket = links.get("customer") if isinstance(links.get("customer"), list) else []

            has_tx_link = any(
                (isinstance(item, int) and item == cid)
                or (isinstance(item, dict) and item.get("id") == cid)
                for item in bucket
            )

            tx_refs_changed = False
            if cid and not has_tx_link:
                cobj = customers.get(cid)
                bucket.append(
                    {
                        "id": cid,
                        "company": getattr(cobj, "company", "") if cobj else "",
                        "org_type": getattr(cobj, "org_type", "customer") if cobj else "customer",
                    }
                )
                links["customer"] = bucket
                refs["links"] = links
                obj.refs = refs
                tx_refs_changed = True
                model_tx_refs += 1

            if (assigned or tx_refs_changed) and not dry_run:
                obj.save(update_fields=["customer", "refs", "dt_modified"])

            if cid:
                cobj = customers.get(cid)
                if cobj:
                    crefs = cobj.refs if isinstance(cobj.refs, dict) else {}
                    clinks = crefs.get("links") if isinstance(crefs.get("links"), dict) else {}
                    tx_bucket = clinks.get(model_name) if isinstance(clinks.get(model_name), list) else []
                    has_customer_link = any(
                        (isinstance(item, int) and item == obj.id)
                        or (isinstance(item, dict) and item.get("id") == obj.id)
                        for item in tx_bucket
                    )
                    if not has_customer_link:
                        tx_bucket.append({"id": obj.id})
                        clinks[model_name] = tx_bucket
                        crefs["links"] = clinks
                        cobj.refs = crefs
                        if not dry_run:
                            cobj.save(update_fields=["refs", "dt_modified"])
                        model_customer_refs += 1

        summary["rows_missing_assigned"] += model_missing
        summary["rows_existing_customer"] += model_existing
        summary["tx_refs_updated"] += model_tx_refs
        summary["customer_refs_updated"] += model_customer_refs
        summary["per_model"][model_name] = {
            "assigned_missing": model_missing,
            "existing_customer": model_existing,
            "tx_refs_updated": model_tx_refs,
            "customer_refs_updated": model_customer_refs,
        }

    return summary
