"""
Alice's data conversion models — alice_conversion database.

These tables document everything Alice learns while converting a supplier's
messy data into clean WC3 bundles. Multiple passes, multiple oddities,
multiple decisions — all recorded here.

The conversion database is Alice's workbench. The noise lives here.
WC3 (commerce_expert) only sees the clean bundle at the end.
"""

import uuid
from django.db import models
from django.utils import timezone


class ConversionProject(models.Model):
    """One conversion effort — a supplier, a data set, a goal."""

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255)
    supplier_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=40, default='active', db_index=True)
    # Which WC3 connection will receive the final bundle
    connection_id = models.BigIntegerField(null=True, blank=True,
        help_text="FK to sync.Connection in commerce_expert (not a DB FK — cross-database)")
    # How many passes Alice has run
    pass_count = models.IntegerField(default=0)
    # Summary stats after each pass
    stats = models.JSONField(default=dict, blank=True)
    dt_created = models.DateTimeField(default=timezone.now)
    dt_modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'conversion_project'

    def __str__(self):
        return f"{self.name} ({self.status})"


class SourceFile(models.Model):
    """A file the user gave Alice to convert."""

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    project = models.ForeignKey(ConversionProject, on_delete=models.CASCADE, related_name='source_files')
    filename = models.CharField(max_length=500)
    file_type = models.CharField(max_length=20, help_text="csv, tsv, xlsx, json, pdf")
    file_size = models.BigIntegerField(default=0)
    file_hash = models.CharField(max_length=64, blank=True, help_text="SHA-256")
    # Raw headers as found in the file
    raw_headers = models.JSONField(default=list, blank=True)
    row_count = models.IntegerField(default=0)
    # Sample rows (first 20) for Claude to examine
    sample_rows = models.JSONField(default=list, blank=True)
    encoding = models.CharField(max_length=40, blank=True)
    delimiter = models.CharField(max_length=10, blank=True)
    dt_created = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'conversion_source_file'

    def __str__(self):
        return f"{self.filename} ({self.row_count} rows)"


class ColumnMap(models.Model):
    """How Alice mapped a source column to a WC3 field.

    One row per source column. Claude proposes, Alice records, user confirms.
    Multiple passes may refine the mapping.
    """

    source_file = models.ForeignKey(SourceFile, on_delete=models.CASCADE, related_name='column_maps')
    source_column = models.CharField(max_length=255, help_text="Column name as it appears in the file")
    target_model = models.CharField(max_length=80, blank=True, help_text="WC3 model name: Item, OrgBase, BillOfMaterial")
    target_field = models.CharField(max_length=80, blank=True, help_text="WC3 field name or JSON path: price.base, gls.inventory")
    confidence = models.FloatField(default=0.0, help_text="Claude's confidence 0.0-1.0")
    transform = models.CharField(max_length=255, blank=True,
        help_text="Transformation to apply: normalize_uom, parse_decimal, map_gl, etc.")
    status = models.CharField(max_length=20, default='proposed', db_index=True,
        help_text="proposed | confirmed | rejected | unmapped")
    # What Claude said about this mapping
    reasoning = models.TextField(blank=True)
    # Sample values from source for this column
    sample_values = models.JSONField(default=list, blank=True)
    pass_number = models.IntegerField(default=1)
    dt_created = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'conversion_column_map'

    def __str__(self):
        return f"{self.source_column} -> {self.target_model}.{self.target_field} ({self.status})"


class Oddity(models.Model):
    """Something wrong or weird Alice found in the source data.

    This is the core documentation table. Every data quality problem,
    every inconsistency, every ambiguity gets a row. This is how Alice
    builds institutional knowledge about a supplier's data habits.
    """

    SEVERITY_CHOICES = [
        ('info', 'Info — notable but not blocking'),
        ('warning', 'Warning — needs human review'),
        ('error', 'Error — blocks conversion'),
        ('pattern', 'Pattern — recurring issue across rows'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    project = models.ForeignKey(ConversionProject, on_delete=models.CASCADE, related_name='oddities')
    source_file = models.ForeignKey(SourceFile, on_delete=models.CASCADE, null=True, blank=True, related_name='oddities')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='warning', db_index=True)
    category = models.CharField(max_length=80, db_index=True,
        help_text="Type of oddity: duplicate_sku, ambiguous_uom, missing_price, bad_date, encoding, gl_unmapped, etc.")
    description = models.TextField()
    # Where in the source
    source_column = models.CharField(max_length=255, blank=True)
    source_row = models.IntegerField(null=True, blank=True)
    source_value = models.TextField(blank=True, help_text="The actual value that caused the oddity")
    # How many rows affected (for pattern-type oddities)
    affected_count = models.IntegerField(default=1)
    # What Alice did about it
    resolution = models.CharField(max_length=40, blank=True, db_index=True,
        help_text="pending | auto_fixed | user_fixed | skipped | escalated")
    resolution_detail = models.TextField(blank=True)
    pass_number = models.IntegerField(default=1)
    dt_created = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'conversion_oddity'
        verbose_name_plural = 'oddities'

    def __str__(self):
        return f"[{self.severity}] {self.category}: {self.description[:80]}"


class StagingRow(models.Model):
    """A row of converted data waiting for bundle assembly.

    After Alice maps columns and resolves oddities, each valid row
    lands here in WC3 schema format. Bundle assembly reads from staging.
    """

    source_file = models.ForeignKey(SourceFile, on_delete=models.CASCADE, related_name='staging_rows')
    source_row_number = models.IntegerField()
    target_model = models.CharField(max_length=80, db_index=True, help_text="Item, BillOfMaterial, OrgBase, etc.")
    # The converted data in WC3 schema format
    data = models.JSONField(default=dict)
    status = models.CharField(max_length=20, default='staged', db_index=True,
        help_text="staged | bundled | rejected | needs_review")
    # Links to oddities that affect this row
    oddity_ids = models.JSONField(default=list, blank=True, help_text="List of Oddity IDs affecting this row")
    pass_number = models.IntegerField(default=1)
    dt_created = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'conversion_staging_row'

    def __str__(self):
        return f"Row {self.source_row_number} -> {self.target_model} ({self.status})"


class PassLog(models.Model):
    """Record of each conversion pass Alice runs.

    Data conversion is never one pass. Each pass finds new oddities,
    refines mappings, and gets closer to a clean bundle. This table
    records what happened on each pass so Alice and the user can see
    the progression.
    """

    project = models.ForeignKey(ConversionProject, on_delete=models.CASCADE, related_name='passes')
    pass_number = models.IntegerField()
    status = models.CharField(max_length=20, default='running')
    # What this pass focused on
    focus = models.TextField(blank=True, help_text="What Alice looked at: initial_mapping, oddity_resolution, validation, etc.")
    # Stats
    rows_processed = models.IntegerField(default=0)
    rows_staged = models.IntegerField(default=0)
    rows_rejected = models.IntegerField(default=0)
    oddities_found = models.IntegerField(default=0)
    oddities_resolved = models.IntegerField(default=0)
    # Claude API usage
    llm_model = models.CharField(max_length=60, blank=True)
    llm_calls = models.IntegerField(default=0)
    llm_input_tokens = models.IntegerField(default=0)
    llm_output_tokens = models.IntegerField(default=0)
    duration_seconds = models.FloatField(default=0)
    dt_started = models.DateTimeField(default=timezone.now)
    dt_completed = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'conversion_pass_log'
        unique_together = [('project', 'pass_number')]

    def __str__(self):
        return f"Pass {self.pass_number} on {self.project.name} ({self.status})"
