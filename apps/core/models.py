from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone

class SoftDeleteLedger(models.Model):
    """
    Tracks soft-deleted objects and when to hard-delete.
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="soft_delete_entries")
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey("content_type", "object_id")

    purge_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["purge_at"]),
            models.Index(fields=["content_type", "object_id"]),
        ]
        unique_together = (("content_type", "object_id"),)

    @classmethod
    def schedule(cls, obj, retention_days: int = 60):
        ct = ContentType.objects.get_for_model(obj.__class__)
        purge_at = timezone.now() + timezone.timedelta(days=int(retention_days or 60))
        entry, _ = cls.objects.update_or_create(
            content_type=ct,
            object_id=obj.pk,
            defaults={"purge_at": purge_at},
        )
        return entry