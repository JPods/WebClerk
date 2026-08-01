"""
Pydantic schemas for JSON envelope fields (.prefs, .metadata, .refs).

Every BaseModel record has these three JSON fields. These schemas define
what goes in each one, per model. Validation on write, documentation by
existence, Alice reads the schemas.

Usage:
    from common.schemas.payment import PaymentMetadata, PaymentPrefs, PaymentRefs

    # Validate on save
    meta = PaymentMetadata(**record.metadata)

    # Build from scratch
    meta = PaymentMetadata(gl_accounts=GlStage(event='payment_journalized', posted=True))
    record.metadata = meta.model_dump()

Image schemas:
    from common.schemas.images import ImageSet, ContactImages, OrgImages, ItemImages
"""
