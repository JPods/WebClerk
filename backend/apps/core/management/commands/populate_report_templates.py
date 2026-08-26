"""Populate Report records with templates — Alice's best-effort generator.

Walks every active Report record and populates config based on output_type:
  - print/report/statement → pdfme JSON template
  - export                 → field list + delimiter config
  - email                  → subject + body templates with merge fields
  - label                  → pdfme label template (Avery 5160)
  - api/json               → endpoint placeholder config

Reports that need human editing (custom layouts, logos, examples from WC2)
are flagged in config.needs_review with a reason and reference links.

Usage:
    python manage.py populate_report_templates                # dry run — show what would change
    python manage.py populate_report_templates --apply        # actually update Report records
    python manage.py populate_report_templates --apply --actions  # update + create Actions for reviews

References:
    React .tsx prints: React2025/src/apps/transactions/components/print/
    pdfme starter:     React2025/src/services/pdfme/starter-templates/invoice.json
    WC2 PDF examples:  ~/Documents/CommerceExpert/Printing/
    WC2 form images:   ~/Documents/CommerceExpert/wc3_form_examples/
    Field registry:    React2025/src/services/pdfme/fieldRegistry.ts
    Flow chart:        webClerk3/readmes/flowcharts/wc3-print-system.dot
"""
import json
import time
from django.core.management.base import BaseCommand
from apps.core.models.report import Report

# ---------------------------------------------------------------------------
# pdfme template builders
# ---------------------------------------------------------------------------

US_LETTER_W = 215.9  # mm
US_LETTER_H = 279.4

def _text(name, x, y, w, h, fontSize=10, content="", **kw):
    el = {
        "type": "text", "name": name,
        "position": {"x": x, "y": y},
        "width": w, "height": h,
        "fontSize": fontSize, "content": content,
        "fontColor": "#111111", "readOnly": True,
    }
    el.update(kw)
    return el

def _multivar(name, x, y, w, h, text_fmt, variables, fontSize=9):
    return {
        "type": "multiVariableText", "name": name,
        "position": {"x": x, "y": y},
        "width": w, "height": h,
        "fontSize": fontSize, "fontColor": "#333333",
        "text": text_fmt, "variables": variables,
        "content": json.dumps({v: "" for v in variables}),
        "readOnly": True,
    }

def _line(name, x, y, w, color="#cccccc"):
    return {
        "type": "line", "name": name,
        "position": {"x": x, "y": y},
        "width": w, "height": 0.5,
        "color": color, "readOnly": True,
    }

def _table(name, x, y, w, h, heads, widths):
    return {
        "type": "table", "name": name,
        "position": {"x": x, "y": y},
        "width": w, "height": h,
        "showHead": True, "head": heads,
        "headWidthPercentages": widths,
        "headStyles": {"fontSize": 8, "fontColor": "#ffffff",
                       "backgroundColor": "#333333", "alignment": "left"},
        "bodyStyles": {"fontSize": 8, "alternateBackgroundColor": "#f9f9f9"},
        "content": "[]", "readOnly": True,
    }


# --- Transaction document (invoice, order, proposal, purchase, etc.) ---
def build_transaction_template(doc_type, doc_title):
    """Standard transaction form: header + addresses + line items + totals."""
    return {
        "name": doc_title,
        "documentType": doc_type,
        "template": {
            "schemas": [[
                _text("companyName", 20, 15, 80, 12, fontSize=16),
                _text("companyDetail", 20, 28, 80, 8, fontSize=8, fontColor="#666666"),
                _text("head", 140, 15, 55, 18, fontSize=28,
                      content=doc_title.upper(), alignment="right"),
                _line("headerLine", 20, 40, 175),

                # Bill To / Ship To
                _text("billToLabel", 20, 44, 30, 6, fontSize=8,
                      content="BILL TO", fontColor="#666666"),
                _text("billTo", 20, 50, 75, 24, fontSize=9),
                _text("shipToLabel", 105, 44, 30, 6, fontSize=8,
                      content="SHIP TO", fontColor="#666666"),
                _text("shipTo", 105, 50, 75, 24, fontSize=9),

                # Document metadata
                _multivar("docMeta", 20, 78, 175, 10,
                          "{docNumber}  |  Date: {docDate}  |  Terms: {terms}  |  PO#: {custPO}",
                          ["docNumber", "docDate", "terms", "custPO"], fontSize=9),
                _line("metaLine", 20, 89, 175),

                # Line items table
                _table("lineItems", 20, 92, 175, 120,
                       ["Qty", "Item #", "Description", "Unit Price", "Extended"],
                       [8, 15, 47, 15, 15]),

                # Totals
                _line("totalsLine", 120, 216, 75),
                _multivar("totals", 120, 218, 75, 30,
                          "Subtotal: {subtotal}\nTax: {tax}\nShipping: {shipping}\nTotal: {total}\nBalance Due: {balance}",
                          ["subtotal", "tax", "shipping", "total", "balance"], fontSize=9),

                # Comments
                _text("comments", 20, 218, 90, 20, fontSize=8, fontColor="#444444"),

                # Footer
                _line("footerLine", 20, 260, 175),
                _text("footer", 20, 262, 175, 8, fontSize=7, fontColor="#999999",
                      content=f"{doc_title} generated by WebClerk"),
            ]],
            "basePdf": {
                "width": US_LETTER_W, "height": US_LETTER_H,
                "padding": [15, 15, 15, 15],
            },
        },
    }


# --- List / summary report ---
def build_list_template(title, columns, col_widths=None):
    """Tabular list report with title + date + table."""
    n = len(columns)
    widths = col_widths or [round(100/n)] * n
    # Ensure widths sum to 100
    widths[-1] = 100 - sum(widths[:-1])
    return {
        "name": title,
        "documentType": "list",
        "template": {
            "schemas": [[
                _text("reportTitle", 20, 15, 120, 12, fontSize=16, content=title),
                _text("reportDate", 140, 15, 55, 8, fontSize=8,
                      alignment="right", fontColor="#666666"),
                _text("companyName", 20, 28, 80, 6, fontSize=8, fontColor="#666666"),
                _line("headerLine", 20, 36, 175),
                _table("data", 20, 40, 175, 220, columns, widths),
                _line("footerLine", 20, 265, 175),
                _text("footer", 20, 267, 175, 6, fontSize=7, fontColor="#999999"),
            ]],
            "basePdf": {
                "width": US_LETTER_W, "height": US_LETTER_H,
                "padding": [15, 15, 15, 15],
            },
        },
    }


# --- Statement ---
def build_statement_template():
    return build_transaction_template("statement", "Statement")


# --- Label (Avery 5160: 1" x 2-5/8", 30 per sheet, 3 across × 10 down) ---
def build_label_template(title):
    labels = []
    x_starts = [4.8, 72.4, 140.0]  # mm from left
    y_start = 12.7
    label_w = 66.7
    label_h = 25.4
    for row in range(10):
        for col in range(3):
            idx = row * 3 + col
            x = x_starts[col]
            y = y_start + row * label_h
            labels.append(
                _text(f"label_{idx}", x, y, label_w - 2, label_h - 2,
                      fontSize=8, fontColor="#111111")
            )
    return {
        "name": title,
        "documentType": "label",
        "template": {
            "schemas": [labels],
            "basePdf": {
                "width": US_LETTER_W, "height": US_LETTER_H,
                "padding": [0, 0, 0, 0],
            },
        },
    }


# ---------------------------------------------------------------------------
# Export config builder
# ---------------------------------------------------------------------------

# Default export fields per model
EXPORT_FIELDS = {
    "customer":  ["ida", "name_first", "name_last", "company", "email", "phone",
                   "address_1", "city", "state", "zip", "country", "status",
                   "totals.sales_ytd", "totals.sales_ly", "totals.balance"],
    "vendor":    ["ida", "name_first", "name_last", "company", "email", "phone",
                   "address_1", "city", "state", "zip", "country", "status"],
    "contact":   ["ida", "name_first", "name_last", "company", "email", "phone",
                   "address_1", "city", "state", "zip", "status"],
    "item":      ["ida", "name", "description", "uom", "status",
                   "price.retail", "price.wholesale", "cost.standard",
                   "quantity.on_hand", "quantity.available", "quantity.on_order"],
    "invoice":   ["ida", "status", "attention", "dt_created",
                   "totals.subtotal", "totals.tax", "totals.total", "totals.balance",
                   "refs.links.customer"],
    "order":     ["ida", "status", "attention", "dt_created",
                   "totals.subtotal", "totals.tax", "totals.total", "totals.balance",
                   "refs.links.customer"],
    "proposal":  ["ida", "status", "attention", "dt_created",
                   "totals.subtotal", "totals.tax", "totals.total", "totals.balance",
                   "refs.links.customer"],
    "purchase":  ["ida", "status", "attention", "dt_created",
                   "totals.subtotal", "totals.tax", "totals.total", "totals.balance",
                   "refs.links.vendor"],
    "payment":   ["ida", "type", "amount", "dt_created", "status",
                   "refs.links.contact"],
    "serial":    ["ida", "item_ida", "status", "dt_created"],
    "employee":  ["ida", "name_first", "name_last", "email", "phone", "status"],
    "action":    ["ida", "task.en", "status", "kanban_column", "priority",
                   "project_name", "dt_created"],
}

def build_export_config(model_name):
    fields = EXPORT_FIELDS.get(model_name, ["ida", "status", "dt_created"])
    return {
        "fields": fields,
        "delimiter": "tab",
        "line_ending": "\\n",
        "include_header": True,
        "encoding": "utf-8",
    }


# ---------------------------------------------------------------------------
# Email template builder
# ---------------------------------------------------------------------------

EMAIL_SUBJECTS = {
    "invoice":  "Invoice {{ida}} from {{company_name}}",
    "order":    "Order Confirmation {{ida}} from {{company_name}}",
    "proposal": "Proposal {{ida}} from {{company_name}}",
    "purchase": "Purchase Order {{ida}} — {{company_name}}",
    "customer": "{{subject}} — {{company_name}}",
    "statement":"Account Statement — {{company_name}}",
}

EMAIL_BODY = """<div style="font-family: -apple-system, Arial, sans-serif; max-width: 600px; margin: 0 auto;">
  <div style="border-bottom: 2px solid #0e639c; padding: 16px 0;">
    <h2 style="margin: 0; color: #111;">{{company_name}}</h2>
  </div>
  <div style="padding: 20px 0;">
    <p>Dear {{attention}},</p>
    <p>{{body_text}}</p>
    <p>Document: <strong>{{ida}}</strong><br/>
       Date: {{date}}<br/>
       Amount: {{total}}</p>
  </div>
  <div style="border-top: 1px solid #ddd; padding: 12px 0; font-size: 12px; color: #666;">
    {{company_name}} · {{company_address}} · {{company_phone}}
  </div>
</div>"""

def build_email_config(model_name, report_name):
    subject = EMAIL_SUBJECTS.get(model_name, "{{subject}} — {{company_name}}")
    # Customize subject for specific report names
    name_lower = report_name.lower()
    if "statement" in name_lower:
        subject = "Account Statement — {{company_name}}"
    elif "confirmation" in name_lower:
        subject = "Order Confirmation {{ida}} — {{company_name}}"
    elif "condition" in name_lower:
        subject = "Condition Report {{ida}} — {{company_name}}"
    elif "warranty" in name_lower:
        subject = "Warranty Information — {{company_name}}"
    return {
        "subject_template": subject,
        "body_template": EMAIL_BODY,
        "attach_pdf": True,
        "merge_fields": ["company_name", "company_address", "company_phone",
                         "attention", "ida", "date", "total", "body_text", "subject"],
    }


# ---------------------------------------------------------------------------
# Review flags — reports that need human attention or WC2 examples
# ---------------------------------------------------------------------------

NEEDS_EXAMPLE = {
    # Proposals — WC2 had 4 distinct layouts, we need to understand each
    "Proposal 1": {
        "reason": "WC2 had 4 numbered proposal layouts with different column structures. Need WC2 example PDF to replicate.",
        "refs": [
            "~/Documents/CommerceExpert/Printing/WebClerk v 10.6r.pdf",
            "~/Documents/CommerceExpert/wc3_form_examples/Report_Selection/Report_wc2_Preview.png",
            "React2025/src/apps/transactions/components/print/ProposalPrintDocument.tsx",
        ],
    },
    "Proposal 2": {"reason": "Distinct WC2 layout — need example to differentiate from Proposal 1.",
                    "refs": ["~/Documents/CommerceExpert/Printing/"]},
    "Proposal 3": {"reason": "Distinct WC2 layout — need example.", "refs": ["~/Documents/CommerceExpert/Printing/"]},
    "Proposal 4": {"reason": "Distinct WC2 layout — need example.", "refs": ["~/Documents/CommerceExpert/Printing/"]},
    "Customer Quote Form": {"reason": "Custom quote format — need WC2 example.",
                            "refs": ["~/Documents/CommerceExpert/Printing/"]},

    # Specialized invoice forms
    "Invoice - Shipping": {"reason": "4-column header layout with DownPayment and Contract Detail from WC2.",
                           "refs": ["React2025/src/apps/transactions/components/print/InvoiceShippingPrint.tsx"]},
    "Invoice - Foreign": {"reason": "International invoice — customs, HS codes, country of origin fields.",
                          "refs": ["React2025/src/apps/transactions/components/print/InvoiceServicePrint.tsx"]},
    "Invoice Bill of Lading": {"reason": "BOL format — carrier, weight, class, NMFC — needs trucking-industry layout.",
                               "refs": ["~/Documents/CommerceExpert/Printing/"]},
    "Bill of Lading": {"reason": "BOL format — carrier fields, NMFC codes. Need industry-standard layout.",
                       "refs": ["~/Documents/CommerceExpert/Printing/"]},
    "Customs Proforma Invoice": {"reason": "Customs form — HS codes, country of origin, declared values.",
                                 "refs": []},
    "Customs Proforma": {"reason": "Customs proforma — same as above, verify if duplicate.",
                         "refs": []},

    # PeopleSoft / specialized integrations
    "PeopleSoft Draft Billing": {"reason": "PeopleSoft-specific format. Need customer example.", "refs": []},

    # PPC forms (specific company)
    "PPC Itemized Sales x Rep": {"reason": "PPC-specific report — need company format.", "refs": []},
    "PPC Sales x Salesman": {"reason": "PPC-specific report.", "refs": []},
    "PPC Sales x Tax Authority": {"reason": "PPC-specific report.", "refs": []},
    "PPC MTD Sales": {"reason": "PPC-specific report.", "refs": []},
    "PPC Daily Sales": {"reason": "PPC-specific report.", "refs": []},
    "PPC Invoice Charged": {"reason": "PPC-specific report.", "refs": []},
    "PPC Credit Memo Charge": {"reason": "PPC-specific report.", "refs": []},
    "PPC Credit Memo": {"reason": "PPC-specific report.", "refs": []},
    "PPC Inventory Status": {"reason": "PPC-specific inventory report.", "refs": []},
    "PPC Items w/Qty Sold": {"reason": "PPC-specific report.", "refs": []},

    # Embroidery / industry-specific
    "Embroidery Worksheet": {"reason": "Industry-specific worksheet — thread colors, placement, garment specs.",
                             "refs": []},
    "Schedule A": {"reason": "Customs Schedule A form — need regulatory format.", "refs": []},

    # Product spec sheet
    "Product Spec Sheet": {"reason": "Product data sheet — images, specs table, features. Needs rich layout.",
                           "refs": []},

    # Condition report
    "Condition Report": {"reason": "QA inspection report with photos/checkboxes. Needs rich layout.",
                         "refs": ["React2025/src/apps/transactions/components/print/"]},

    # Labels need specific Avery format verification
    "Item Barcode Labels": {"reason": "Barcode generation (Code128) — need barcode font or image generation.",
                            "refs": ["pdfme @pdfme/schemas barcodes plugin"]},
    "iLabel Printing": {"reason": "Specific iLabel format — need example.", "refs": []},
    "iLabel Printing (Meteor)": {"reason": "Meteor-specific label format.", "refs": []},
    "iLabels Customer": {"reason": "Customer iLabel format.", "refs": []},
}

# List report column definitions
LIST_COLUMNS = {
    "Contact Directory":     (["Name", "Company", "Phone", "Email", "City", "State"], None),
    "Contact List":          (["ID", "Name", "Company", "Phone", "Email", "Status"], None),
    "Customer List Export":  (["ID", "Name", "Company", "Phone", "Email", "City", "State", "Balance"], None),
    "Call List, Traveling":  (["Company", "Contact", "Phone", "City", "State", "Last Call"], None),
    "Customers by Rep":     (["Rep", "Company", "Contact", "Phone", "Sales YTD", "Balance"], None),
    "Contacts In Call List": (["Company", "Contact", "Phone", "Email", "Notes"], None),
    "Price List":            (["Item #", "Description", "UOM", "Retail", "Wholesale", "Distributor"], None),
    "Task List":             (["ID", "Task", "Status", "Priority", "Project", "Due"], None),
    "Employee Listing":      (["ID", "Name", "Email", "Phone", "Status"], None),
    "Chart of Accounts":     (["Account #", "Name", "Type", "Category", "Status"], None),
    "Journal Listing":       (["Date", "Reference", "Account", "Debit", "Credit", "Description"], None),
    "Vendor Contact List":   (["Company", "Contact", "Phone", "Email", "City", "State"], None),
    "Vendor List":           (["ID", "Company", "Phone", "Email", "Status", "Balance"], None),
    "Tax Authority Listing": (["Code", "Name", "Rate", "State", "Status"], None),
    "Open Receivables":      (["Customer", "Invoice #", "Date", "Amount", "Balance", "Days"], None),
    "Open Order Lines":      (["Order #", "Item #", "Description", "Qty Ordered", "Qty Shipped", "B/O"], None),
    "Document Index":        (["ID", "Title", "Type", "Model", "Date", "Status"], None),
    "List of Orders Report": (["Order #", "Date", "Customer", "Status", "Total", "Balance"], None),
    "Item Catalog Export":   (["Item #", "Name", "Description", "UOM", "Price", "Status"], None),
}

# Summary report columns
SUMMARY_COLUMNS = {
    "Receivable Summary":    (["Customer", "Current", "30 Days", "60 Days", "90+ Days", "Total"], None),
    "AR Aging Summary":      (["Customer", "Current", "30 Days", "60 Days", "90+ Days", "Total"], None),
    "AP Aging Summary":      (["Vendor", "Current", "30 Days", "60 Days", "90+ Days", "Total"], None),
    "Invoice Summary":       (["Date", "Count", "Subtotal", "Tax", "Total"], None),
    "Order Summary":         (["Date", "Count", "Subtotal", "Tax", "Total"], None),
    "Proposal Summary":      (["Date", "Count", "Subtotal", "Tax", "Total"], None),
    "Purchase Summary":      (["Date", "Count", "Subtotal", "Tax", "Total"], None),
    "Work Order Summary":    (["Date", "Count", "Subtotal", "Total"], None),
    "Trial Balance":         (["Account", "Debit", "Credit", "Balance"], None),
    "Sales by State (Summary)": (["State", "Orders", "Sales", "Tax", "Total"], None),
    "Summary of Sales by Rep":  (["Rep", "Orders", "Sales", "Commission", "Margin"], None),
    "Sales by Item and TypeSale": (["Item", "Type", "Qty Sold", "Sales", "Cost", "Margin"], None),
}


# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Populate Report records with pdfme templates, export configs, and email templates"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Actually update Report records (default is dry run)")
        parser.add_argument("--actions", action="store_true",
                            help="Create Action records for reports needing review")

    def handle(self, *args, **options):
        apply = options["apply"]
        create_actions = options["actions"]

        reports = Report.objects.filter(
            is_active=True, is_deleted=False
        ).order_by("model_name", "sort_order", "name")

        stats = {"generated": 0, "skipped_has_template": 0,
                 "needs_review": 0, "export_configured": 0,
                 "email_configured": 0, "label_configured": 0,
                 "api_skipped": 0, "total": 0}
        review_list = []

        for r in reports:
            stats["total"] += 1
            cfg = r.config if isinstance(r.config, dict) else {}
            model = (r.model_name or "").lower()
            name = r.name or ""
            output = (r.output_type or "print").lower()
            category = (r.category or "").lower()

            # Skip if already has a template
            if cfg.get("pdfme_template") or cfg.get("fields") or cfg.get("subject_template"):
                stats["skipped_has_template"] += 1
                continue

            # Check if needs human review
            review_info = NEEDS_EXAMPLE.get(name)
            if review_info:
                cfg["needs_review"] = True
                cfg["review_reason"] = review_info["reason"]
                cfg["review_refs"] = review_info["refs"]
                stats["needs_review"] += 1
                review_list.append((r.id, name, model, review_info["reason"]))

            # --- Route by output_type ---

            if output == "export":
                export_cfg = build_export_config(model)
                cfg.update(export_cfg)
                stats["export_configured"] += 1
                if apply:
                    r.config = cfg
                    r.save(update_fields=["config"])
                self.stdout.write(f"  EXPORT  {model:<18} {name}")

            elif output == "email" or output == "merge":
                email_cfg = build_email_config(model, name)
                cfg.update(email_cfg)
                stats["email_configured"] += 1
                if apply:
                    r.config = cfg
                    r.save(update_fields=["config"])
                self.stdout.write(f"  EMAIL   {model:<18} {name}")

            elif output == "label":
                cfg["pdfme_template"] = build_label_template(name)
                stats["label_configured"] += 1
                if apply:
                    r.config = cfg
                    r.save(update_fields=["config"])
                self.stdout.write(f"  LABEL   {model:<18} {name}")

            elif output in ("api", "json"):
                # API/JSON reports need endpoint config — can't auto-generate
                cfg.setdefault("needs_review", True)
                cfg.setdefault("review_reason",
                               f"API/JSON report — needs endpoint URL or output format configuration.")
                cfg.setdefault("review_refs", [])
                stats["api_skipped"] += 1
                if apply:
                    r.config = cfg
                    r.save(update_fields=["config"])
                self.stdout.write(f"  API     {model:<18} {name} (needs endpoint config)")

            elif output == "print":
                # Try to generate a pdfme template

                # Check if it's a list/summary report
                if name in LIST_COLUMNS:
                    cols, widths = LIST_COLUMNS[name]
                    cfg["pdfme_template"] = build_list_template(name, cols, widths)
                    stats["generated"] += 1
                elif name in SUMMARY_COLUMNS:
                    cols, widths = SUMMARY_COLUMNS[name]
                    cfg["pdfme_template"] = build_list_template(name, cols, widths)
                    stats["generated"] += 1
                elif category in ("list", "summary"):
                    # Generic list — use model name as basis
                    cfg["pdfme_template"] = build_list_template(
                        name, ["ID", "Name", "Status", "Date", "Details"])
                    stats["generated"] += 1
                elif category == "statement":
                    cfg["pdfme_template"] = build_statement_template()
                    stats["generated"] += 1
                elif model in ("invoice", "order", "proposal", "purchase",
                               "receipt", "requisition", "workorder"):
                    # Transaction document
                    title_map = {
                        "invoice": "Invoice", "order": "Order",
                        "proposal": "Proposal", "purchase": "Purchase Order",
                        "receipt": "Receipt", "requisition": "Requisition",
                        "workorder": "Work Order",
                    }
                    doc_title = title_map.get(model, name)
                    # Use report name if it's more specific than the generic
                    if name not in (doc_title, f"{doc_title} Report"):
                        doc_title = name
                    cfg["pdfme_template"] = build_transaction_template(model, doc_title)
                    stats["generated"] += 1
                elif category in ("report", "operations", "customer_facing",
                                  "accounting", "sales_analysis"):
                    # Generic report — use a list-style table layout
                    cfg["pdfme_template"] = build_list_template(
                        name, ["Field", "Value", "Details"])
                    stats["generated"] += 1
                else:
                    # Anything else — generic
                    cfg["pdfme_template"] = build_list_template(
                        name, ["Field", "Value"])
                    stats["generated"] += 1

                if apply:
                    r.config = cfg
                    r.save(update_fields=["config"])
                self.stdout.write(f"  PRINT   {model:<18} {name}")

        # --- Summary ---
        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Total reports:          {stats['total']}")
        self.stdout.write(f"Already had template:   {stats['skipped_has_template']}")
        self.stdout.write(f"Print templates gen'd:  {stats['generated']}")
        self.stdout.write(f"Export configs:          {stats['export_configured']}")
        self.stdout.write(f"Email templates:         {stats['email_configured']}")
        self.stdout.write(f"Label templates:         {stats['label_configured']}")
        self.stdout.write(f"API/JSON (need config):  {stats['api_skipped']}")
        self.stdout.write(f"Flagged for review:      {stats['needs_review']}")
        if not apply:
            self.stdout.write("")
            self.stdout.write("DRY RUN — no changes saved. Use --apply to update records.")

        # --- Review list ---
        if review_list:
            self.stdout.write("")
            self.stdout.write("=" * 70)
            self.stdout.write("REPORTS NEEDING HUMAN REVIEW / WC2 EXAMPLES:")
            self.stdout.write("-" * 70)
            for rid, rname, rmodel, reason in review_list:
                self.stdout.write(f"  #{rid:<5} {rmodel:<18} {rname}")
                self.stdout.write(f"         Reason: {reason}")

        # --- Create Action records for reviews ---
        if create_actions and apply and review_list:
            from apps.core.models import Action
            now_ms = int(time.time() * 1000)

            for rid, rname, rmodel, reason in review_list:
                review_info = NEEDS_EXAMPLE.get(rname, {})
                refs_text = "\n".join(f"  - {r}" for r in review_info.get("refs", []))
                Action.objects.create(
                    task={"en": f"Review/edit report template: {rname} ({rmodel})"},
                    description={"en": f"Report #{rid} needs human review.\n\n"
                                       f"Reason: {reason}\n\n"
                                       f"References:\n{refs_text}\n\n"
                                       f"Open in PDF Designer: /pdf-designer/{rid}"},
                    kanban_column="Backlog",
                    status="open",
                    priority=3,
                    project_name="WC3 Print System",
                    project_ida="wc3-print",
                    dt_created=now_ms,
                    dt_modified=now_ms,
                    metadata={"domain": "WC3", "agent": "Alice",
                              "report_id": rid, "report_name": rname},
                )
            self.stdout.write(f"\nCreated {len(review_list)} Action records for review items.")

        # --- Update parent Action records ---
        if apply:
            from apps.core.models import Action
            now_ms = int(time.time() * 1000)
            parent_actions = Action.objects.filter(
                project_ida="wc3-print",
                status="open",
            )
            for a in parent_actions:
                task_text = (a.action or {}).get("en", "")
                if "primary reports" in task_text.lower():
                    a.kanban_column = "In Progress"
                    a.percent_complete = 80
                    a.description = {"en": (a.description or {}).get("en", "") +
                                    f"\n\n--- Auto-update {time.strftime('%Y-%m-%d')} ---\n"
                                    f"populate_report_templates generated templates for primary reports.\n"
                                    f"{stats['generated']} print, {stats['needs_review']} flagged for review."}
                    a.dt_modified = now_ms
                    a.save(update_fields=["kanban_column", "percent_complete",
                                          "description", "dt_modified"])
                elif "export" in task_text.lower() and "field" in task_text.lower():
                    a.kanban_column = "Done" if stats["export_configured"] > 0 else "In Progress"
                    a.percent_complete = 100 if stats["export_configured"] > 0 else 0
                    a.dt_modified = now_ms
                    a.save(update_fields=["kanban_column", "percent_complete", "dt_modified"])
                elif "email" in task_text.lower() and "template" in task_text.lower():
                    a.kanban_column = "Done" if stats["email_configured"] > 0 else "In Progress"
                    a.percent_complete = 100 if stats["email_configured"] > 0 else 0
                    a.dt_modified = now_ms
                    a.save(update_fields=["kanban_column", "percent_complete", "dt_modified"])
                elif "label" in task_text.lower() and "template" in task_text.lower():
                    a.kanban_column = "Done" if stats["label_configured"] > 0 else "In Progress"
                    a.percent_complete = 100 if stats["label_configured"] > 0 else 0
                    a.dt_modified = now_ms
                    a.save(update_fields=["kanban_column", "percent_complete", "dt_modified"])
            self.stdout.write("\nUpdated parent Action records with progress.")
