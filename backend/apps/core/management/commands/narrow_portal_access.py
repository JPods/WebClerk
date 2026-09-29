"""Set the customer and buyer blocks on every model to PORTAL_CUSTOMER_ACCESS.

Bill, 2026-09-28: customers order, pay and ask for support — plus their own contact, their
own customer record, their quotes and invoices, and the published catalog with images. A
model not in the table loses its customer and buyer blocks: no block, no rows. The same
table seeds a new install (access.default_access); this command brings an existing
database, and the seed bundles, to it.

    manage.py narrow_portal_access                       # show what would change
    manage.py narrow_portal_access --apply               # write the wc:model Settings
    manage.py narrow_portal_access --bundle init-bundle.json --apply   # rewrite a bundle
"""
import json
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.core.services import access


def narrowed_roles(key: str, acc: dict) -> dict:
    """The model's roles with the customer and buyer blocks set from the table."""
    roles = dict(acc.get('roles') or {})
    block = access.portal_customer_block(key)
    for role in access.PORTAL_ORDER_ROLES:
        if block is None:
            roles.pop(role, None)
            continue
        mine = dict(block)
        if '@customer_view' in mine['view'] and 'customer_view' not in (acc.get('sets') or {}):
            mine['view'] = (['id', 'ida', 'status', 'dt_created'] + mine['edit']
                            + [p for p in mine['view'] if p != '@customer_view'])
        roles[role] = mine
    return roles


class Command(BaseCommand):
    help = "Set customer/buyer access to the portal table (dry run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write the changes.')
        parser.add_argument('--bundle', help='Rewrite this bundle file instead of the database.')

    def handle(self, *args, **options):
        if options.get('bundle'):
            return self._bundle(Path(options['bundle']), options['apply'])
        from apps.core.models.setting import Setting
        changed = 0
        for setting in Setting.objects.filter(purpose='wc:model').order_by('parent_model', 'pk'):
            config = dict(setting.config or {})
            acc = dict(config.get('access') or {})
            roles = narrowed_roles(setting.parent_model, acc)
            if roles == (acc.get('roles') or {}):
                continue
            if access.model_key(setting.parent_model) is None:
                # A Setting for a model no longer registered: nothing can be read through it,
                # and it cannot be saved (its parent_model is refused). Reported, not written.
                self.stdout.write(f"{setting.parent_model}: skipped, model not registered")
                continue
            changed += 1
            self.stdout.write(f"{setting.parent_model}: customer/buyer -> "
                              f"{'removed' if access.PORTAL_ORDER_ROLES[0] not in roles else 'set'}")
            if options['apply']:
                acc['roles'] = roles
                # Removing a block cannot widen anything, so only a block being set is
                # validated (a Setting for a model no longer registered still loses it).
                setting_one = access.portal_customer_block(setting.parent_model) is not None
                problems = access.validate_access(setting.parent_model, acc) if setting_one else []
                if problems:
                    raise CommandError(f'{setting.parent_model}: {problems}')
                config['access'] = acc
                setting.config = config
                setting._setting_update_authorized = True
                try:
                    setting.save(update_fields=['config'])
                except ValidationError as exc:
                    if setting_one:
                        raise CommandError(f'{setting.parent_model}: {exc}')
                    # Other roles' lists on this Setting fail the save guard (a problem of
                    # their own). A block with no scope already reads nothing for a portal
                    # role (role_filter), so leaving it is safe; it is named here.
                    self.stdout.write(f"{setting.parent_model}: NOT written — the Setting fails "
                                      f"validation on other roles; fix it, then rerun")
        access.clear_cache()
        self.stdout.write(f"{changed} model(s) {'changed' if options['apply'] else 'would change'}")

    def _bundle(self, path: Path, apply_changes: bool):
        if not path.exists():
            raise CommandError(f'{path} does not exist')
        data = json.loads(path.read_text())
        changed = []

        def walk(node):
            if isinstance(node, dict):
                if node.get('purpose') == 'wc:model' and isinstance(node.get('config'), dict):
                    acc = node['config'].get('access')
                    if isinstance(acc, dict):
                        roles = narrowed_roles(node.get('parent_model'), acc)
                        if roles != (acc.get('roles') or {}):
                            acc['roles'] = roles
                            changed.append(node.get('parent_model'))
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(data)
        if apply_changes and changed:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        self.stdout.write(f"{path.name}: {len(changed)} model(s) "
                          f"{'changed' if apply_changes else 'would change'}")
