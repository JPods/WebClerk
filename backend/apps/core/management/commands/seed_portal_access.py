"""Give the portal roles their field enumeration on order and quote.

What a portal customer may write lived as a tuple in
``apps/transactions/views/wcapi.py`` — so the one place that says what a role may write
did not say it (Bill, 2026-09-20: the list is an enumeration in a Setting record, not a
filter and not a literal in a view).

This adds that enumeration to the existing order and quote Settings for the roles that
raise their own documents, and touches no other role's block.

    manage.py seed_portal_access            # show what would change
    manage.py seed_portal_access --apply
"""
from django.core.management.base import BaseCommand

from apps.core.services import access


class Command(BaseCommand):
    help = "Enumerate what portal customers may write on their own orders and quotes."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        from apps.core.models.setting import Setting
        from apps.core.services import field_leaves as fl

        apply_changes = options['apply']
        changed = 0

        for key in sorted(access.PORTAL_ORDER_MODELS):
            setting = (Setting.objects.filter(purpose='wc:model', parent_model=key,
                                              is_deleted=False).first())
            if setting is None:
                self.stdout.write(self.style.WARNING(f"{key}: no wc:model Setting"))
                continue

            config = dict(setting.config or {})
            acc = dict(config.get('access') or {})
            roles = dict(acc.get('roles') or {})
            leaves = set(fl.model_leaves(key)['leaves'])
            allowed = [p for p in access.PORTAL_ORDER_FIELDS if p in leaves]
            missing = [p for p in access.PORTAL_ORDER_FIELDS if p not in leaves]
            if missing:
                self.stdout.write(self.style.WARNING(
                    f"  {key}: not leaves of this model, skipped — {', '.join(missing)}"))

            for role in access.PORTAL_ORDER_ROLES:
                block = dict(roles.get(role) or {})
                before = list(block.get('edit') or [])
                # edit must be a subset of view — you cannot fill a field you cannot see.
                # Anything not viewable is skipped and reported, never granted silently:
                # widening what a portal user can see is a decision, not a side effect.
                viewable = set(access.expand_sets(block.get('view') or [], acc.get('sets') or {}))
                grant = [p for p in allowed if p in viewable]
                blocked = [p for p in allowed if p not in viewable]
                if blocked:
                    self.stdout.write(self.style.WARNING(
                        f"  {key}/{role}: not in this role's view, so not granted — "
                        f"{', '.join(blocked)}"))
                if sorted(before) == sorted(grant):
                    continue
                block['edit'] = grant
                allowed_for_role = grant
                block.setdefault('view', ['@all'])
                block.setdefault('scope', {'customer_id__in': '$user.org_ids.customer'})
                block.setdefault('create', True)
                block.setdefault('delete', False)
                roles[role] = block
                changed += 1
                self.stdout.write(
                    f"  {key}/{role}: edit {len(before)} -> {len(allowed_for_role)} leaves "
                    f"({', '.join(allowed_for_role) or 'none'})")

            if apply_changes:
                acc['roles'] = roles
                config['access'] = acc
                setting.config = config
                setting._setting_update_authorized = True
                setting.save(update_fields=['config', 'dt_modified', 'version'])
                access.clear_cache(key)

        verb = 'Updated' if apply_changes else 'Would update'
        self.stdout.write(self.style.SUCCESS(f"{verb} {changed} role block(s)."))
        if not apply_changes and changed:
            self.stdout.write("Dry run — pass --apply to write.")
