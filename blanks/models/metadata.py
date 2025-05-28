from django.db import models
from django.contrib.postgres.fields import JSONField

class Metadata(models.Model):
    security = models.BigIntegerField(
        help_text="Security level or identifier"
    )
    publish = models.CharField(
        max_length=255,
        help_text="Publication status or identifier"
    )
    priority = models.CharField(
        max_length=50,
        help_text="Priority level"
    )
    version = models.CharField(
        max_length=50,
        help_text="Version identifier"
    )
    approvals = JSONField(
        default=list,
        help_text="List of approval records: [{dt: long, id_contact: long, attention: string, purpose: string, status: string, comment: string}]"
    )
    health = JSONField(
        default=dict,
        help_text="Health status: {created: {dt: long, id_contact: long}, updated: {dt: long, id_contact: long, count: int}, dtCompleted: {dt: long, id_contact: long}, dtExpire: {dt: long, id_contact: long}, dtRetired: {dt: long, id_contact: long}}"
    )
    history = JSONField(
        default=list,
        help_text="History records (array of arbitrary objects)"
    )
    profiles = JSONField(
        default=list,
        help_text="Profile records: [{value: string, sequence: int, type: string, comment: string}]"
    )

    class Meta:
        db_table = 'metadata'
        verbose_name = 'Metadata'
        verbose_name_plural = 'Metadata'

    def __str__(self):
        return f"Metadata (Version: {self.version}, Priority: {self.priority})"