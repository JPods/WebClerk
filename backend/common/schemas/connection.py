"""
Pydantic schemas for Connection JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# -- .config ----------------------------------------------------------------

class CarrierCredentials(BaseModel):
    """Carrier API credentials (UPS, FedEx, USPS, DHL)."""
    client_id: str = ''
    client_secret: str = ''
    account_number: str = ''

    class Config:
        extra = "forbid"  # carrier-specific fields


class CarrierSettings(BaseModel):
    """Carrier-specific operational settings."""
    test_mode: bool = True
    label_format: str = 'pdf'
    fuel_factor: float = 0.0
    handling_charge: float = 0.0
    markup_percent: float = 0.0

    class Config:
        extra = "forbid"


class EscalationProtocol(BaseModel):
    """Alice → Claude Code escalation configuration."""
    action_ida_prefix: str = ''
    required_fields: list[str] = Field(default_factory=list)
    priority_levels: list[str] = Field(default_factory=list)
    pickup_trigger: str = ''
    resolution: str = ''


class ImportLesson(BaseModel):
    """What Alice learned from processing this source.

    Each successful import adds lessons. Confidence increases with
    repeated successful mappings. Alice reads these before attempting
    a new import from the same source — she gets smarter per source.
    """
    dt: str = ''                             # UTC ISO-8601
    column_source: str = ''                  # source file column name
    field_target: str = ''                   # WC3 model.field it maps to
    transform: str = 'direct'               # direct, split, lookup, formula, skip
    transform_detail: str = ''              # formula or lookup table if not direct
    note: str = ''                          # why this mapping — what Alice observed
    confidence: float = 1.0                 # 0.0-1.0, increases with repeated success


class UserInstruction(BaseModel):
    """User-provided rules for this source.

    Users tell Alice how to handle edge cases. These override Alice's
    inferences. Stored per-Connection so each vendor/source has its own
    instruction set.
    """
    dt: str = ''                             # UTC ISO-8601
    instruction: str = ''                    # what the user said to do
    applies_to: str = 'all'                 # column name, field name, or 'all'
    given_by: str = ''                      # contact ida who gave instruction


class ImportConfig(BaseModel):
    """Import pipeline configuration — stored in Connection.config.import_config.

    All data transformation happens OUTSIDE WC3. Alice reads the source file,
    applies lessons + user_instructions, produces a standard bundle.json.
    The bundle enters WC3 through the Connection's sync pipeline.

    No parsing inside WC3. No custom importers. One path: file → Alice → bundle → Connection.
    """
    model_target: str = ''                   # WC3 model name: item, contact, order, etc.
    file_type: str = 'csv'                   # csv, xlsx, json, xml, tsv
    delimiter: str = ','                     # for CSV/TSV
    header_row: int = 0                      # 0-based row index for column headers
    lessons: list[ImportLesson] = Field(default_factory=list)
    user_instructions: list[UserInstruction] = Field(default_factory=list)
    column_map: dict[str, str] = Field(default_factory=dict)  # confirmed column→field
    skip_rules: list[str] = Field(default_factory=list)       # conditions that skip a row
    last_import_dt: str = ''
    last_import_count: int = 0
    last_import_errors: int = 0
    last_import_file: str = ''               # original filename for reference


class ImportBundleHeader(BaseModel):
    """Header for import bundle.json — user signs off before import.

    This is the accountability layer. No bundle enters WC3 without a header
    that identifies who prepared it, who approved it, where the data came from,
    and what Athena found during review.
    """
    # ── Source identification ──
    source_name: str = ''                    # vendor/supplier/system name
    source_file: str = ''                    # original file path or URL
    source_format: str = ''                  # csv, xlsx, json, etc.
    source_encoding: str = 'utf-8'
    source_hash: str = ''                    # SHA-256 of original file (tamper detection)

    # ── Content summary ──
    model_target: str = ''                   # WC3 model the records map to
    record_count: int = 0                    # total records in bundle
    skipped_count: int = 0                   # records skipped (with reasons in skip_log)
    error_count: int = 0                     # records that failed mapping
    field_count: int = 0                     # number of fields mapped per record
    size_bytes: int = 0                      # bundle file size

    # ── Trust & accountability ──
    trust_level: str = 'unverified'          # unverified, known, trusted, certified
    prepared_by: str = ''                    # contact ida who prepared/ran the import
    prepared_dt: str = ''                    # UTC ISO-8601
    approved_by: str = ''                    # contact ida who signed off
    approved_dt: str = ''                    # UTC ISO-8601 — blank until signed off
    point_of_contact: str = ''              # contact ida at the source (vendor rep, etc.)
    responsible_person: str = ''            # contact ida accountable for data quality
    connection_ida: str = ''                # Connection record ida

    # ── Athena review ──
    athena_reviewed: bool = False            # did Athena inspect this bundle?
    athena_review_dt: str = ''               # UTC ISO-8601
    athena_findings: list[str] = Field(default_factory=list)  # concerns flagged
    athena_approved: bool = False            # Athena cleared for import?
    athena_risk_level: str = 'unknown'       # low, medium, high, blocked

    # ── Processing notes ──
    notes: str = ''                          # free text — preparer's notes
    skip_log: list[str] = Field(default_factory=list)  # why each skipped row was skipped

    class Config:
        extra = "forbid"


class ConnectionConfig(ConfigBase):
    """Integration protocol metadata.

    Connection.config varies by channel type: bundle sync, carrier API,
    agent escalation, server deployment, or **import pipeline**.

    For imports: all data transformation happens outside WC3. Alice reads
    source files, applies import_config.lessons and user_instructions,
    produces a bundle.json with a signed ImportBundleHeader. Athena reviews
    for hidden harms. User approves. Bundle enters WC3 through sync pipeline.
    """
    channel: str = ''                        # bundle, action_queue, carrier, server, import
    direction: str = ''                      # push, pull, bidirectional
    endpoint: str = ''                       # URL or host
    auth_method: str = ''                    # api_key, oauth, token
    api_key_setting: str = ''                # Setting ida for credentials
    content_types: list[str] = Field(default_factory=list)
    review_required: bool = False
    # Import pipeline (channel='import')
    import_config: Optional[ImportConfig] = None
    # Carrier-specific
    carrier_code: str = ''                   # ups, fedex, usps, dhl
    credentials: Optional[CarrierCredentials] = None
    settings: Optional[CarrierSettings] = None
    # Agent escalation
    from_agent: str = ''
    to_agent: str = ''
    escalation_protocol: Optional[EscalationProtocol] = None

    class Config:
        extra = "forbid"  # channel-specific extensions


# -- .metadata (inherits MetadataBase) --------------------------------------

class ConnectionMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class ConnectionPrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class ConnectionRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
