from django.db import models
from common.models import BaseModel


# Output type choices — what the report/form produces
REPORT_OUTPUT_CHOICES = (
    ("print", "Print / PDF"),
    ("screen", "Screen form"),
    ("email", "Email (SMTP)"),
    ("api", "POST to external endpoint"),
    ("json", "Return structured JSON"),
    ("export", "CSV / Excel download"),
    ("label", "Label / barcode print"),
    ("merge", "Word / spreadsheet merge"),
)

# Category choices — grouping for the report/form menu
REPORT_CATEGORY_CHOICES = (
    ("form", "Form"),
    ("report", "Report"),
    ("statement", "Statement"),
    ("list", "List"),
    ("summary", "Summary"),
    ("letter", "Letter / Email"),
    ("label", "Label"),
    ("export", "Export"),
    ("function", "Function"),
    ("utility", "Utility"),
    ("tally", "Tally / Calculation"),
    ("dashboard", "Dashboard widget"),
)


class Report(BaseModel):
    """Report / print definition — one record per report per model.

    Stored in the ``reports`` table. Synced from canonical definitions in
    ``common/sync_wcreact/reports.py`` via ``python manage.py sync_reports``.

    Fields inherited from BaseModel:
        security_level (int) — 0 = unrestricted, higher = more restricted
        is_active (bool)     — soft-enable/disable
    """

    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    model_name = models.CharField(
        max_length=255, blank=True, null=True, db_index=True,
        help_text="Canonical model key (e.g. 'customer', 'order')",
    )
    record_id = models.CharField(
        max_length=255, blank=True, null=True, db_index=True,
        help_text="Optional: tie to a specific record",
    )
    output_type = models.CharField(
        max_length=30, blank=True, null=True,
        choices=REPORT_OUTPUT_CHOICES, default="print",
        help_text="What the report produces (print, email, api, json, export, label)",
    )
    category = models.CharField(
        max_length=30, blank=True, null=True,
        choices=REPORT_CATEGORY_CHOICES, default="report",
        help_text="Menu grouping (report, statement, list, summary, etc.)",
    )
    role_required = models.CharField(
        max_length=120, blank=True, null=True,
        help_text="Role required to see/run this report (blank = all users)",
    )
    sort_order = models.IntegerField(
        default=0,
        help_text="Display order within the model's report menu",
    )
    config = models.JSONField(
        default=dict,
        help_text="Extended config: endpoint_url, template, parameters, etc.",
    )
    script_before = models.TextField(
        blank=True, default="",
        help_text="Setup phase: initialize accumulators, apply filters, establish selections",
    )
    script_during = models.TextField(
        blank=True, default="",
        help_text="Calculation phase: the business logic — line extensions, bucket assignments, GL accumulation",
    )
    script_after = models.TextField(
        blank=True, default="",
        help_text="Completion phase: write results, format output, send notifications, update records",
    )

    class Meta:
        db_table = 'reports'
        ordering = ['model_name', 'sort_order', 'name']

    def __str__(self):
        return f"{self.name or 'Report'} ({self.model_name}) [{self.output_type}]"
