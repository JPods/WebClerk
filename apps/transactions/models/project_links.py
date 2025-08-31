from django.db import models
from .projects import Project

LINK_MODEL_CHOICES = [
    ("proposal", "Proposal"),
    ("order", "Order"),
    ("invoice", "Invoice"),
    ("purchase", "Purchase"),
    ("workorder", "Workorder"),
    ("requisition", "Requisition"),
]


class ProjectAssociation(models.Model):
    """Formal link between a Project and a transactional header record.

    We keep this intentionally narrow (not generic foreign key) for predictable
    queries and to discourage over‑use. The object_id refers to the primary key
    of the target model identified by `model_code`.
    """

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="associations")
    model_code = models.CharField(max_length=32, choices=LINK_MODEL_CHOICES, db_index=True)
    object_id = models.BigIntegerField(db_index=True)
    created_dt = models.BigIntegerField(auto_created=False, default=0, db_index=True)

    class Meta:
        db_table = "project_associations"
        unique_together = ("project", "model_code", "object_id")
        indexes = [
            models.Index(fields=["model_code", "object_id"], name="projassoc_target_idx"),
        ]

    def __str__(self):  # pragma: no cover - debug convenience
        return f"Proj#{getattr(self, 'project_id', '?')}:{self.model_code}:{self.object_id}"
