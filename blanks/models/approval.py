from django.db import models

class Approval(models.Model):
    TYPE_CHOICES = [
        ('approved', 'Approved'),
        ('pending', 'Pending'),
        ('rejected', 'Rejected'),
    ]
    
    name = models.CharField(
        max_length=255,
        help_text="Name or identifier for the approval"
    )
    value = models.TextField(
        blank=True,
        help_text="Value or details of the approval"
    )
    type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        default='pending',
        help_text="Type of approval"
    )
    seq = models.CharField(
        max_length=50,
        blank=True,
        help_text="Sequence identifier"
    )
    dt_approval = models.BigIntegerField(
        help_text="Approval datetime as Unix timestamp (milliseconds)"
    )

    class Meta:
        db_table = 'approval'
        verbose_name = 'Approval'
        verbose_name_plural = 'Approvals'

    def __str__(self):
        return f"Approval ({self.name}, Type: {self.type})"