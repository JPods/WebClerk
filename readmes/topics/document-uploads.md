# Document Uploads

## Overview

Unified document upload pattern that:
1. **Uploads file** to storage (local/S3)
2. **Extracts metadata** - EXIF data, GPS coordinates from images
3. **Creates Document record** with metadata (who, when, path, checksum, address, virus status)
4. **Deduplicates** using SHA-256 checksum (same file = same Document)
5. **Returns RefLink** for adding to parent's `refs.links.document[]`

This ensures all uploads are tracked centrally and documents can be moved/organized without breaking references.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Upload Flow                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐   │
│  │ Select  │→ │ Checksum │→ │ Extract  │→ │ Virus    │→ │ Create      │   │
│  │ File    │  │ Dedup    │  │ EXIF/GPS │  │ Scan     │  │ Document    │   │
│  └─────────┘  └──────────┘  └──────────┘  └──────────┘  └─────────────┘   │
│                                                                      │      │
│                                                              ┌───────▼────┐ │
│                                                              │ Add RefLink│ │
│                                                              │ to Parent  │ │
│                                                              └────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Document Model

The Django `Document` model stores:

| Field | Description |
|-------|-------------|
| `name` | Display name |
| `mime_type` | File MIME type |
| `size_bytes` | File size |
| `path` | JSON: `{storage, full, original_name}` |
| `checksum` | SHA-256 hash for integrity/dedup |
| `model_name` | Parent model type |
| `metadata` | Extended metadata (see below) |

## Document Metadata Structure

Each Document has a rich `metadata` JSON field:

```python
metadata = {
    # Standard history tracking
    "history": {
        "created": {"dt": 1770340141833, "contact_id": 41},
        "modified": {"dt": 1770340141833, "contact_id": 41},
        "accessed": {"dt": 0, "contact_id": 0},
        "verified": {"dt": 0, "contact_id": 0},
        "synced": {"dt": 0, "contact_id": 0},
    },
    
    # Health metrics
    "health": {
        "rating": 0,
        "completeness": 0,
        "accuracy": 0,
        "freshness": 0,
        "consistency": 0,
    },
    
    # Physical address / geolocation provenance
    "address": {
        "street": "",
        "street2": "",
        "city": "",
        "state": "",
        "postal_code": "",
        "country": "",
        "geo": {
            "lat": 30.2672,    # latitude
            "lng": -97.7431,   # longitude  
            "altitude": None,   # meters above sea level
            "accuracy": 10.0,   # GPS accuracy in meters
        },
        "source": "exif",  # "exif" | "manual" | "gps" | "ip_lookup" | "browser"
        "captured_at": 1770340141833,
    },
    
    # Virus/malware scan status
    "virus": {
        "status": "clean",      # "pending" | "scanning" | "clean" | "infected" | "error" | "skipped"
        "scanner": "clamav",
        "scanner_version": "1.0.0",
        "scanned_at": 1770340141833,
        "threat": None,         # threat name if infected
        "quarantined": False,
        "details": {},
    },
    
    # EXIF metadata from images
    "exif": {
        "camera_make": "Apple",
        "camera_model": "iPhone 15 Pro",
        "lens": "iPhone 15 Pro back triple camera",
        "focal_length": 6.86,
        "aperture": 1.78,
        "shutter_speed": "1/120",
        "iso": 100,
        "flash": False,
        "orientation": 1,
        "width": 4032,
        "height": 3024,
        "datetime_original": 1770340141833,
        "datetime_digitized": 1770340141833,
        "software": "iOS 17.0",
        "copyright": "",
        "raw": {},  # full raw EXIF data
    },
}
```

## RefLink Storage

Documents are referenced via `refs.links.document[]` on parent entities:

```typescript
refs: {
  links: {
    document: [
      { 
        id: 123,                    // Document record ID
        display: "spec_sheet.pdf",  // Display name
        type: "pdf",                // File type category
        purpose: "qa_image"         // Context/category
      }
    ]
  }
}
```

## React Usage

### Basic Upload

```typescript
import { uploadDocument } from '@/apps/common/components/panels';

const result = await uploadDocument({
  file: selectedFile,
  parentType: 'order',
  parentId: 123,
  purpose: 'spec_sheet',
  description: 'Product specifications',
});

// result.document = full Document record
// result.refLink = ready for refs.links.document[]
// result.url = direct file URL
```

### Upload with Browser Geolocation

```typescript
import { uploadDocumentWithLocation } from '@/apps/common/components/panels';

// Automatically captures browser geolocation
const result = await uploadDocumentWithLocation({
  file: photoFile,
  parentType: 'delivery_visit',
  parentId: 456,
  purpose: 'delivery_photo',
});
```

### Upload with Manual Address

```typescript
const result = await uploadDocument({
  file: docFile,
  parentType: 'project',
  parentId: 789,
  purpose: 'site_photo',
  address: {
    street: '123 Main St',
    city: 'Austin',
    state: 'TX',
    postal_code: '78701',
    country: 'US',
  },
  geolocation: {
    lat: 30.2672,
    lng: -97.7431,
    accuracy: 10,
  },
});
```

### Using DocumentsPanel

```tsx
import { DocumentsPanel } from '@/apps/common/components/panels';

<DocumentsPanel
  parentType="order"
  parentId={orderId}
  data={salesOrder.refs?.links?.document || []}
  onChange={(docs) => updateRefs({ links: { document: docs } })}
  purpose="order_attachment"
  maxFileSize={10 * 1024 * 1024}  // 10MB
  allowedExtensions={['pdf', 'jpg', 'png', 'docx']}
/>
```

### Using the Hook

```typescript
import { useDocumentUpload } from '@/apps/common/components/panels';

const { 
  upload, 
  uploadMultiple, 
  isUploading, 
  progress, 
  error 
} = useDocumentUpload({
  parentType: 'order',
  parentId: orderId,
  purpose: 'attachment',
  maxSizeBytes: 10 * 1024 * 1024,
  allowedExtensions: ['pdf', 'jpg', 'png'],
  onSuccess: (result) => addDocumentRef(result.refLink),
  onError: (err) => toast.error(err.message),
});

await upload(file);
```

## API Endpoints

### Upload File

```http
POST /wcapi/upload/
Content-Type: multipart/form-data

file: <binary>
model_name: order
parent_id: 123
purpose: attachment

# Optional address fields
address_street: 123 Main St
address_city: Austin
address_state: TX
address_postal_code: 78701
address_country: US

# Optional geolocation (from browser)
geo_lat: 30.2672
geo_lng: -97.7431
geo_accuracy: 10
```

Response:
```json
{
  "document_id": 11,
  "path": "uploads/document/2026/02/abc123_photo.jpg",
  "checksum": "d90ef1651fd9e7563e1a1450a16bd784...",
  "is_duplicate": false,
  "url": "/static/uploads/document/2026/02/abc123_photo.jpg",
  "name": "photo.jpg",
  "size_bytes": 1048576,
  "mime_type": "image/jpeg",
  "has_exif": true,
  "has_geo": true,
  "virus_status": "pending"
}
```

### Get Document Info

```http
GET /wcapi/document/{document_id}/
```

### Delete Document

```http
DELETE /wcapi/document/{document_id}/delete/
```

## Checksum Deduplication

When uploading a file, the backend:
1. Computes SHA-256 checksum
2. Checks for existing Document with same checksum
3. If found, returns existing Document (no duplicate storage)
4. If new, saves file and creates Document record

This means the same file uploaded multiple times or to different parent entities shares a single storage path and Document record.

## Virus Scanning

The backend supports pluggable virus scanning:

```python
# settings.py
VIRUS_SCAN_ENABLED = True
VIRUS_SCANNER = 'clamav'  # or 'virustotal'
```

Scan statuses:
- `pending` - Not yet scanned
- `scanning` - Scan in progress
- `clean` - No threats found
- `infected` - Threat detected (file quarantined)
- `error` - Scan failed
- `skipped` - Scanning disabled

## EXIF Extraction

For image uploads, the backend automatically extracts:
- Camera make/model
- Lens information
- Exposure settings (aperture, shutter, ISO)
- GPS coordinates (→ stored in `metadata.address.geo`)
- Image dimensions
- Original capture date/time

## Purpose Categories

| Purpose | Context |
|---------|---------|
| `attachment` | General file attachment |
| `qa_image` | Q&A answer photo |
| `spec_sheet` | Product specifications |
| `proof` | Design proof/mockup |
| `invoice` | Invoice document |
| `po` | Purchase order |
| `receipt` | Payment receipt |
| `shipping_label` | Shipping label |
| `delivery_photo` | Delivery confirmation photo |
| `site_photo` | Site/location photo |
| `artwork` | Design artwork |

## TypeScript Types

```typescript
import type { 
  DocumentRecord,
  DocumentMetadata,
  DocumentAddress,
  VirusScanResult,
  ExifData,
  GeoLocation,
  UploadDocumentOptions,
  UploadDocumentResult,
} from '@/apps/common/components/panels';
```

## Benefits

1. **Audit Trail** - All uploads logged with who, when, where
2. **Deduplication** - Checksum prevents duplicate storage
3. **Location Tracking** - EXIF GPS + browser geolocation
4. **Security** - Virus scanning integration
5. **Library Consolidation** - Move/organize without breaking refs
6. **Metadata Extraction** - Automatic EXIF data from images

## Related

- [refs.md](refs.md) - RefLink storage pattern
- Backend: `webClerk3/apps/docs/views_upload.py`
- Model: `webClerk3/apps/docs/models/document.py`
- Mixin: `webClerk3/common/models.py` → `default_document_metadata()`

## Testing

### Unit Tests

Run all document upload unit tests (no database required):

```bash
cd webClerk3
source bin/activate
pytest tests/test_document_upload.py -k 'not API' -v
```

Test coverage:
- `TestComputeChecksum` - SHA-256 checksum computation and deduplication
- `TestGetUploadPath` - Upload path generation and filename sanitization
- `TestParseExifDatetime` - EXIF datetime string parsing
- `TestConvertGpsCoords` - GPS coordinate conversion (N/S/E/W → decimal)
- `TestExtractExifData` - EXIF metadata extraction from images
- `TestScanForViruses` - Virus scanning placeholder
- `TestDefaultDocumentMetadata` - Metadata structure validation

### Manual EXIF Testing

Test EXIF extraction directly:

```python
# In Django shell
from apps.docs.views_upload import extract_exif_data

with open('/path/to/photo_with_gps.jpg', 'rb') as f:
    result = extract_exif_data(f)
    print(result)

# Expected output:
# {
#   'exif': {'camera_make': 'Apple', 'camera_model': 'iPhone 15', 'width': 4032, ...},
#   'geo': {'lat': 30.2672, 'lng': -97.7431, 'altitude': 182.5}
# }
```

### API Integration Test

```python
import requests
import json

# Get auth token
token_resp = requests.post('http://localhost:8001/wcapi/token/', 
    json={'email': 'test@example.com', 'password': 'password123'})
token = token_resp.json()['data']['access']

# Upload with geolocation
with open('/path/to/test.jpg', 'rb') as f:
    resp = requests.post('http://localhost:8001/wcapi/upload/',
        headers={'Authorization': f'Bearer {token}'},
        files={'file': ('test.jpg', f)},
        data={
            'purpose': 'document',
            'model_name': 'test',
            'geo_lat': '30.2672',
            'geo_lng': '-97.7431',
            'geo_accuracy': '10',
            'address_city': 'Austin',
            'address_state': 'TX',
        })

print(json.dumps(resp.json(), indent=2))
```

### Sample Image with GPS

Download a test image with EXIF GPS data:

```bash
curl -o /tmp/test_gps.jpg \
  "https://raw.githubusercontent.com/ianare/exif-samples/master/jpg/gps/DSCN0010.jpg"
```

Then upload to verify GPS extraction:

```python
from apps.docs.views_upload import extract_exif_data

with open('/tmp/test_gps.jpg', 'rb') as f:
    result = extract_exif_data(f)
    if result['geo']:
        print(f"GPS: {result['geo']['lat']}, {result['geo']['lng']}")
    else:
        print("No GPS data found")
```
