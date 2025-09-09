import sys
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.core.models.pending import Pending
from apps.core.constants.keyword_requirements import get_keyword_requirements
from django.db import connection
from apps.core.services.wcapi_registry import to_model_name

@receiver(post_save)
def create_pending_on_save(sender, instance, created, **kwargs):
    if 'makemigrations' in sys.argv or 'migrate' in sys.argv:
        return
    model_key = getattr(instance._meta, 'db_table', None)  # physical table identifier
    record_id = getattr(instance, 'id', None)
    if not model_key or not record_id:
        return

    # Only create Pending if keyword requirements registered for this model
    try:
        with connection.cursor() as cur:
            table_list = connection.introspection.get_table_list(cur)
            existing_tables = {t.name for t in table_list}
        # Ensure supporting tables exist before proceeding
        if 'settings' not in existing_tables or 'pending' not in existing_tables:
            return
        if model_key in get_keyword_requirements():
            model_name = to_model_name(model_key) or model_key
            Pending.objects.create(
                model_name=model_name,
                record_id=record_id,
                ida=f"{model_name}:{record_id}",
                data={},
            )
    except Exception as e:  # pragma: no cover
        msg = str(e).lower()
        if 'no such table' in msg or 'does not exist' in msg:
            return
        raise


