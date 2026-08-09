# WC3 File Storage Policy

## Purpose

Define where user-uploaded files live, how they're named, what the database knows about them, and the boundary between local files and library URLs.

This policy applies to all WC3 installations. Alice enforces it at upload time. Violations are flagged, not blocked — commerce must flow.

## The WC2 Pattern (what worked)

WC2 stored files in `jitweb/` with a model-based folder structure:

```
jitweb/
  customer/<ida>/logo.png
  item/<class_or_vendor>/<ida>/tn.png
  item/<class_or_vendor>/<ida>/detail.png
  item/<class_or_vendor>/<ida>/spec.pdf
  order/<ida>/signed-po.pdf
  invoice/<ida>/packing-slip.pdf
```

The key property: **given a model + ida, you knew where files lived without querying a database.** WC3 preserves this.

## WC3 File Storage Structure

```
media/
  <model_name>/
    <ida>/
      <role>.<ext>          # known roles get standard names
      <original_name>.<ext> # attachments keep their upload name
      archive/              # replaced files moved here (not deleted)
```

### Examples

```
media/item/WIDGET-100/tn.png
media/item/WIDGET-100/detail.png
media/item/WIDGET-100/spec.pdf
media/customer/ACME-CORP/logo.png
media/customer/ACME-CORP/credit-app.pdf
media/order/SO-2026-0042/signed-po.pdf
media/invoice/IV-2026-0108/packing-slip.pdf
media/contact/bill-james/avatar.png
media/flowchart/wc3-master-flow/source.dot
media/flowchart/wc3-master-flow/rendered.pdf
```

### Rules

| Rule | Enforcement |
|------|-------------|
| Files live under `media/<model>/<ida>/` | wcapi creates folder on upload, rejects paths outside it |
| Known roles get standard names (`tn.png`, `detail.png`) | Upload endpoint renames to `<role>.<ext>` |
| Unknown files keep original name | `role='attachment'`, filename preserved |
| File extensions must match allowed list per role | Pydantic validates before write |
| Max file size per role | Checked before write |
| One file per role (latest wins) | Upload replaces, moves old to `<ida>/archive/` |
| Every file has a Document record | Upload endpoint creates/updates Document |
| Path is derivable from record | `media/{model_name}/{ida}/{role}.{ext}` — no query needed |

### User responsibility (not enforced by WC3)

- Users who FTP files directly into folders bypass all validation
- Django admin and psql bypass the schema
- File content quality (is the "spec.pdf" actually a spec?) is the user's job

## Default File Roles per Model

| Model | Role | Label | Allowed Extensions | Max Size | Required |
|-------|------|-------|--------------------|----------|----------|
| **item** | tn | Thumbnail | png, jpg, webp | 2 MB | No |
| | detail | Detail Image | png, jpg, webp | 10 MB | No |
| | spec | Specification | pdf | 25 MB | No |
| | msds | Safety Data Sheet | pdf | 10 MB | No |
| **customer** | logo | Company Logo | png, jpg, svg | 2 MB | No |
| | contract | Contract | pdf | 25 MB | No |
| **order** | signed | Signed Document | pdf | 25 MB | No |
| | attachment | Attachment | any | 25 MB | No |
| **invoice** | packing | Packing Slip | pdf | 10 MB | No |
| | attachment | Attachment | any | 25 MB | No |
| **contact** | avatar | Profile Photo | png, jpg | 2 MB | No |
| **connection** | credential | Credentials | pdf | 5 MB | No |
| **flowchart** | source | DOT Source | dot | 1 MB | No |
| | rendered | Rendered PDF | pdf | 5 MB | No |
| *(any model)* | attachment | Attachment | any | 25 MB | No |

Roles are defined in Setting records (`name='file_config'`, `parent_model='<model>'`). Users can add roles. Alice flags roles with no files after 30 days.

## Library URLs vs. Local Files

**Policy: drive local file paths to library URLs wherever possible.**

A fireplace installer in Tulsa does not need the hi-res product image and 40-page spec PDF for every fireplace in the catalog stored on their local machine. They need access when they need it — not permanent local copies of files they'll open twice a year.

### How this works

1. **Library** — WC_HQ (or manufacturer, or distributor) hosts product media at stable URLs. These are the source of truth for product images, specs, MSDS sheets, and catalog content.

2. **Local pointer** — The WC3 item record stores a `library_url` in its Document config, not the file itself. The URL points to the library. When the user needs the file, they fetch it. When they're online, it loads seamlessly.

3. **Local cache** — Files the user actually opens get cached locally in `media/item/<ida>/`. The cache has a size budget. Least-recently-used files are evicted. The Document record tracks `cached_dt` and `cache_size`.

4. **Offline subset** — For off-internet operation (job sites, trade shows, travel), the user marks specific items or categories for offline access. Alice downloads those files before departure. Everything else stays as library URLs.

5. **What's always local** — Files the user created (photos from a job site, signed contracts, custom quotes). These are never library URLs — they originated here.

### The boundary

| File Type | Where it lives | Why |
|-----------|---------------|-----|
| Product thumbnail | Library URL | Manufacturer provides; 50,000 items × 100KB = 5GB nobody needs locally |
| Product spec PDF | Library URL | Fetch on demand; cache if opened |
| Product hi-res image | Library URL | Only needed for catalogs and presentations |
| Customer logo | Local → archive | Customer provided it; small, keep local |
| Signed PO | Local | You created it; legal record |
| Job site photo | Local → archive hosting | High volume, low reuse after project closes |
| MSDS | Library URL + offline flag | Required at job site; Alice downloads for marked jobs |
| Flowchart | Local | Training material; small files |

### Job site photos and customer files

Installers take photos as work progresses — before, during, after. These go into `media/customer/<ida>/` immediately. They're critical during the active project. After the project closes, they become reference material that might get opened once in five years for a warranty claim.

**Policy: Alice moves completed project photos to low-cost archive hosting when practical.**

The lifecycle:

1. **Active project** — photos live locally at `media/customer/<ida>/`. Instant access. This is work-in-progress.
2. **Project closes** — Alice identifies photos older than the project close date. She uploads them to archive hosting (S3, Backblaze B2, or equivalent low-cost object storage).
3. **Document record updated** — `path` cleared, `archive_url` set, `source` changed to `'archived'`. The Document record stays in the database. The photo stays findable.
4. **On demand** — if someone opens an archived photo (warranty claim, dispute, reference), Alice fetches it from archive hosting. Fast enough for occasional use. Not fast enough for daily work — which is fine, because daily work is over.
5. **Never deleted** — archived photos are never deleted. Storage cost for photos at archive rates (~$0.005/GB/month) is negligible. A 5-year project history of 10,000 photos at 3MB each = 30GB = $0.15/month.

**What triggers archival:**
- Project status changes to `closed` or `complete`
- Photos older than 90 days with no access
- Alice runs archival sweep nightly (or on schedule)
- User can force-archive from the Document record

**What stays local:**
- Photos for active/open projects — always
- Photos the user has flagged for offline access
- The most recent photo per customer (for recognition/context)

### Job photos as marketing

A completed fireplace installation is a marketing asset. The customer shows friends. Friends become leads. The archive URL should be **shareable** — not buried behind a login.

**Policy: completed project photos get a public-readable archive URL.**

Alice generates a shareable link per project (or per photo). The customer can text it, post it, email it. No login required. The link points to archive hosting, not the installer's WC3 server — so sharing doesn't consume the installer's bandwidth or expose their system.

The Document record tracks `share_url` (public) separately from `archive_url` (internal). Share URLs can be revoked. Alice tracks click counts on shared links — that's ad source data. A photo that generates 3 leads is worth knowing about.

```
Document.config:
  share_url: "https://photos.wc.com/p/abc123"   # public, no login
  share_enabled: true                             # revocable
  share_clicks: 14                                # Alice tracks
  share_leads: 2                                  # leads attributed to this share
```

This connects directly to the Ad Source tracking flowchart — the photo IS the ad source. Cost: zero. ROI: measurable. Alice closes the loop from shared photo → lead → customer → revenue.

### Progress reports — print + web

When the installer prints a progress report (from the Report output pipeline), a web version is generated simultaneously. The printed report is a summary — the web version is the full story.

```
Printed report:         4 photos, summary text, next steps
Web version:            All photos, videos, detailed notes, timeline, before/after
```

The web version lives at a shareable URL tied to the project. The customer gets the printed report AND a link to the full web gallery. They forward the link to friends. Friends see professional work documentation — not a text message with a phone photo.

**What the web progress report contains:**
- All project photos in timeline order (before → during → after)
- Videos (walkthrough, operation demo)
- Detailed notes per phase
- Materials used (links to product specs via library URLs)
- Next steps / schedule
- Installer's contact info and company branding

**What this replaces:**
- Texting individual photos to the customer
- "I'll email you the photos" (never happens)
- Customer taking their own bad photos to show friends

**Alice's role:**
- Auto-generates the web gallery when a progress report is printed
- Pulls photos from `media/customer/<ida>/` and videos from the same path
- Applies the installer's branding (logo, colors from company Setting)
- Generates the shareable URL
- Tracks views and shares as ad source data

The gallery URL stays live after the project closes because the photos move to archive hosting, not local storage. The installer's server is not involved in serving the gallery to the customer's friends — archive hosting handles it.

```
Document.config (progress report):
  report_type: "progress"
  print_path: "media/customer/ACME-CORP/reports/progress-2026-08-08.pdf"
  gallery_url: "https://photos.wc.com/g/project-abc123"
  gallery_enabled: true
  gallery_views: 47
  gallery_shares: 8
  gallery_leads: 3
```

### QA photos and video — compliance + relationship texture

QA inspections generate photos and video. These serve two purposes that can't be separated:

1. **Compliance** — proof that required steps were performed. Gas line pressure test photo. Clearance measurement photo. Final inspection video. These are the evidence that the work met spec. Without them, QA answers are just checkboxes.

2. **Relationship texture** — the anecdotal record of the job. The customer sees the installer taking photos at each step and knows the work is being documented. The QA gallery becomes part of the progress report. It shows care, not just compliance.

QA photos and video are stored the same way as job site photos:

```
media/customer/<ida>/qa/
  <qa_id>/
    step-01-gas-test.jpg
    step-02-clearance.jpg
    step-03-final-walkthrough.mp4
```

Each QA record (in the `qas` table) references its media via Document records. The Document config carries the same `archive_url` / `share_url` / `gallery_url` fields. When the project closes, QA media archives with everything else — but the QA answers and their photo references remain queryable in the database.

**For Gordy-style quality manuals** (ISO 9001, nuclear discipline): the QA photos are the objective evidence. The QAQuestion defines what photo is required. The QA answer without the photo is incomplete. Alice flags QA records where a required photo role has no file.

```
QAQuestion.config:
  required_media: ["photo_before", "photo_after", "video_walkthrough"]

QA.config (answer):
  media:
    - role: "photo_before"
      document_id: 4521
    - role: "photo_after"
      document_id: 4522
    - role: "video_walkthrough"
      document_id: null        # ← Alice flags this: required but missing
```

```
Document.config:
  path: ""                                              # cleared after archive
  archive_url: "https://b2.example.com/wc3/customer/ACME-CORP/job-2026-03/img_0042.jpg"
  source: "archived"                                    # was "uploaded", now "archived"
  archived_dt: "2026-08-15T03:00:00Z"                   # when Alice moved it
  archived_from: "media/customer/ACME-CORP/img_0042.jpg" # where it was
```

### Document record fields for library vs. local vs. archived

```
Document.config:
  path: "media/item/WIDGET-100/spec.pdf"    # local path (blank if not local)
  library_url: "https://library.wchq.com/mfr/acme/WIDGET-100/spec.pdf"
  archive_url: ""                            # set when Alice moves to archive hosting
  is_cached: true                            # file exists locally right now
  cached_dt: "2026-08-01T14:00:00Z"          # when last fetched/cached
  cache_size: 2458000                        # bytes
  offline_flag: false                        # user wants this for offline
  source: "library"                          # library | uploaded | archived
  archived_dt: ""                            # when Alice archived it
  archived_from: ""                          # original local path before archival
```

Three states a file can be in:

| Source | path | library_url | archive_url | Meaning |
|--------|------|-------------|-------------|---------|
| `uploaded` | set | blank | blank | User uploaded, lives locally |
| `library` | blank or cached | set | blank | Manufacturer/HQ provides, fetch on demand |
| `archived` | blank | blank | set | Was local, Alice moved to cheap storage |

### Alice's role

- **On sync:** Alice receives library URLs from upstream connections. She stores them on Document records, does NOT download files.
- **On demand:** When user opens a library file, Alice fetches it, caches locally, updates Document.
- **Offline prep:** Before offline mode, Alice downloads all `offline_flag=true` files.
- **Cache management:** Alice evicts cached files older than 90 days that haven't been opened, respecting a configurable size budget.
- **Missing file alerts:** If a local file referenced by a Document doesn't exist on disk, Alice flags it (don't silently fail).

## Pydantic Schemas

Defined in `common/schemas/document.py`:

- `FileRole` — one expected file type for a model (name, label, allowed_ext, max_size_mb)
- `ModelFileConfig` — Setting per model (base_path, folder_pattern, roles[], archive policy)
- `DocumentFileRef` — stored in Document.config (path, library_url, role, hash, upload info, cache state)

## For Alice: User Instructions

When a user asks about file storage, uploading, or where files go:

1. Files are stored under `media/<model>/<ida>/` — always.
2. Known file types (thumbnail, spec, logo) get standard names. Other files keep their upload name.
3. Product images and specs from manufacturers should be library URLs, not local files. The library serves them on demand.
4. To mark files for offline access, set `offline_flag` on the Document record. Alice will download before you go offline.
5. Old files aren't deleted — they're moved to `archive/` under the same ida folder.
6. Every uploaded file gets a Document record. If you can't find a file, search Documents first.
7. If a file should be a library URL but is stored locally, tell Alice — she'll convert it.

## WC2 Upload Pattern (design basis for R25)

WC2 vue2020 + 4D handled phone photo uploads simply and well. This is the pattern to preserve.

**Frontend (vue2020 `QAForm.vue`):**
```html
<input type="file" @change="onFileChange" />
```
- Standard `<input type="file">` — on phones, this opens the camera
- `FileReader.readAsDataURL()` converts to base64
- POSTs JSON: `{ id, answer, idQAAnswer, photo: base64string }`
- After submit, auto-advances to the next QA question

**Backend (4D `WCapi_QASave.4dm`):**
- Receives base64 photo in the JSON payload
- Builds path from record context: `customer/<customerID>/numTask<taskNum>/`
- Builds filename: `QA-<question>-<answer>-<timestamp>`
- `imgBase64()` decodes and saves full image + thumbnail to disk
- Stores `imagePath` and `imagePathTn` on the QA record
- Returns web-accessible URLs in the response

**What was good (preserve in R25):**
- Simple — one file input, one POST, one save
- Phone-friendly — `<input type="file">` opens camera on mobile
- Auto-advance through QA questions — installer answers, takes photo, next
- Thumbnails generated server-side automatically
- Predictable folder structure: server builds the path, client doesn't decide
- The installer never thinks about file management

**What to change for R25:**
- Base64 in JSON → `multipart/form-data` (base64 doubles the file size over the wire)
- Path stored on QA record → Document record with `DocumentFileRef` in config
- Local-only storage → archive hosting after project close
- Add video support (same `<input type="file" accept="image/*,video/*">`)
- Document record tracks the file, not just a string field on QA

**Source files (reference):**
- `vue2020/src/components/QAForm.vue` — frontend QA with photo upload
- `webclerk2/ComEx19ak/Project/Sources/Methods/WCapi_QASave.4dm` — backend photo handling
- `webclerk2/ComEx19ak/Project/Sources/Methods/WC_Core.4dm` — request routing

## Related

- `common/schemas/document.py` — Pydantic schemas
- `readmes/topics/architecture/data-library-ecosystem.md` — WC_HQ library model
- `readmes/topics/sync/` — how library URLs arrive via Connection bundles
- `readmes/21-sync-integration.md` — Connection + Bundle architecture
