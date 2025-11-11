"""
Management command to validate mandatory constants configuration.
"""

from django.core.management.base import BaseCommand
from apps.core.constants.mandatory_constants import validate_mandatory_constants


class Command(BaseCommand):
    help = 'Validate that all mandatory constants are properly configured'

    def handle(self, *args, **options):
        self.stdout.write('Validating mandatory constants...')

        try:
            result = validate_mandatory_constants()

            if result['valid']:
                self.stdout.write(
                    self.style.SUCCESS('All mandatory constants are valid!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('Mandatory constants validation failed!')
                )

                issues = result['issues']

                if issues['missing_categories']:
                    self.stdout.write(
                        self.style.ERROR('Missing categories:')
                    )
                    for category in issues['missing_categories']:
                        self.stdout.write(f'  - {category}')

                if issues['missing_constants']:
                    self.stdout.write(
                        self.style.WARNING('Missing constants:')
                    )
                    for constant in issues['missing_constants']:
                        self.stdout.write(f'  - {constant}')

                if issues['invalid_types']:
                    self.stdout.write(
                        self.style.ERROR('Invalid types:')
                    )
                    for issue in issues['invalid_types']:
                        self.stdout.write(f'  - {issue}')

                if issues['warnings']:
                    self.stdout.write(
                        self.style.WARNING('Warnings:')
                    )
                    for warning in issues['warnings']:
                        self.stdout.write(f'  - {warning}')

                return 1

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error validating constants: {e}')
            )
            return 1

        return 0