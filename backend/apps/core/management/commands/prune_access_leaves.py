"""Drop names from the access lists that are no longer leaves of their model.

A field removed from a model (is_deleted, when soft delete went — Bill, 2026-09-22) stays
named in the wc:model Settings' view/edit lists and sets. validate_access then refuses the
whole block, so no one can save access for that model — seed_rep_access was refused on
every rep block for exactly this (2026-09-24). A name that is not a leaf grants nothing, so
removing it changes no one's access. Bill, 2026-09-24: yes, prune them.

    manage.py prune_access_leaves            # show what would be removed
    manage.py prune_access_leaves --apply
"""
from django.core.management.base import BaseCommand

from apps.core.services import access


def _is_leaf_name(name, leaves) -> bool:
    if not isinstance(name, str):
        return False
    if name.startswith('@'):
        return True                          # a set reference; the set itself is pruned
    if '$user.' in name:
        head = name.split('$user.')[0]
        return any(leaf.startswith(head) for leaf in leaves)
    return name in leaves


class Command(BaseCommand):
    help = "Remove non-leaf names from wc:model access lists (dry run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write the pruned lists.')

    def handle(self, *args, **options):
        from apps.core.models.setting import Setting
        from apps.core.services import field_leaves as fl

        apply_changes = options['apply']
        pruned_models = 0
        for setting in Setting.objects.filter(purpose='wc:model').order_by('parent_model', 'pk'):
            key = setting.parent_model
            config = dict(setting.config or {})
            acc = dict(config.get('access') or {})
            if not acc:
                continue
            try:
                leaves = fl.model_leaves(key)['leaves']
            except (LookupError, AttributeError) as e:
                # A model whose leaves cannot be read cannot be validated either: report it.
                self.stdout.write(self.style.WARNING(f"{key}: leaves unreadable ({e}) — skipped"))
                continue

            removed = {}
            sets = {}
            for name, members in (acc.get('sets') or {}).items():
                members = members if isinstance(members, list) else []
                kept = [m for m in members if _is_leaf_name(m, leaves) and not str(m).startswith('@')]
                gone = [m for m in members if m not in kept]
                if gone:
                    removed[f'sets/{name}'] = gone
                sets[name] = kept
            roles = {}
            for role, block in (acc.get('roles') or {}).items():
                block = dict(block) if isinstance(block, dict) else block
                if isinstance(block, dict):
                    for kind in ('view', 'edit'):
                        paths = block.get(kind)
                        if isinstance(paths, list):
                            kept = [p for p in paths if _is_leaf_name(p, leaves)]
                            if len(kept) != len(paths):
                                removed[f'{role}/{kind}'] = [p for p in paths if p not in kept]
                            block[kind] = kept
                roles[role] = block
            if not removed:
                continue

            pruned_models += 1
            for where, names in removed.items():
                self.stdout.write(f"  {key}/{where}: {len(names)} — {', '.join(map(str, names[:6]))}"
                                  + (' …' if len(names) > 6 else ''))
            if not apply_changes:
                continue
            if 'sets' in acc:
                acc['sets'] = sets
            acc['roles'] = roles
            problems = access.validate_access(key, acc)
            if problems:
                self.stdout.write(self.style.ERROR(f"  {key}: still refused — {problems[:3]}"))
                pruned_models -= 1
                continue
            config['access'] = acc
            setting.config = config
            setting._setting_update_authorized = True
            setting.save(update_fields=['config', 'dt_modified', 'version'])
            access.clear_cache(key)

        verb = 'Pruned' if apply_changes else 'Would prune'
        self.stdout.write(self.style.SUCCESS(f"{verb} {pruned_models} model(s)."))
        if not apply_changes and pruned_models:
            self.stdout.write("Dry run — pass --apply to write.")
