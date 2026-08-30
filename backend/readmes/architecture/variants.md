# Variant model: configurable attributes and stable identity


<!-- TOC START -->

## Table of Contents

- [Variant model: configurable attributes and stable identity](#variant-model-configurable-attributes-and-stable-identity)
  - [Table of Contents](#table-of-contents)
  - [Design in brief](#design-in-brief)
  - [JSON shapes](#json-shapes)
  - [Item helpers](#item-helpers)
  - [Validation](#validation)
  - [Example](#example)
  - [Notes](#notes)

<!-- TOC END -->

Goal: Provide a lean, migration-free way to model item variants (size/color/etc.) with consistent identity across environments and integrations.

Policy: `id` is the authoritative unique key within a single database. Reserve `uuid` strictly for cross-database or cross-system identity.

## Design in brief

- No new tables. We leverage the universal JSON envelopes on `Item`:
  - `metadata.variants`: schema and family identifier (set_uuid)
  - `refs.variants`: variant relationship and chosen attributes
  - `prefs.variants`: small UX hints
- Deterministic UUIDs using v5:
  - `variant_set_uuid = uuid5(NAMESPACE_URL, f"variant-set:{item.uuid}")`
  - `variant_uuid = uuid5(variant_set_uuid, canonicalize(attrs))`
- Canonical key for attributes: `color=blue|size=m` (keys/values normalized and sorted)

## JSON shapes

- metadata.variants
  - schema: {key: [values]} (optional; used for validation/UX)
  - set_uuid: string UUID for the variant family (derived from parent Item.uuid)
- refs.variants
  - parent_id: DB id of the parent/base item (preferred for local joins)
  - parent_uuid: UUID of the parent/base item (for cross-system sync; optional)
  - attrs: {key: value} chosen for this variant
  - key: canonical string key derived from attrs
- prefs.variants
  - auto_slug: true to auto-compose slug from attrs (optional)

## Item helpers

- set_variant_schema(schema)
- set_variant_attrs(attrs, parent_uuid=None, parent_id=None)
- variant_set_uuid() -> str | None
- variant_canonical_key() -> str
- variant_uuid() -> str | None

## Validation

- If `metadata.variants.schema` is present, we validate `refs.variants.attrs` keys/values against it.

## Example

Parent item (no attrs yet):

- metadata.variants.set_uuid = uuid5(NAMESPACE_URL, f"variant-set:{parent.uuid}")

Child variant (attrs={"color":"Blue","size":"M"}):

- refs.variants.parent_id = parent.id
- refs.variants.parent_uuid = parent.uuid  # optional if used for cross-system
- refs.variants.attrs = {color: "Blue", size: "M"}
- refs.variants.key = "color=blue|size=m"
- variant_uuid() -> uuid5(parent.set_uuid, "color=blue|size=m")

## Notes

- Works across databases/environments: same attrs yield same UUID given the same parent.
- You can still introduce concrete Variant tables later; these helpers provide a stable bridge and immediate utility.
