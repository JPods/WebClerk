# Alice — File Storage Enforcement

## What Alice Watches

Every file upload, image save, and document attachment passes through Alice.
She enforces the file storage protocol defined in
`readmes/topics/architecture/file-storage-protocol.md`.

## Rules Alice Enforces

### 1. Path Structure
Every file must follow: `/media/<org_id>/<model>/<record_id>/<filename>`

If a file is saved outside this structure, Alice:
- Moves it to the correct path
- Updates the record's metadata.images with the new path
- Logs the correction

### 2. Image Sizes
On every image upload, Alice ensures all sizes are generated:
- tn (64px) — lists, badges, gantt assignee
- sm (128px) — contact card, chat avatar
- md (256px) — profile page, directory
- lg (512px) — detail page hero
- original — user download, print

Missing sizes are generated on demand. Alice tracks which sizes are
actually accessed and can skip pre-generation for rarely-viewed records.

### 3. Metadata Sync
After file operations, Alice verifies:
- `record.metadata.images` paths match actual files on disk
- Orphaned files (on disk but not in metadata) are flagged
- Dead references (in metadata but not on disk) are cleaned

### 4. Tenant Isolation
Alice never serves a file from org A to a user in org B.
The path structure enforces this — but Alice validates it at the
application layer as a defense-in-depth check.

### 5. Size Limits
Images over 10MB are rejected at upload.
Documents over the inline threshold (64KB) are stored as files,
not in JSON fields. (See alice-field-size-discipline.md)

## Algorithm: On Upload

```
1. Validate file type and size
2. Determine org_id, model, record_id from context
3. Build target path: /media/{org_id}/{model}/{record_id}/
4. For images:
   a. Save original as {purpose}_original.{ext}
   b. Generate sizes: 512, 256, 128, 64 via Pillow
   c. Save as {purpose}_{size}.{ext}
   d. Build ImageSet with all paths
   e. Update record.metadata.images.{purpose} = ImageSet
5. For documents:
   a. Save with original filename
   b. Create/update Document record with path
   c. Link to parent record via refs.links.document
6. Log the operation for audit
```

## Algorithm: Nightly Cleanup

```
1. Walk /media/{org_id}/ directories
2. For each file, check if metadata.images references it
3. Orphaned files → log warning, do not delete (admin decides)
4. Dead references → clear from metadata.images
5. Missing sizes → generate on demand if record was accessed recently
```

## Vector Store Entry

This document should be indexed into Alice's vector store.
Key concepts for retrieval:
- file upload path structure
- image resize pipeline
- metadata.images sync
- tenant file isolation
- orphan detection
- size generation on demand
