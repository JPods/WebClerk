# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/communications/models/domain.py
from django.db import models
from common.models import BaseModel

DOMAIN_TYPE_CHOICES = [
    ('website', 'Website'),
    ('linkedin', 'LinkedIn'),
    ('facebook', 'Facebook'),
    ('twitter', 'Twitter'),
    ('github', 'GitHub'),
    ('other', 'Other'),
]

class Domain(BaseModel):
    path = models.CharField(max_length=255, blank=True, db_index=True, help_text="URL or handle (indexed)")
    type = models.CharField(max_length=50, blank=True, choices=DOMAIN_TYPE_CHOICES, db_index=True)
    comment = models.TextField(blank=True, default="", help_text="General notes")
    
    status = models.CharField(max_length=30, blank=True, default='active', db_index=True)
    security_level = models.PositiveSmallIntegerField(default=0, db_index=True)
    sequence = models.PositiveIntegerField(default=0, db_index=True, help_text="Custom ordering value")
    count_accessed = models.PositiveIntegerField(default=0, help_text="Access counter")
    is_active = models.BooleanField(default=True, db_index=True)

    # all metadata changes inside common/models/BaseModel.py

    class Meta:
        db_table = 'domains'
        indexes = [
            models.Index(fields=['path']),
            models.Index(fields=['type', 'status']),
            models.Index(fields=['security_level']),
        ]
        
    def __str__(self):
        return f"{self.path}, {self.type}"

    # lightweight helpers
    def increment_access(self, by: int = 1, save: bool = True):
        self.count_accessed = (self.count_accessed or 0) + by
        if save:
            self.save(update_fields=['count_accessed', 'modified_dt', 'version'])
        return self.count_accessed
    