"""Seed enrichment panel Settings for item, contact, and org detail pages.

Usage: ./manage.py seed_enrichment_panels
       ./manage.py seed_enrichment_panels --model item
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting
from common.schemas.enrichment import (
    ItemEnrichment,
    ContactEnrichment,
    OrgEnrichment,
)


ENRICHMENTS = {
    'item': {
        'schema': ItemEnrichment,
        'name': 'Item detail enrichment panels',
        'description': 'Sales history, margins, inventory, pricing, costing, images',
    },
    'contact': {
        'schema': ContactEnrichment,
        'name': 'Contact detail enrichment panels',
        'description': 'Organizations, activity summary, relationships',
    },
    'customer': {
        'schema': OrgEnrichment,
        'name': 'Customer detail enrichment panels',
    },
    'vendor': {
        'schema': OrgEnrichment,
        'name': 'Vendor detail enrichment panels',
    },
    'manufacturer': {
        'schema': OrgEnrichment,
        'name': 'Manufacturer detail enrichment panels',
    },
}


class Command(BaseCommand):
    help = "Seed enrichment panel Settings for item, contact, and org models"

    def add_arguments(self, parser):
        parser.add_argument(
            '--model', type=str, default=None,
            help='Seed only this model (item, contact, org). Default: all.',
        )

    def handle(self, *args, **options):
        target = options.get('model')
        to_seed = {target: ENRICHMENTS[target]} if target and target in ENRICHMENTS else ENRICHMENTS

        for model_name, info in to_seed.items():
            schema_instance = info['schema']()
            config = schema_instance.model_dump()

            setting, created = Setting.objects.update_or_create(
                purpose='wc:enrichment_panels',
                parent_model=model_name,
                defaults={
                    'ida': f'enrichment-{model_name}',
                    'name': info['name'],
                    'config': config,
                },
            )

            verb = 'Created' if created else 'Updated'
            panel_count = len(config.get('panels', []))
            self.stdout.write(self.style.SUCCESS(
                f"{verb} enrichment Setting #{setting.id} for {model_name} "
                f"({panel_count} panels)"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"\nSeeded {len(to_seed)} enrichment panel(s)."
        ))
