# Collaborate_WebClerk — Template Submission, Review, and Library

**Setting record:** #444, purpose=`collaborate_webclerk`
**Created:** 2026-07-17

---

## What This Is

A sovereignty-preserving collaboration system between local WC3 instances and
WebClerk HQ (WCHQ). Users submit forms and templates for review. Alice_WCHQ +
human reviewers evaluate. Innovative layouts get promoted to the generally
available library. All participation is opt-in, per-category, and revocable.

This is not SaaS — it is the Desktop Hosting model applied to best practices.
WCHQ is a library service, not a controller.

---

## The Three Flows

### Flow 1: Receiving Recommendations (WCHQ → Local)

```
Alice_WCHQ maintains library of best practices
    ↓
Collaborate_WebClerk Setting checked:
    Is this category enabled for this instance?
    ↓ yes
WCHQ creates sync Pending record with recommendation
    ↓ delivered via sync app
Alice_local receives Pending record
    ↓ creates Action for admin review
Admin reviews recommendation in DataBrowser
    ↓ accepts or rejects
If accepted → applied to local instance
If rejected → logged, WCHQ learns what this instance doesn't want
```

**Categories (14):**

| Category | What WCHQ Provides |
|----------|-------------------|
| `print_forms` | Invoice, proposal, PO, packing slip, pick list, BOL, statement templates |
| `payment_portal` | Stripe checkout config, webhook setup, PCI compliance guidance |
| `shipping_portal` | UPS/FedEx/DHL/USPS API configs, rate shopping, label generation |
| `databrowser_layouts` | Community DataBrowser column layouts for all models |
| `email_templates` | Transactional email templates (order confirmation, invoice, payment) |
| `saved_searches` | Pre-built search filters and keyword configurations |
| `alice_coaching` | Training tips, field help text, onboarding sequences, quiz questions |
| `inventory_practices` | Reorder points, ABC classification, cycle count schedules |
| `commission_management` | Commission calc templates, split patterns, broker reports |
| `tax_compliance` | Tax rate updates, nexus rules, 1099 templates |
| `security_hardening` | RBAC role templates, rate limiting, audit policies |
| `workflow_automation` | Document conversion chains, approval workflows, notification triggers |
| `gl_accounting` | Chart of accounts, GL posting rules, period close checklists |
| `report_definitions` | Canned reports for sales, AR aging, inventory, operations |

Each category is independently toggleable. Admin reviews quarterly.

---

### Flow 2: Submitting Templates for Review (Local → WCHQ)

```
User designs template in PDF Designer (/pdf-designer)
    ↓
Clicks "Submit for Review" button
    ↓
Dialog shows:
  - Template name and document type
  - "Business data is stripped — only the layout is shared"
  - Optional notes for reviewers
  - Confirm button
    ↓
System creates Document record:
  - ida: TMPL-SUBMIT-{timestamp}
  - status: "submitted"
  - config.submission_type: "template_review"
  - config.template_json: the pdfme template (layout only)
  - config.review_status: "submitted"
  - refs.keywords.type: "template_submission"
    ↓
Sync pushes Document to WCHQ
    ↓
Alice_WCHQ receives and validates:
  - Valid pdfme JSON? ✓
  - No PII or business data in template? ✓
  - Renders correctly? ✓
  - Queues for human review
    ↓
Human reviewer evaluates:
  - Layout quality and professionalism
  - Innovation (does it solve a problem others have?)
  - Completeness (all expected fields present?)
  - Writes feedback
    ↓
WCHQ posts feedback as sync Pending record back to submitter
    ↓
Alice_local receives feedback:
  - Creates Action: "Feedback ready on your invoice template"
  - User can view reviewer comments
    ↓
config.review_status updated through lifecycle:
  submitted → under_review → feedback_ready → accepted_to_library | declined
```

**Review Status Lifecycle:**

| Status | Meaning |
|--------|---------|
| `submitted` | User posted, waiting for WCHQ pickup |
| `under_review` | Alice_WCHQ validated, human reviewer assigned |
| `feedback_ready` | Reviewer posted comments, user can read |
| `accepted_to_library` | Promoted to generally available library |
| `declined` | Not suitable for library (feedback explains why) |

---

### Flow 3: Library Distribution (WCHQ → All Instances)

```
Template accepted_to_library
    ↓
WCHQ adds to curated library:
  - Assigns library ID
  - Tags by document type + use case
  - Credits original submitter
    ↓
All instances with that category enabled:
  - Alice_local notifies: "New invoice template available in library"
  - User can browse library
  - Preview before install (always — never auto-installed)
    ↓
User installs → creates local Report record with pdfme_template
    ↓
WCHQ tracks adoption (anonymized) to measure template quality
```

**Submitter credit:** tracked in `contact.config.library_credits`. Credits
accumulate per accepted submission. Future: credits can be used for premium
support time or WCHQ services.

---

## Setting Record Structure

```json
{
  "enabled": true,
  "auto_accept": false,

  "categories": {
    "print_forms": {
      "enabled": true,
      "label": "Print Form Templates",
      "description": "...",
      "last_sync_utc": "",
      "pending_count": 0,
      "accepted_count": 0,
      "rejected_count": 0
    }
    // ... 13 more categories
  },

  "submissions": {
    "enabled": true,
    "submit_for_review": true,
    "submit_to_library": true,
    "anonymize_business_data": true,
    "require_approval": true,
    "notification_on_feedback": true,
    "categories_submittable": [
      "print_forms", "email_templates", "databrowser_layouts",
      "workflow_automation", "report_definitions", "alice_coaching"
    ]
  },

  "library": {
    "browse_enabled": true,
    "auto_notify_new": true,
    "preview_before_install": true,
    "track_adoption": true,
    "last_browse_utc": ""
  },

  "delivery": {
    "via": "sync_app_record",
    "sync_model": "pending",
    "review_action": true,
    "notification": "alice"
  },

  "contribute": {
    "enabled": false,
    "share_custom_templates": false,
    "share_workflow_recipes": false,
    "share_alice_tips": false,
    "anonymize": true,
    "require_approval": true
  },

  "admin_review": {
    "frequency": "quarterly",
    "next_review_utc": "",
    "last_reviewed_utc": "",
    "reviewed_by_contact_id": null,
    "dt_approved": "",
    "approval_note": ""
  }
}
```

---

## Alice on IT15 — Production Requirements

### What Alice Needs on GEEKOM IT15

| Component | Purpose | Status |
|-----------|---------|--------|
| **ChromaDB** (:8100) | Vector store for RAG retrieval | In deployment plan (Step 9) |
| **Ollama** (:11434) | Local LLM for Alice inference | Needs adding to deployment plan |
| **Model: deepseek-r1:8b** | Alice's LLM (or successor) | Pull after Ollama install |
| **Celery worker** | Background task processing (sync, submissions) | In deployment plan |
| **Celery beat** | Scheduled tasks (nightly index, sync checks) | In deployment plan |
| **Sync app records** | Connection records to WCHQ | Need seed on first deploy |

### Pre-Deployment Checklist for Alice

```bash
# 1. Ollama — not yet in deployment plan
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull deepseek-r1:8b

# Create systemd service for Ollama
sudo tee /etc/systemd/system/ollama.service << 'EOF'
[Unit]
Description=Ollama LLM Server (Alice)
After=network.target

[Service]
User=DEPLOY_USER
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=5
Environment="OLLAMA_HOST=0.0.0.0:11434"

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama
```

```bash
# 2. ChromaDB — already in deployment plan (Step 9)
# Verify it's running:
curl http://localhost:8100/api/v1/heartbeat
```

```bash
# 3. Index documents into Alice's vector store
cd /var/www/webclerk3
source venv/bin/activate
python manage.py index_docs --reset    # full initial index
python manage.py index_docs --stats    # verify
```

```bash
# 4. Seed the Collaborate_WebClerk setting
python manage.py seed_collaborate_settings
python manage.py seed_wchq_settings
```

```bash
# 5. Seed Alice's coaching data
python manage.py seed_alice_coaching    # if command exists
```

```bash
# 6. Verify Alice can respond
python manage.py ai_health             # checks Ollama + Chroma + settings
```

### Environment Variables (.env on IT15)

```bash
# Alice LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:8b
OLLAMA_TIMEOUT=120

# ChromaDB
CHROMA_PERSIST_DIR=/var/www/chroma/data
CHROMA_COLLECTION=commerce_expert_docs

# Collaboration (WCHQ endpoint — set when WCHQ instance is live)
WCHQ_SYNC_URL=https://wchq.webclerk.com/wcapi/sync/
WCHQ_API_KEY=                    # set at deployment — Alice_local authenticates to WCHQ
```

### Celery Beat Schedule — Alice's Recurring Tasks

| Task | Schedule | What It Does |
|------|----------|-------------|
| `index_docs` | Daily 03:00 UTC | Re-index readmes + code docs into ChromaDB |
| `sync_collaborate` | Daily 03:30 UTC | Check WCHQ for new recommendations in enabled categories |
| `process_submissions` | Every 6 hours | Check for outgoing template submissions, push to WCHQ |
| `alice_nightly_review` | Daily 04:00 UTC | Review pending Actions, generate coaching tips |

These need Celery beat entries in `webclerk3_api/celery.py` or a `django-celery-beat`
schedule record.

### What's Missing from 58-production-deployment.md

1. **Ollama systemd service** — not in the deployment plan yet. Add as Step 10.
2. **Celery beat schedule** for Alice tasks — needs specific task entries
3. **WCHQ sync endpoint** — env var placeholder, set when WCHQ is live
4. **Initial data seeds** — `seed_collaborate_settings`, `seed_wchq_settings`
5. **Alice MCP server** — if Alice serves as MCP tool for Claude Code on IT15

### Data Flow on IT15

```
                        ┌──────────────────┐
                        │  WCHQ (future)   │
                        │  wchq.webclerk.com│
                        └────────┬─────────┘
                                 │ sync (Pending records)
                                 ▼
┌──────────────────────────────────────────────────────┐
│  GEEKOM IT15                                          │
│                                                       │
│  Nginx → Gunicorn → WC3 Django                       │
│           │                                           │
│           ├── wcapi/sync/ ← receives WCHQ sync        │
│           ├── wcapi/save/ ← template submissions       │
│           └── ai_assistant/ ← Alice API endpoints      │
│                                                       │
│  Celery worker ← processes sync, submissions          │
│  Celery beat   ← schedules index, sync, review        │
│                                                       │
│  Ollama (:11434) ← Alice LLM inference                │
│  ChromaDB (:8100) ← RAG vector store                  │
│  PostgreSQL (:5432) ← all data                        │
│  Redis (:6379) ← Celery broker + cache                │
└──────────────────────────────────────────────────────┘
```

---

## Sovereignty Guarantees

| Principle | How It's Enforced |
|-----------|------------------|
| Local instance is sovereign | `auto_accept: false` — nothing applied without admin review |
| Per-category control | Each of 14 categories independently toggleable |
| Submission is voluntary | `submissions.require_approval: true` — user confirms each send |
| Business data never leaves | `anonymize_business_data: true` — templates stripped of transaction data |
| Revocable at any time | Toggle any category off; takes effect immediately |
| Admin reviews periodically | Quarterly review with dated approval signature |
| WCHQ suggests, local decides | All recommendations arrive as Pending records for review |
| Contribution is opt-in | `contribute.enabled: false` by default |

---

## Related Files

| File | What |
|------|------|
| `apps/core/management/commands/seed_collaborate_settings.py` | Seeds Setting #444 |
| `apps/core/management/commands/seed_wchq_settings.py` | Seeds WCHQ connection Setting |
| `React2025/src/pages/tools/PdfDesigner.tsx` | Visual template designer with Submit button |
| `React2025/src/services/pdfme/templateService.ts` | Template load/save from Report model |
| `React2025/src/services/pdfme/fieldRegistry.ts` | Exposes WC3 fields to template system |
| `readmes/topics/print/pdfme-template-system.md` | pdfme template architecture |
| `readmes/58-production-deployment.md` | IT15 deployment plan |
