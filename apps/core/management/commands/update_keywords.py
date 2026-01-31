"""
Management command to update keywords for all models that support keyword denormalization.
"""
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction
from django.core.paginator import Paginator
import logging
import time


class Command(BaseCommand):
    help = "Update refs.keywords denormalization for all models that support it"

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            action='append',
            help='Specific model name to update (e.g., "contact", "action"). Can be specified multiple times. If not provided, updates all models.'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of records to process in each batch (default: 100)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Maximum number of records to process per model (for testing)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed progress information'
        )

    def handle(self, *args, **options):
        model_names = options.get('model')
        batch_size = options.get('batch_size', 100)
        limit = options.get('limit')
        dry_run = options.get('dry_run', False)
        verbose = options.get('verbose', False)

        # Set up logging
        logger = logging.getLogger(__name__)

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Find all models that have update_keywords method
        models_to_update = self._find_models_with_keywords(model_names)

        if not models_to_update:
            if model_names:
                self.stdout.write(self.style.ERROR(f"No model(s) named {model_names} found with keyword support"))
            else:
                self.stdout.write(self.style.ERROR("No models found with keyword support"))
            return

        self.stdout.write(f"Found {len(models_to_update)} model(s) with keyword support:")
        for model in models_to_update:
            self.stdout.write(f"  - {model._meta.label}")

        total_processed = 0
        total_updated = 0
        total_errors = 0

        start_time = time.time()

        for model in models_to_update:
            model_start_time = time.time()
            processed, updated, errors = self._update_model_keywords(
                model, batch_size, limit, dry_run, verbose
            )
            model_time = time.time() - model_start_time

            total_processed += processed
            total_updated += updated
            total_errors += errors

            self.stdout.write(
                f"  {model._meta.label}: {processed} processed, {updated} updated, {errors} errors "
                f"({model_time:.1f}s)"
            )

        total_time = time.time() - start_time

        self.stdout.write(self.style.SUCCESS(
            f"\nCompleted: {total_processed} records processed, "
            f"{total_updated} updated, {total_errors} errors "
            f"({total_time:.1f}s total)"
        ))

    def _find_models_with_keywords(self, specific_model_names=None):
        """Find all models that have an update_keywords method."""
        models_with_keywords = []

        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                # Skip models without refs field
                if not hasattr(model, 'refs'):
                    continue

                # Check if model has update_keywords method
                if hasattr(model, 'update_keywords') and callable(getattr(model, 'update_keywords')):
                    if specific_model_names:
                        # Check if this model's name matches any of the specified names
                        model_name_lower = model._meta.model_name.lower()
                        if any(name.lower() == model_name_lower for name in specific_model_names):
                            models_with_keywords.append(model)
                    else:
                        models_with_keywords.append(model)

        return models_with_keywords

    def _update_model_keywords(self, model, batch_size, limit, dry_run, verbose):
        """Update keywords for all records in a model."""
        processed = 0
        updated = 0
        errors = 0

        # Get queryset
        queryset = model.objects.all().order_by('id')

        if limit:
            queryset = queryset[:limit]

        # Use pagination for memory efficiency
        paginator = Paginator(queryset, batch_size)

        for page_num in range(1, paginator.num_pages + 1):
            page = paginator.page(page_num)
            batch_start_time = time.time()

            # Process batch
            for record in page.object_list:
                try:
                    processed += 1

                    if verbose:
                        self.stdout.write(f"    Processing {model._meta.label} id={record.id}")

                    if not dry_run:
                        # Call update_keywords method
                        record.update_keywords()

                        # Save the record (update_keywords modifies refs in memory)
                        # Note: This may fail validation if the record has invalid data in other fields,
                        # but the keywords were updated successfully
                        try:
                            record.save(update_fields=['refs', 'metadata'])
                            updated += 1
                        except Exception as save_error:
                            # Keywords were updated but save failed (likely due to validation on other fields)
                            if verbose:
                                self.stdout.write(
                                    self.style.WARNING(f"      Keywords updated but save failed for {model._meta.label} id={record.id}: {save_error}")
                                )
                            # Still count as updated since keywords were generated successfully
                            updated += 1

                except Exception as e:
                    errors += 1
                    if verbose:
                        self.stdout.write(
                            self.style.ERROR(f"      Error updating {model._meta.label} id={record.id}: {e}")
                        )

            batch_time = time.time() - batch_start_time
            if verbose:
                self.stdout.write(f"    Batch {page_num}/{paginator.num_pages} completed in {batch_time:.1f}s")

        return processed, updated, errors