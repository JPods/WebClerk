from django.db import models
from django.contrib.postgres.fields import JSONField

class HistoryModel(models.Model):
    created = JSONField(
        default=dict,
        help_text="Stores creation data: {dt: datetime, id_contact: long, attention: string}"
    )
    modified = JSONField(
        default=dict,
        help_text="Stores modification data: {dt: datetime, id_contact: long, attention: string, why: string, count: int}"
    )
    active = JSONField(
        default=dict,
        help_text="Stores activation data: {dt: datetime, id_contact: long, attention: string}"
    )
    expire = JSONField(
        default=dict,
        help_text="Stores expiration data: {dt: datetime, id_contact: long, attention: string}"
    )
    retired = JSONField(
        default=dict,
        help_text="Stores retirement data: {dt: datetime, id_contact: long, attention: string}"
    )
    last_used = JSONField(
        default=dict,
        help_text="Stores last used data: {dt: datetime, id_contact: long, attention: string, count: int}"
    )
    sync = JSONField(
        default=dict,
        help_text="Stores sync data: {dt: datetime, id_sync: long}"
    )

    class Meta:
        db_table = 'history'
        verbose_name = 'History'
        verbose_name_plural = 'Histories'

    def __str__(self):
        return f"HistoryModel (ID: {self.id}, Created: {self.created.get('dt', 'N/A')})"