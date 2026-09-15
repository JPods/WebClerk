# Convert contact_id BigIntegerField → ForeignKey to Contact.
# Both use DB column name 'contact_id', so data is preserved in place.
# We use SeparateDatabaseAndState to update Django's state while
# only adding FK constraints in the database.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


MODELS = ['address', 'domain', 'email', 'phone']
TABLES = {
    'address': 'locations',
    'domain': 'domains',
    'email': 'emails',
    'phone': 'phones',
}
INDEX_NAMES = {
    'address': 'locations_contact_2fa128_idx',
    'domain': 'domains_contact_91ca24_idx',
    'email': 'emails_contact_e2ee94_idx',
    'phone': 'phones_contact_9a46af_idx',
}


def add_fk_constraints(apps, schema_editor):
    """Add FK constraints on existing contact_id columns."""
    for model, table in TABLES.items():
        # Clear orphan references first (contact_id values with no matching contact)
        schema_editor.execute(
            f"UPDATE {table} SET contact_id = NULL "
            f"WHERE contact_id IS NOT NULL "
            f"AND contact_id NOT IN (SELECT id FROM contacts);"
        )
        # Add FK constraint
        schema_editor.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {table}_contact_id_fk "
            f"FOREIGN KEY (contact_id) REFERENCES contacts(id) "
            f"ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;"
        )


def drop_fk_constraints(apps, schema_editor):
    """Remove FK constraints (reverse)."""
    for model, table in TABLES.items():
        schema_editor.execute(
            f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_contact_id_fk;"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0006_comms_fk_to_values'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Remove old indexes first
        migrations.RemoveIndex(model_name='address', name='locations_contact_2fa128_idx'),
        migrations.RemoveIndex(model_name='domain', name='domains_contact_91ca24_idx'),
        migrations.RemoveIndex(model_name='email', name='emails_contact_e2ee94_idx'),
        migrations.RemoveIndex(model_name='phone', name='phones_contact_9a46af_idx'),

        # Swap BigInt → FK in Django state + add FK constraint in DB
        # The DB column (contact_id) stays the same — only the constraint changes.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name='address', name='contact_id'),
                migrations.RemoveField(model_name='domain', name='contact_id'),
                migrations.RemoveField(model_name='email', name='contact_id'),
                migrations.RemoveField(model_name='phone', name='contact_id'),
                migrations.AddField(
                    model_name='address', name='contact',
                    field=models.ForeignKey(blank=True, null=True, help_text='Owning contact',
                                            on_delete=django.db.models.deletion.SET_NULL,
                                            related_name='addresses', to=settings.AUTH_USER_MODEL),
                ),
                migrations.AddField(
                    model_name='domain', name='contact',
                    field=models.ForeignKey(blank=True, null=True, help_text='Owning contact',
                                            on_delete=django.db.models.deletion.SET_NULL,
                                            related_name='domains', to=settings.AUTH_USER_MODEL),
                ),
                migrations.AddField(
                    model_name='email', name='contact',
                    field=models.ForeignKey(blank=True, null=True, help_text='Owning contact',
                                            on_delete=django.db.models.deletion.SET_NULL,
                                            related_name='emails', to=settings.AUTH_USER_MODEL),
                ),
                migrations.AddField(
                    model_name='phone', name='contact',
                    field=models.ForeignKey(blank=True, null=True, help_text='Owning contact',
                                            on_delete=django.db.models.deletion.SET_NULL,
                                            related_name='phones', to=settings.AUTH_USER_MODEL),
                ),
            ],
            database_operations=[
                migrations.RunPython(add_fk_constraints, drop_fk_constraints),
            ],
        ),

        # Re-add indexes on the FK field
        migrations.AddIndex(
            model_name='address',
            index=models.Index(fields=['contact'], name='locations_contact_2fa128_idx'),
        ),
        migrations.AddIndex(
            model_name='domain',
            index=models.Index(fields=['contact'], name='domains_contact_91ca24_idx'),
        ),
        migrations.AddIndex(
            model_name='email',
            index=models.Index(fields=['contact'], name='emails_contact_e2ee94_idx'),
        ),
        migrations.AddIndex(
            model_name='phone',
            index=models.Index(fields=['contact'], name='phones_contact_9a46af_idx'),
        ),
    ]
