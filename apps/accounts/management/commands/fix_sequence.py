from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Fix database auto-increment sequences that are out of sync with existing data"

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            help='Model name to fix (e.g., "ExchangeRate")',
        )
        parser.add_argument(
            '--app',
            type=str,
            help='App name (e.g., "accounts")',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Fix all sequences in the database',
        )

    def handle(self, *args, **options):
        if options['all']:
            self.fix_all_sequences()
        elif options['model'] and options['app']:
            self.fix_specific_sequence(options['app'], options['model'])
        else:
            self.stdout.write(self.style.ERROR('Please specify --model and --app, or use --all'))

    def fix_specific_sequence(self, app_name, model_name):
        """Fix sequence for a specific model"""
        try:
            from django.apps import apps
            model = apps.get_model(app_name, model_name)
            table_name = model._meta.db_table
            sequence_name = f"{table_name}_id_seq"
            
            self.stdout.write(f"Fixing sequence for {app_name}.{model_name} (table: {table_name})")
            
            with connection.cursor() as cursor:
                # Get current max ID
                cursor.execute(f"SELECT max(id) FROM {table_name}")
                result = cursor.fetchone()
                max_id = result[0] if result and result[0] is not None else 0
                
                if max_id is None:
                    self.stdout.write(self.style.WARNING(f"No records found in {table_name}, setting sequence to 1"))
                    cursor.execute(f"SELECT setval('{sequence_name}', 1)")
                else:
                    cursor.execute(f"SELECT setval('{sequence_name}', {max_id} + 1)")
                    self.stdout.write(self.style.SUCCESS(f"Sequence {sequence_name} reset to {max_id + 1}"))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fixing sequence: {e}"))

    def fix_all_sequences(self):
        """Fix all sequences in the database"""
        from django.apps import apps
        from django.db import connection
        
        self.stdout.write("Scanning all models for sequence issues...")
        
        fixed_count = 0
        
        with connection.cursor() as cursor:
            for model in apps.get_models():
                try:
                    table_name = model._meta.db_table
                    sequence_name = f"{table_name}_id_seq"
                    
                    # Check if sequence exists using PostgreSQL system catalogs
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM pg_class c
                            JOIN pg_namespace n ON n.oid = c.relnamespace
                            WHERE c.relkind = 'S' 
                            AND c.relname = %s
                            AND n.nspname = 'public'
                        )
                    """, [sequence_name])
                    
                    result = cursor.fetchone()
                    if result and result[0]:
                        # Get current max ID and sequence value
                        cursor.execute(f"SELECT COALESCE(max(id), 0) FROM {table_name}")
                        result = cursor.fetchone()
                        max_id = result[0] if result and result[0] is not None else 0
                        
                        cursor.execute(f"SELECT last_value FROM {sequence_name}")
                        result = cursor.fetchone()
                        current_sequence = result[0] if result else 1
                        
                        # If sequence is behind, fix it
                        if current_sequence <= max_id:
                            new_sequence = max_id + 1
                            cursor.execute(f"SELECT setval('{sequence_name}', {new_sequence})")
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Fixed {table_name}: sequence {sequence_name} {current_sequence} -> {new_sequence}"
                                )
                            )
                            fixed_count += 1
                        else:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"OK {table_name}: sequence {sequence_name} is current ({current_sequence})"
                                )
                            )
                            
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error processing {model.__name__}: {e}")
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f"Sequence fix complete. Fixed {fixed_count} sequences.")
        )