# filepath: core/signals/pending_trigger.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models.pending import Pending
from core.constants.keyword_requirements import get_keyword_requirements

@receiver(post_save)
def create_pending_on_save(sender, instance, created, **kwargs):
    table_name = getattr(instance._meta, 'db_table', None)
    record_id = getattr(instance, 'id', None)
    if not table_name or not record_id:
        return

    # Lazily fetch requirements
    keyword_requirements = get_keyword_requirements()

    if table_name in keyword_requirements:
        Pending.objects.create(
            table_name=table_name,
            record_id=record_id,
            data={},  # Optionally pass relevant data
            # metadata, prefs, refs will be auto-initialized
        )
