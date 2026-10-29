"""seed_layouts — every model's list, detail, form, panel and card (apps/core/layouts).

Fills only the parts a model's definition lacks, from layouts.json or, for a model it does not
hold, a guess from the model's fields. A company's own layout is never overwritten; to put
one part back, a staff login resets it (POST /wcapi/_layout_reset/).

    python manage.py seed_layouts                 # report what is missing
    python manage.py seed_layouts --apply         # fill it
    python manage.py seed_layouts --model order   # one model
    python manage.py seed_layouts --capture       # the layouts in use become layouts.json (commit it)
"""
from django.core.management.base import BaseCommand

from apps.core import layouts
from apps.core.models import Setting
from apps.core.services import definition


class Command(BaseCommand):
    help = "Fill each model's missing layout parts; --capture writes the layouts in use to layouts.json"

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write the filled parts')
        parser.add_argument('--model', type=str, default=None, help='One model only')
        parser.add_argument('--capture', action='store_true',
                            help='Write the layouts in use into apps/core/layouts/layouts.json')

    def handle(self, *args, **options):
        qs = Setting.objects.filter(purpose='wc:model').order_by('parent_model', 'id')
        if options['model']:
            qs = qs.filter(parent_model=options['model'])

        if options['capture']:
            captured = {d.parent_model: (d.config or {}).get('layout') or {}
                        for d in qs if d.parent_model}
            layouts.capture(captured)
            self.stdout.write(f'captured {len(captured)} layouts into {layouts.DESIGNED}')
            return

        filled_models = 0
        for d in qs:
            layout, filled = layouts.fill(d.parent_model, (d.config or {}).get('layout'))
            if not filled:
                continue
            filled_models += 1
            self.stdout.write(f"  {d.parent_model}: {', '.join(filled)}")
            if options['apply']:
                config = dict(d.config or {})
                config['layout'] = layout
                Setting.objects.filter(pk=d.pk).update(config=config)
                definition.clear(d.parent_model)
        verb = 'filled' if options['apply'] else 'missing parts (dry run; --apply to fill)'
        self.stdout.write(self.style.SUCCESS(f'{filled_models} models {verb}'))
