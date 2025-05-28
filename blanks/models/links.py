from django.db import models

class LinksModel(models.Model):
    table_name = models.CharField(
        max_length=255,
        help_text="Name of the table"
    )
    record_id = models.BigIntegerField(
        help_text="ID of the record"
    )
    denorm = models.TextField(
        blank=True,
        help_text="Denormalized data, possibly controlled by a template"
    )
    comment = models.TextField(
        blank=True,
        null=True,
        help_text="Arbitrary comment"
    )

    class Meta:
        db_table = 'links'
        verbose_name = 'Link'
        verbose_name_plural = 'Links'

    def __str__(self):
        return f"LinksModel (Table: {self.table_name}, Record ID: {self.record_id})"