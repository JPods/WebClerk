from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone

class SoftDeleteLedger(models.Model):
    """
    Tracks soft-deleted objects and when to hard-delete them.
    """

    @property
    def dt_created(self):
        # CoreModel stores dt_created as epoch ms integer; convert to datetime
        val = getattr(self, '_dt_created', None)
        if val is None:
            # Try to get from BaseModel/CoreModel if present
            val = getattr(self, 'dt_created', None)
        if val:
            from datetime import datetime, timezone
            # If already datetime, return as is
            if isinstance(val, datetime):
                return val
            # If integer, convert from ms to datetime
            try:
                return datetime.fromtimestamp(int(val) / 1000, tz=timezone.utc)
            except Exception:
                return None
        return None

    @property
    def dt_modified(self):
        val = getattr(self, '_dt_modified', None)
        if val is None:
            val = getattr(self, 'dt_modified', None)
        if val:
            from datetime import datetime, timezone
            if isinstance(val, datetime):
                return val
            try:
                return datetime.fromtimestamp(int(val) / 1000, tz=timezone.utc)
            except Exception:
                return None
        return None
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="soft_delete_entries", db_column='contenttype_id')
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey("content_type", "object_id")

    dt_purge = models.DateTimeField(db_index=True)
    # dt_created is inherited from BaseModel/CoreModel

    class Meta:
        indexes = [
            models.Index(fields=["dt_purge"]),
            models.Index(fields=["content_type", "object_id"]),
        ]
        unique_together = (("content_type", "object_id"),)

    @classmethod
    def schedule(cls, obj, retention_days: int = 60):
        ct = ContentType.objects.get_for_model(obj.__class__)
        when = timezone.now() + timezone.timedelta(days=int(retention_days or 60))
        entry, _ = cls.objects.update_or_create(
            content_type=ct,
            object_id=obj.pk,
            defaults={"dt_purge": when},
        )
        return entry