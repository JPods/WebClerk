"""After display_name became company, put the new leaf into the access lists.

    manage.py fix_company_leaf_in_access            # show what would change
    manage.py fix_company_leaf_in_access --apply

A positive list names leaves, and a renamed leaf is in no list until someone adds it
(recheck 2, R1). Migration orgs/0007 renamed the column but every `wc:model` Setting still
named `display_name`, so `company` was enumerated nowhere: invisible on GET and unwritable
on save, for every role including admin — and nothing raises. That is the whole failure
mode of a positive list, and it is why this step cannot be skipped.

Surgical on purpose. `view_edit_convert` regenerates these lists from the old rules and
would discard the rep and portal grants made since, so this touches only the leaf that moved.

Two rules:

1. **On an org model** — customer, vendor, rep, employee, manufacturer, orgbase — the bare
   leaf `display_name` is that model's own column and becomes `company`.
2. **On any model**, a denormalized link leaf `refs.links.<org>.display_name` follows the
   link template, which now reads the org's `company`.

Contact keeps its own `display_name`: it is a read-only property over `get_full_name()`, a
different thing that did not move. UserProfile likewise.

Idempotent — a list already holding `company` is left alone.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models.setting import Setting

ORG_MODELS = {'customer', 'vendor', 'rep', 'employee', 'manufacturer', 'orgbase'}
ORG_LINK_PREFIXES = tuple(f'refs.links.{m}.' for m in ORG_MODELS)


def _rename_leaf(value, is_org_model: bool):
    """Return (new_value, count) with the moved leaf renamed inside any list of strings."""
    if isinstance(value, dict):
        out, n = {}, 0
        for k, v in value.items():
            nv, c = _rename_leaf(v, is_org_model)
            out[k] = nv
            n += c
        return out, n
    if isinstance(value, list):
        out, n = [], 0
        for v in value:
            if isinstance(v, str):
                if is_org_model and v == 'display_name':
                    out.append('company'); n += 1
                elif v.startswith(ORG_LINK_PREFIXES) and v.endswith('.display_name'):
                    out.append(v[: -len('display_name')] + 'company'); n += 1
                else:
                    out.append(v)
            else:
                nv, c = _rename_leaf(v, is_org_model)
                out.append(nv); n += c
        return out, n
    return value, 0


class Command(BaseCommand):
    help = "Rename the display_name leaf to company inside wc:model access lists."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='write the changes (default: show them only)')

    def handle(self, *args, **options):
        apply_changes = options['apply']
        settings_qs = Setting.objects.filter(purpose='wc:model', is_deleted=False)

        planned, total_leaves = [], 0
        for s in settings_qs:
            config = s.config if isinstance(s.config, dict) else {}
            access = config.get('access')
            if not isinstance(access, dict):
                continue
            is_org = (s.parent_model or '').lower() in ORG_MODELS
            new_access, n = _rename_leaf(access, is_org)
            if n:
                planned.append((s, config, new_access, n))
                total_leaves += n
                self.stdout.write(f"  {s.parent_model}: {n} leaf/leaves")

        if not planned:
            self.stdout.write(self.style.SUCCESS(
                "Nothing to change — company is already named wherever display_name was."))
            return

        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                f"{len(planned)} Settings, {total_leaves} leaves would change. "
                f"Re-run with --apply."))
            return

        with transaction.atomic():
            for s, config, new_access, _n in planned:
                config['access'] = new_access
                s.config = config
                s._setting_update_authorized = True   # this command is the authorization
                s.save(update_fields=['config', 'dt_modified', 'version'])

        from apps.core.services import access as access_service
        access_service.clear_cache()

        self.stdout.write(self.style.SUCCESS(
            f"{len(planned)} Settings updated, {total_leaves} leaves renamed; access cache cleared."))
