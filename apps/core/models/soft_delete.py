from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone

class SoftDeleteLedger(models.Model):
    """
    Tracks soft-deleted objects and when to hard-delete them.
    """
    contenttype_id = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="soft_delete_entries")
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey("contenttype_id", "object_id")

    dt_purge = models.DateTimeField(db_index=True)
    dt_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["dt_purge"]),
            models.Index(fields=["contenttype_id", "object_id"]),
        ]
        unique_together = (("contenttype_id", "object_id"),)

    @classmethod
    def schedule(cls, obj, retention_days: int = 60):
        ct = ContentType.objects.get_for_model(obj.__class__)
        when = timezone.now() + timezone.timedelta(days=int(retention_days or 60))
        entry, _ = cls.objects.update_or_create(
            contenttype_id=ct,
            object_id=obj.pk,
            defaults={"dt_purge": when},
        )
        return entry