# Alice Toolkit — Open Source Tools and Capabilities
**Created:** 2026-07-03
**Purpose:** Complete registry of tools available to Alice, Ingrid, and the team. Each tool has a Document record in WC3 (model_name="tool_reference") with version, install command, resources, and license.

---

## Vector Stores

Alice has her own semantic search engine — **3,977 chunks** of WC3 knowledge.

| Store | Chunks | Script | What it indexes |
|-------|--------|--------|----------------|
| **Alice** (`.chroma_db_alice/`) | 3,977 | `alice-vectorstore.py` | WC3 models, views, readmes, legacy PDFs (Desktop Hosting, flow charts), cross-refs from Allie + Claude |
| **Allie** (`.chroma_db/`) | 2,368 | `allie-vectorstore.py` | Knowledge, readmes, thoughts, handoff, facets, wisdom |
| **Claude** (`.chroma_db_claude/`) | 1,178 | `claude-vectorstore.py` | Sessions, retrospections, process inbox, agent docs |

All use ChromaDB with cosine similarity. Python in `~/Allie/venv/`.

---

## MCP Servers

Alice is an MCP server — Claude Code calls her directly.

| Server | Script | Tools |
|--------|--------|-------|
| **alice** | `alice-mcp-server.py` | `ask_alice`, `alice_search`, `alice_observe`, `alice_recall`, `alice_quiz` |
| **allie** | `allie-mcp-server.py` | `ask_allie`, `teach_allie`, `allie_recall`, `allie_flag` |
| **allie-db** | `allie_db_mcp.py` | SQL queries, memory, messages, observations |
| **commerce-db** | `commerce_db_mcp.py` | WC3 database queries |
| **webclerk** | `wc_mcp_server.py` | Search, get contact/invoice/item, add notes |
| **chrome-devtools** | `npx chrome-devtools-mcp` | Browser inspection, screenshots, network, console |

---

## Quiz Engine

Alice generates learning quizzes from WC3 knowledge. Questions are stored as Document records (`model_name="quiz"`) and served via the `alice_quiz` MCP tool.

### Quiz Sets (Document IDA)

| IDA | Topic | Questions | Source |
|-----|-------|-----------|--------|
| `QUIZ-INVENTORY-FLOW` | Inventory bucket flow | 7 | test_inventory_bucket_flow.py, inventory_flow_testing.md |
| `QUIZ-PAYMENT-CASH` | Payment and cash flow | 7 | test_payment_services.py, test_ledger.py |
| `QUIZ-GL-POSTING` | GL posting and journals | 4 | test_gl_posting.py, test_dollars_by_account_code.py |
| `QUIZ-COMMERCE-FLOW` | Commerce flow and models | 6 | WC3 flow charts, Desktop Hosting |
| `QUIZ-TOOLS` | Open source tools | 4 | Tool reference documents |

**Categories:** `commerce_flow`, `models`, `tools`, `billing`, `data_quality`, `inventory`
**Difficulties:** `beginner`, `intermediate`, `advanced`

To add questions: create or update Document records with `model_name="quiz"` and body containing `{"questions": [...]}`.

---

## Diagramming Tools — Alice Generates Workflow Visuals

| Tool | IDA | Version | Install | Output formats |
|------|-----|---------|---------|----------------|
| **Graphviz** | `TOOL-GRAPHVIZ` | 13.1.2 | `brew install graphviz` | PDF, SVG, PNG, EPS |
| **D2** | `TOOL-D2` | 0.7.1 | `brew install d2` | SVG, PDF, PNG |
| **Mermaid** | `TOOL-MERMAID` | 11.16.0 | `npx @mermaid-js/mermaid-cli` | SVG, PNG, PDF |

**Use case:** Alice diagrams a customer's actual commerce workflow from their data. "Show me how my business works."

### WC3 Flow Charts (generated)

All at `~/Allie/readmes/flowcharts/`:

| File | What it shows |
|------|--------------|
| `wc3-master-flow.dot/.pdf` | Full commerce cycle — Contact → GL |
| `wc3-order-to-invoice.dot/.pdf` | Customer → verify → Order → Production → Invoice |
| `wc3-inventory-buckets.dot/.pdf` | Quantity flow: on_hand, on_so, on_po, on_wo → available |
| `wc3-payment-gl.dot/.pdf` | Invoice → Ledger → Aging → Payment → Journals → GL |

Regenerate: `dot -Tpdf <name>.dot -o <name>.pdf`

---

## PDF / Document Generation

| Tool | IDA | Version | Purpose |
|------|-----|---------|---------|
| **WeasyPrint** | `TOOL-WEASYPRINT` | 69.0 | HTML/CSS → branded PDF (invoices, proposals, reports) |
| **ReportLab** | `TOOL-REPORTLAB` | 5.0.0 | Programmatic PDF (exact positioning, barcodes, labels) |
| **PyMuPDF** | `TOOL-PYMUPDF` | 1.28.0 | PDF text extraction (vector store ingestion, supplier docs) |

**Pipeline:** Data → Diagram (Graphviz/D2) → HTML template → WeasyPrint → branded PDF

---

## Data Visualization

| Tool | IDA | Version | Purpose |
|------|-----|---------|---------|
| **matplotlib** | `TOOL-MATPLOTLIB` | 3.11.0 | Charts — margin velocity, campaign ROI, inventory turns, sales trends |
| **Pillow** | `TOOL-PILLOW` | 12.3.0 | Image processing — thumbnails, watermarks, format conversion |
| **svgwrite** | `TOOL-SVGWRITE` | 1.4.3 | SVG generation for web embedding |
| **CairoSVG** | `TOOL-CAIROSVG` | 2.9.0 | SVG → PDF/PNG conversion |

---

## Ingrid — Data Conversion Tools

| Tool | IDA | Version | Purpose |
|------|-----|---------|---------|
| **pandas** | `TOOL-PANDAS` | 3.0.3 | Read CSV/Excel/JSON/SQL, normalize, convert types |
| **openpyxl** | `TOOL-OPENPYXL` | 3.1.5 | Modern Excel (.xlsx) reader/writer |
| **xlrd** | `TOOL-XLRD` | 2.0.2 | Legacy Excel (.xls) reader |
| **xmltodict** | `TOOL-XMLTODICT` | — | XML → Python dict (EDI, QuickBooks, supplier feeds) |
| **chardet** | `TOOL-CHARDET` | 7.4.3 | File encoding detection (UTF-8, Latin-1, Windows-1252) |
| **phonenumbers** | `TOOL-PHONENUMBERS` | 9.0.34 | Phone number normalization (Google libphonenumber) |
| **pycountry** | `TOOL-PYCOUNTRY` | 26.2.16 | ISO country/currency/language codes |
| **thefuzz** | `TOOL-THEFUZZ` | 0.22.1 | Fuzzy string matching (customer deduplication) |
| **tabulate** | `TOOL-TABULATE` | 0.10.0 | Pretty-print tables for reports |

**Ingrid's pipeline:** External file → chardet (encoding) → pandas (read/normalize) → phonenumbers/pycountry (clean) → thefuzz (dedup) → JSON output → wcapi import

---

## Chrome DevTools MCP

Browser inspection for debugging and testing. Requires Chrome with `--remote-debugging-port=9222`.

**Chrome Debug app** at `/Applications/Chrome Debug.app` — wrapper that launches Chrome with debug port always on. Same profile, same extensions.

Full documentation: `~/Allie/readmes/46-chrome-devtools-mcp.md`

---

## Alice Services — Business Logic

| Service | Readme | What it does |
|---------|--------|-------------|
| **Dedup** | `topics/ai/alice-dedup.md` | Duplicate detection and extraction. Scans orgbase/contact/item, hard deletes dups, bundle files for operator review (indented BOM pattern), Claude escalation for complex cases. Connection: `conn-alice-dedup` (id=52). |
| **Exchange Rates** | `topics/architecture/exchange-rates.md` | Setting-based currency conversion. All amounts in base currency, rate captured at transaction time, FX gain/loss at settlement. Flowchart: `~/Allie/readmes/flowcharts/wc3-exchange-rates.dot`. |
| **Commission Invoices** | — | Tradeshow pattern: split order by vendor, manufacturer fulfills, commission invoice after fulfillment. Reports: "Split by Vendor" (id=439), "Commission Invoice" (id=440). Service: `transactions/services/split_by_vendor.py`. |

---

## All Tool Document Records

Every tool above has a Document record in WC3 with `model_name="tool_reference"`. Search in databrowser:
- Filter: `model_name = tool_reference`
- Or search by IDA: `TOOL-GRAPHVIZ`, `TOOL-PANDAS`, etc.

Each record contains: version, install command, used_by agents, purpose, resource links (homepage, docs, source, gallery), and license. Body is JSON — machine-readable.
