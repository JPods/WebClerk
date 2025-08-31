"""Seed minimal demo data for every empty table.

Behavior:
 1. Iterate all concrete Django models.
 2. If the table already has rows -> skip.
 3. Otherwise attempt to create 3 placeholder records with generic field values.

Constraints / Pragmatic Rules:
 - Skips obviously transient / system tables (auth.Permission, contenttypes, etc.).
 - Skips session, celery, and Pending/task result tables.
 - Skips models whose required (non-null) FK targets are empty (can't satisfy integrity easily).
 - Skips custom user model (core.Contact) unless explicitly forced (simplifies password handling).
 - For each field:
     * AutoField / PK: omitted
     * Char/Text: modelname-sample-i
     * Email: sample{i}@example.com
     * Boolean: i % 2 == 0
     * Integer/BigInteger/SmallInteger/Positive*: i
     * Decimal: Decimal(i)
     * Float: float(i)
     * Date/DateTime: timezone.now()/date()
     * UUID: uuid4
     * JSONField: {}
     * ForeignKey: first existing related object (if any); if required and none -> abort that model.
     * Choices: first choice key if available.
 - Fields with defaults are left untouched (Django will fill) unless they are blank-able and we set values anyway.

Usage:
   python manage.py seed_minimal_if_empty
   python manage.py seed_minimal_if_empty --include-contact
   python manage.py seed_minimal_if_empty --limit 50  (only process first 50 models)

Exit code / output: Prints a summary of created records / skipped reasons.
"""

from django.core.management.base import BaseCommand
from django.apps import apps
from django.utils import timezone
from decimal import Decimal
import uuid


SKIP_MODELS = {
    'auth.Permission',
    'contenttypes.ContentType',
    'admin.LogEntry',
    'sessions.Session',
    'core.Pending',
    # celery beat / results
    'django_celery_beat.PeriodicTask',
    'django_celery_beat.CrontabSchedule',
    'django_celery_beat.IntervalSchedule',
    'django_celery_beat.ClockedSchedule',
    'django_celery_beat.SolarSchedule',
    'django_celery_beat.PeriodicTasks',
    'django_celery_results.TaskResult',
    'django_celery_results.GroupResult',
    'django_celery_results.ChordCounter',
}


NUM_RECORDS = 3


class Command(BaseCommand):
    help = "Populate every empty table with 3 generic demo rows (skips if any existing rows)."

    def add_arguments(self, parser):  # pragma: no cover (simple CLI plumbing)
        parser.add_argument('--include-contact', action='store_true', help='Also seed core.Contact if empty (creates generic users).')
        parser.add_argument('--include-setting', action='store_true', help='Also seed core.Setting if empty (opt-in).')
        parser.add_argument('--limit', type=int, default=None, help='Optional max number of models to process (debug).')
        parser.add_argument('--verbose-errors', action='store_true', help='Show full exception messages when a model fails to seed.')
        parser.add_argument('--populate-links', action='store_true', help='After seeding, populate refs.links with global contact/action/location/email/phone/domain ids and line associations.')

    def handle(self, *args, **opts):
        include_contact = opts['include_contact']
        include_setting = opts['include_setting']
        limit = opts.get('limit') or None
        verbose_errors = opts['verbose_errors']
        populate_links = opts.get('populate_links')

        processed = 0
        created_summary = []
        skipped = []

        for model in apps.get_models():
            if limit and processed >= limit:
                break
            model_label = f"{model._meta.app_label}.{model.__name__}"
            if model_label in SKIP_MODELS:
                skipped.append((model_label, 'skip-list'))
                continue
            if model_label == 'core.Contact' and not include_contact:
                skipped.append((model_label, 'contact (opt-in)'))
                continue
            if model_label == 'core.Setting' and not include_setting:
                skipped.append((model_label, 'setting (opt-in)'))
                continue
            # Abstract / proxy safety
            if model._meta.abstract or model._meta.proxy:
                continue
            try:
                if model.objects.exists():
                    skipped.append((model_label, 'has data'))
                    continue
            except Exception as e:  # some unmanaged models might error
                skipped.append((model_label, f'count-error: {e}'))
                continue

            # Build prototype field values
            required_fk_unmet = False
            fk_cache = {}
            for field in model._meta.fields:
                if field.is_relation and field.many_to_one and not field.null:  # required FK
                    rel_model = field.related_model
                    try:
                        first_rel = rel_model.objects.first()
                    except Exception:
                        first_rel = None
                    if not first_rel:
                        required_fk_unmet = True
                        break
                    fk_cache[field.name] = first_rel
            if required_fk_unmet:
                skipped.append((model_label, 'required FK empty'))
                continue

            created_ids = []
            for i in range(1, NUM_RECORDS + 1):
                data = {}
                for field in model._meta.fields:
                    if field.primary_key or getattr(field, 'auto_created', False):
                        continue
                    if field.is_relation and field.many_to_one:
                        if field.name in fk_cache:
                            data[field.name] = fk_cache[field.name]
                        else:
                            if field.null:
                                data[field.name] = None
                        continue
                    internal_type = field.get_internal_type()
                    if getattr(field, 'choices', None):
                        try:
                            first_choice = field.choices[0][0]
                            data[field.name] = first_choice
                            continue
                        except Exception:
                            pass
                    try:
                        if internal_type in ('CharField', 'TextField', 'SlugField'):
                            max_len = getattr(field, 'max_length', 50) or 50
                            base = f"{model.__name__.lower()}-{i}"
                            data[field.name] = base[:max_len]
                        elif internal_type == 'EmailField':
                            data[field.name] = f"sample{i}@example.com"
                        elif internal_type in ('BooleanField', 'NullBooleanField'):
                            data[field.name] = (i % 2 == 0)
                        elif internal_type in ('IntegerField', 'BigIntegerField', 'SmallIntegerField', 'PositiveIntegerField', 'PositiveSmallIntegerField', 'AutoField'):
                            data[field.name] = i
                        elif internal_type == 'DecimalField':
                            data[field.name] = Decimal(i)
                        elif internal_type == 'FloatField':
                            data[field.name] = float(i)
                        elif internal_type == 'UUIDField':
                            data[field.name] = uuid.uuid4()
                        elif internal_type == 'DateTimeField':
                            data[field.name] = timezone.now()
                        elif internal_type == 'DateField':
                            data[field.name] = timezone.now().date()
                        elif internal_type == 'JSONField':
                            data[field.name] = {}
                    except Exception:
                        pass
                try:
                    obj = model.objects.create(**data)
                    created_ids.append(obj.pk)
                except Exception as e:
                    if verbose_errors:
                        self.stderr.write(f"Failed create {model_label} #{i}: {e}")
                    if i == 1 and not created_ids:
                        created_ids = []
                        break
            if created_ids:
                created_summary.append((model_label, created_ids))
            else:
                skipped.append((model_label, 'create-failed'))
            processed += 1

        self.stdout.write(self.style.SUCCESS('Seeding pass complete.'))
        if created_summary:
            self.stdout.write('Created:')
            for label, ids in created_summary:
                self.stdout.write(f" - {label}: {ids}")
        self.stdout.write(f"Skipped ({len(skipped)}):")
        for label, reason in skipped:
            self.stdout.write(f" - {label}: {reason}")

        # Optional refs.links population
        if populate_links:
            self._populate_links(verbose_errors=verbose_errors)

    # --- Link population helpers -------------------------------------------------
    def _populate_links(self, verbose_errors=False):
        """Populate refs.links for models that have a JSONField named 'refs'.

        Adds:
          - contacts, actions, locations, emails, phones, domains (all IDs) if those models exist.
          - For any header model that has related line models (line model class name ends with 'Line' and FK to header),
            adds refs.links[<line_table_name>] = list of line ids for that header.
        """
    # transaction import not required; relying on per-object saves for simplicity

        # Collect global ID lists
        def ids_for(label):
            try:
                app_label, model_name = label.split('.')
                M = apps.get_model(app_label, model_name)
                return list(M.objects.values_list('id', flat=True))
            except Exception:
                return []

        contacts_ids = ids_for('core.Contact')
        actions_ids = ids_for('core.Action')
        locations_ids = ids_for('communications.Location')
        emails_ids = ids_for('communications.Email')
        phones_ids = ids_for('communications.Phone')
        domains_ids = ids_for('communications.Domain')

        # Pre-build line associations: { (header_model, header_pk): { line_table: [ids...] } }
        line_map = {}
        for line_model in apps.get_models():
            if not line_model.__name__.endswith('Line'):
                continue
            # Find its FK(s) to a potential header
            fk_targets = [f for f in line_model._meta.fields if f.is_relation and f.many_to_one]
            # We treat the first FK as the header anchor (heuristic)
            if not fk_targets:
                continue
            header_fk = fk_targets[0]
            header_model = header_fk.related_model
            try:
                for line_obj in line_model.objects.all().only('id', header_fk.name):
                    header_id = getattr(line_obj, header_fk.attname)
                    if header_id is None:
                        continue
                    key = (header_model, header_id)
                    bucket = line_map.setdefault(key, {})
                    lt = line_model._meta.db_table
                    bucket.setdefault(lt, []).append(line_obj.pk)
            except Exception as e:
                if verbose_errors:
                    self.stderr.write(f"Line scan error {line_model}: {e}")
                continue

        # Update header refs and generic refs for all models possessing 'refs'
        updated = 0
        for model in apps.get_models():
            if 'refs' not in {f.name for f in model._meta.fields}:
                continue
            # Determine if this model acts as header for any lines
            is_header = any(k[0] is model for k in line_map.keys())
            try:
                for obj in model.objects.all():
                    refs = getattr(obj, 'refs', {}) or {}
                    links = refs.setdefault('links', {})
                    # Add global lists if present
                    if contacts_ids:
                        links.setdefault('contacts', contacts_ids)
                    if actions_ids:
                        links.setdefault('actions', actions_ids)
                    if locations_ids:
                        links.setdefault('locations', locations_ids)
                    if emails_ids:
                        links.setdefault('emails', emails_ids)
                    if phones_ids:
                        links.setdefault('phones', phones_ids)
                    if domains_ids:
                        links.setdefault('domains', domains_ids)
                    if is_header:
                        header_bucket = line_map.get((model, obj.pk))
                        if header_bucket:
                            for lt, id_list in header_bucket.items():
                                links.setdefault(lt, id_list)
                    # Assign back only if changed
                    setattr(obj, 'refs', refs)
                    try:
                        obj.save(update_fields=['refs'])
                        updated += 1
                    except Exception as e:
                        if verbose_errors:
                            self.stderr.write(f"Failed saving refs for {model.__name__}#{obj.pk}: {e}")
            except Exception as e:
                if verbose_errors:
                    self.stderr.write(f"Header iteration error {model}: {e}")
        self.stdout.write(self.style.SUCCESS(f"refs.links population complete. Updated {updated} rows."))