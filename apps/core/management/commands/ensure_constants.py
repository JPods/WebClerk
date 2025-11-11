"""
Management command to ensure mandatory constants exist in the database.
"""

from django.core.management.base import BaseCommand
from apps.core.constants.mandatory_constants import ensure_mandatory_constants_exist


class Command(BaseCommand):
    help = 'Ensure all mandatory constants exist in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress verbose output',
        )

    def handle(self, *args, **options):
        verbose = not options['quiet']

        self.stdout.write('Ensuring mandatory constants exist...')

        try:
            result = ensure_mandatory_constants_exist(verbose=verbose)

            if isinstance(result, dict):
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully processed constants: '
                        f'{len(result["created"])} created, '
                        f'{len(result["updated"])} updated, '
                        f'{len(result["existing"])} existing'
                    )
                )

                if result['created']:
                    self.stdout.write('Created categories:')
                    for category in result['created']:
                        self.stdout.write(f'  - {category}')

                if result['updated']:
                    self.stdout.write('Updated categories:')
                    for category in result['updated']:
                        self.stdout.write(f'  - {category}')

                self.stdout.write(
                    f'Total: {result["total_categories"]} categories, '
                    f'{result["total_constants"]} constants'
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'Command completed successfully')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error ensuring constants: {e}')
            )
            return 1

        return 0