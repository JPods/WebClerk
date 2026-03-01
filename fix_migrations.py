#!/usr/bin/env python
"""
Fix inconsistent migration history by marking duplicate migrations as applied.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()

from django.db.migrations.recorder import MigrationRecorder

def fix_migrations():
    """Mark duplicate migrations with ' 2' suffix as applied."""
    migrations_to_fix = [
        ('core', '0011_merge_20260110_1331 2'),
        ('core', '0012_alter_contact_role 2'),
        ('core', '0013_contact_customer_id_contact_employee_id_and_more 2'),
        ('transactions', '0015_merge_20260110_1331 2'),
    ]
    
    for app, name in migrations_to_fix:
        obj, created = MigrationRecorder.Migration.objects.get_or_create(
            app=app,
            name=name
        )
        if created:
            print(f"✓ Marked {app}.{name} as applied")
        else:
            print(f"• {app}.{name} already applied")
    
    print("\n✅ Migration history fixed!")

if __name__ == '__main__':
    fix_migrations()
