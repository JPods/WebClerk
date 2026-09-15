from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Denormalize links in refs for all models that inherit from BaseModel'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Specific model to process (app_label.model_name)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Batch size for processing records',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        specific_model = options.get('model')
        batch_size = options['batch_size']

        # Get all models that inherit from BaseModel
        models_to_process = []
        for model in apps.get_models():
            if hasattr(model, 'ensure_links_denormalized'):
                if specific_model:
                    if f"{model._meta.app_label}.{model._meta.model_name}" == specific_model:
                        models_to_process.append(model)
                else:
                    models_to_process.append(model)

        if not models_to_process:
            self.stdout.write(self.style.WARNING('No models found to process'))
            return

        for model in models_to_process:
            self.stdout.write(f"Processing model: {model._meta.label}")
            self.process_model(model, dry_run, batch_size)

    def process_model(self, model, dry_run, batch_size):
        queryset = model.objects.all()
        total_count = queryset.count()
        processed = 0

        self.stdout.write(f"  Total records: {total_count}")

        while processed < total_count:
            batch = queryset[processed:processed + batch_size]
            with transaction.atomic():
                for instance in batch:
                    try:
                        if hasattr(instance, 'ensure_links_denormalized'):
                            instance.ensure_links_denormalized()
                            if not dry_run:
                                instance.save(update_fields=['refs'])
                    except Exception as e:
                        logger.error(f"Error processing {model._meta.label} id={instance.pk}: {e}")
                        self.stdout.write(self.style.ERROR(f"Error processing {model._meta.label} id={instance.pk}: {e}"))

            processed += len(batch)
            self.stdout.write(f"  Processed {processed}/{total_count} records")

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry run completed for {model._meta.label}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully processed {model._meta.label}"))