"""
Pydantic schemas for JSON envelope fields.

Every BaseModel record has six JSON fields. These schemas define what goes
in each one, per model. Validation on write, documentation by existence,
Alice reads the schemas.

Six envelopes:
    .config   — model-specific structural data (ConfigBase, extra='forbid')
    .metadata — system-managed (MetadataBase: history, health, flags, audit)
    .prefs    — user-managed (RecordPrefsBase: userdefined, tags, pinned)
    .refs     — relationship cache (RefsBase: links, source)
    .comments — structured notes (CommentsBase: public, process, partner, notes[])
    .actions  — next-action (ActionsBase: required, status, who, when, what, kind)

Usage:
    from common.schemas.payment import PaymentMetadata, PaymentPrefs, PaymentRefs
    from common.schemas.envelopes import CommentsBase, ActionsBase, ConfigBase

    # Validate on save
    meta = PaymentMetadata(**record.metadata)

    # Build from scratch
    meta = PaymentMetadata(gl_accounts=GlStage(event='payment_journalized', posted=True))
    record.metadata = meta.model_dump()

Image schemas:
    from common.schemas.images import ImageSet, ContactImages, OrgImages, ItemImages
"""
