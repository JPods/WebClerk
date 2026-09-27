"""Add a model's new leaves to the stored 'all' set that '@all' roles use.

The counterpart of prune_access_leaves. A role granted '@all' (superuser, admin, agent on a new
install) reads a stored set — the model's leaves as they were when the install was seeded — so a
field added later is in no list (Bill, 2026-09-20: "a leaf added later is in no list until someone
adds it"). The door then ignores it on save, silently: on wc_demo the workorder's kind (and the new
line leaves physical.layer_id, physical.warehouse_id, shipping.warehouse_id) could not be written.
Bill, 2026-09-27: a command that grows '@all'. Only the 'all' set grows; a role whose lists name
paths one by one (rep, sales) gets nothing new without an admin's grant.

    manage.py grow_access_leaves [--model workorder]     # show what would be added
    manage.py grow_access_leaves --apply
"""
from django.core.management.base import BaseCommand

from apps.core.services import access


class Command(BaseCommand):
    help = "Add each model's current leaves to its stored 'all' access set (dry run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write the grown sets.')
        parser.add_argument('--model', help='Only this model key.')

    def handle(self, *args, **options):
        from apps.core.models.setting import Setting
        from apps.core.services import field_leaves as fl

        apply_changes = options['apply']
        grown = 0
        settings = Setting.objects.filter(purpose='wc:model').order_by('parent_model', 'pk')
        if options.get('model'):
            settings = settings.filter(parent_model=options['model'])
        for setting in settings:
            key = setting.parent_model
            config = dict(setting.config or {})
            acc = dict(config.get('access') or {})
            sets = dict(acc.get('sets') or {})
            if not isinstance(sets.get('all'), list):
                continue
            try:
                leaves = sorted(fl.model_leaves(key)['leaves'])
            except (LookupError, AttributeError) as e:
                self.stdout.write(self.style.WARNING(f"{key}: leaves unreadable ({e}) — skipped"))
                continue
            added = [leaf for leaf in leaves if leaf not in sets['all']]
            if not added:
                continue
            grown += 1
            self.stdout.write(f"  {key}/sets/all: +{len(added)} — {', '.join(added[:8])}"
                              + (' …' if len(added) > 8 else ''))
            if not apply_changes:
                continue
            sets['all'] = sorted(set(sets['all']) | set(added))
            acc['sets'] = sets
            problems = access.validate_access(key, acc)
            if problems:
                self.stdout.write(self.style.ERROR(f"  {key}: refused — {problems[:3]}"))
                grown -= 1
                continue
            config['access'] = acc
            setting.config = config
            setting._setting_update_authorized = True
            setting.save(update_fields=['config', 'dt_modified', 'version'])
            access.clear_cache(key)

        verb = 'Grew' if apply_changes else 'Would grow'
        self.stdout.write(self.style.SUCCESS(f"{verb} {grown} model(s)."))
        if not apply_changes and grown:
            self.stdout.write("Dry run — pass --apply to write.")
