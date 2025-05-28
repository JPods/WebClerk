from django.db import models
from django.contrib.postgres.fields import JSONField

class Refs(models.Model):
    keywords = models.TextField(
        db_index=True,
        help_text="Denormalized keywords including user-selected keytags, indexed for search"
    )
    tags = models.TextField(
        blank=True,
        help_text="User-defined tags, stored as a string (e.g., comma-separated)"
    )
    links = JSONField(
        default=list,
        help_text="List of link objects: [{tableName: string, id: long, denormalized: string, comment: string}]"
    )

    class Meta:
        db_table = 'refs'
        verbose_name = 'Reference'
        verbose_name_plural = 'References'
        indexes = [
            models.Index(fields=['keywords'], name='keywords_idx')
        ]

    def __str__(self):
        return f"Refs (Keywords: {self.keywords[:50]}...)"