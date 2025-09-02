import sys
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.core.models.pending import Pending
from apps.core.constants.keyword_requirements import get_keyword_requirements
from django.db import connection

@receiver(post_save)
def create_pending_on_save(sender, instance, created, **kwargs):
    if 'makemigrations' in sys.argv or 'migrate' in sys.argv:
        return
    table_name = getattr(instance._meta, 'db_table', None)
    record_id = getattr(instance, 'id', None)
    if not table_name or not record_id:
        return

    # Only create Pending if denormalized keyword requirements exist
    try:
        existing_tables = set(connection.introspection.table_names())
        # If settings or pending table not yet created, skip
        if 'settings' not in existing_tables or 'pending' not in existing_tables:
            return
        if table_name in get_keyword_requirements():
            Pending.objects.create(
                table_name=table_name,
                record_id=record_id,
                data={},  # Optionally pass relevant data
            )
    except Exception as e:
        if 'no such table' in str(e).lower():  # sqlite wording
            return
        raise


