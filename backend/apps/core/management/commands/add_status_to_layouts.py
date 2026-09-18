"""Add 'status' field next to 'purpose' in all Setting layout definitions.

Shows the first 10 changes one at a time for review. After 10 records,
if not canceled, auto-completes the rest. Even the owner should have to
suffer to change Setting records.

Usage:
    python manage.py add_status_to_layouts
    python manage.py add_status_to_layouts --dry-run
"""
from django.core.management.base import BaseCommand


def _insert_after(lst, after_field, new_field):
    """Insert new_field after after_field in a list of field specs.
    If after_field not found, append at end. Returns True if changed."""
    # Extract field names for comparison
    def get_name(item):
        if isinstance(item, dict):
            return item.get('field', '')
        return str(item)

    names = [get_name(x) for x in lst]
    if new_field in names:
        return False  # already present

    if after_field in names:
        idx = names.index(after_field)
        lst.insert(idx + 1, {'field': new_field, 'width': 80, 'align': 'left'})
    else:
        # purpose not found — insert status after ida or at position 2
        if 'ida' in names:
            idx = names.index('ida')
            lst.insert(idx + 1, {'field': new_field, 'width': 80, 'align': 'left'})
        else:
            lst.insert(min(2, len(lst)), {'field': new_field, 'width': 80, 'align': 'left'})
    return True


class Command(BaseCommand):
    help = "Add 'status' next to 'purpose' in all Setting layout definitions (list, detail, form)"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show changes without saving')

    def handle(self, *args, **options):
        from apps.core.models.setting import Setting

        dry_run = options['dry_run']
        settings = Setting.objects.filter(
            purpose='wc:model',
            is_active=True,
            is_deleted=False,
        ).order_by('parent_model')

        total = settings.count()
        self.stdout.write(f"\n  {total} wc:model Settings to check\n")

        changed_count = 0
        skipped_count = 0
        auto_mode = False

        for i, setting in enumerate(settings):
            config = setting.config if isinstance(setting.config, dict) else {}
            layout = config.get('layout', {})
            if not layout:
                continue

            changes = []

            # ── List layouts ──
            for name, ll in layout.get('list', {}).items():
                cols = ll.get('columns', [])
                if _insert_after(cols, 'purpose', 'status'):
                    changes.append(f"list.{name}: added status after purpose")

            # ── Detail layouts ──
            for name, dl in layout.get('detail', {}).items():
                for si, section in enumerate(dl.get('sections', [])):
                    if not isinstance(section, dict):
                        continue
                    for col in section.get('columns', []):
                        if not isinstance(col, dict):
                            continue
                        fields = col.get('fields', [])
                        if _insert_after(fields, 'purpose', 'status'):
                            changes.append(f"detail.{name}.section[{si}]: added status")

            # ── Form layouts ──
            for name, fl in layout.get('form', {}).items():
                header = fl.get('header', {})
                if isinstance(header, dict):
                    for ci, card in enumerate(header.get('cards', [])):
                        if isinstance(card, dict):
                            fields = card.get('fields', [])
                            if _insert_after(fields, 'purpose', 'status'):
                                changes.append(f"form.{name}.header.cards[{ci}]: added status")

            # ── Column layouts ──
            for name, cl in layout.get('column', {}).items():
                cols = cl.get('columns', [])
                if _insert_after(cols, 'purpose', 'status'):
                    changes.append(f"column.{name}: added status after purpose")

            if not changes:
                continue

            # ── Show the change ──
            self.stdout.write(f"\n  [{i+1}/{total}] {setting.parent_model} (Setting #{setting.id})")
            for c in changes:
                self.stdout.write(f"    + {c}")

            # ── Interactive confirmation for first 10 ──
            if not auto_mode and changed_count < 10 and not dry_run:
                answer = input("    Apply? (y/n/q to quit): ").strip().lower()
                if answer == 'q':
                    self.stdout.write(self.style.WARNING("\n  Quit. No further changes."))
                    break
                if answer != 'y':
                    skipped_count += 1
                    self.stdout.write("    Skipped.")
                    continue

                if changed_count == 9:
                    self.stdout.write(self.style.WARNING(
                        "\n  ── 10 records reviewed. Remaining changes will auto-apply. ──"
                    ))
                    cont = input("    Continue with auto-apply? (yes/no): ").strip().lower()
                    if cont != 'yes':
                        self.stdout.write("  Stopped.")
                        break
                    auto_mode = True

            # ── Save ──
            if not dry_run:
                setting.config = config
                setting._setting_update_authorized = True
                setting.save(update_fields=['config', 'dt_modified'])

            changed_count += 1
            if dry_run:
                self.stdout.write("    (dry run)")

        self.stdout.write(f"\n  Done: {changed_count} changed, {skipped_count} skipped")
        if dry_run:
            self.stdout.write(self.style.WARNING("  DRY RUN — no changes saved"))
