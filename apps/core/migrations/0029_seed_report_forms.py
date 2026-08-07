"""
Seed config.form (PrintLayout JSON) into Report records.

Each form layout defines sections that UniversalPrint renders:
  company_header, address_blocks, meta_row, line_items, totals,
  comments, conditions, signature, footer.

Reports that are analysis/summary (no single-record form) get no layout.
"""
from django.db import migrations
import json

# ---------------------------------------------------------------------------
# Base layouts — reusable across report variants
# ---------------------------------------------------------------------------

INVOICE_FORM = {
    "model": "invoice",
    "title": "Invoice",
    "family": "sell",
    "paper": "letter",
    "version": 1,
    "sections": [
        {"type": "company_header", "logo": True, "show_address": True, "show_contact": True},
        {"type": "address_blocks", "columns": [
            {"title": "Bill To", "fields": [
                {"field": "attention", "label": "Attn"},
                {"field": "company", "label": "Company"},
                {"field": "address_full", "label": "Address"},
                {"field": "phone", "label": "Phone"},
                {"field": "email", "label": "Email"},
            ]},
            {"title": "Ship To", "fields": [
                {"field": "config.ship_to.attention", "label": "Attn"},
                {"field": "config.ship_to.company", "label": "Company"},
                {"field": "config.ship_to.address", "label": "Address"},
                {"field": "config.ship_to.phone", "label": "Phone"},
            ]},
        ]},
        {"type": "meta_row", "fields": [
            {"field": "ida", "label": "Invoice #"},
            {"field": "status", "label": "Status"},
            {"field": "dt_created", "label": "Date", "format": "date"},
            {"field": "terms", "label": "Terms"},
            {"field": "price_level", "label": "Price Level"},
            {"field": "source.campaign_name", "label": "Cust PO#"},
        ]},
        {"type": "line_items", "show_footer_totals": True, "columns": [
            {"field": "item.ida_item", "label": "Item #", "width": "12%"},
            {"field": "item.description", "label": "Description", "width": "38%"},
            {"field": "quantity.active", "label": "Qty", "align": "right", "width": "8%"},
            {"field": "price.unit", "label": "Unit Price", "format": "currency", "align": "right", "width": "14%"},
            {"field": "price.discount_percent", "label": "Disc %", "format": "percent", "align": "right", "width": "10%"},
            {"field": "price.extended", "label": "Extended", "format": "currency", "align": "right", "width": "18%"},
        ]},
        {"type": "comments", "source": "comments.public", "label": "Comments"},
        {"type": "totals", "left_text": "Thank you for your business.", "rows": [
            {"field": "totals.subtotal", "label": "Subtotal", "format": "currency"},
            {"field": "totals.tax", "label": "Sales Tax", "format": "currency"},
            {"field": "totals.shipping", "label": "Shipping", "format": "currency"},
            {"field": "totals.total", "label": "Invoice Total", "format": "currency", "bold": True},
            {"field": "totals.balance", "label": "Balance Due", "format": "currency", "style": "bold"},
        ]},
        {"type": "conditions", "source": "conditions_description"},
        {"type": "signature", "preamble": "By signing below, the customer accepts the terms and conditions of this invoice.", "blocks": [
            {"label": "Customer", "lines": ["Signature", "Date"]},
            {"label": "Accepted By", "lines": ["Accepted By", "Date"]},
        ]},
        {"type": "footer", "fields": [
            {"field": "ida", "label": "Invoice #"},
            {"field": "customer_id", "label": "Customer #"},
            {"field": "source.campaign_name", "label": "PO #"},
        ]},
    ],
}

CREDIT_MEMO_FORM = {**INVOICE_FORM, "title": "Credit Memo"}
CREDIT_MEMO_FORM["sections"] = list(INVOICE_FORM["sections"])  # shallow copy
# Replace totals labels
credit_totals = {
    "type": "totals", "rows": [
        {"field": "totals.subtotal", "label": "Subtotal", "format": "currency"},
        {"field": "totals.tax", "label": "Sales Tax", "format": "currency"},
        {"field": "totals.shipping", "label": "Shipping", "format": "currency"},
        {"field": "totals.total", "label": "Credit Total", "format": "currency", "bold": True},
        {"field": "totals.balance", "label": "Credit Amount", "format": "currency", "style": "bold"},
    ],
}
# Replace signature
credit_sig = {"type": "signature", "blocks": [
    {"label": "Authorized By", "lines": ["Signature", "Date"]},
]}
credit_footer = {"type": "footer", "fields": [
    {"field": "ida", "label": "Credit Memo #"},
    {"field": "customer_id", "label": "Customer #"},
    {"field": "source.campaign_name", "label": "PO #"},
]}
CREDIT_MEMO_FORM["sections"] = [
    s if s.get("type") not in ("totals", "signature", "footer") else
    credit_totals if s.get("type") == "totals" else
    credit_sig if s.get("type") == "signature" else credit_footer
    for s in INVOICE_FORM["sections"]
]

INVOICE_SHIPPING_FORM = {**INVOICE_FORM, "title": "Invoice - Shipping"}
# Add ship via to meta
shipping_meta = {"type": "meta_row", "fields": [
    {"field": "ida", "label": "Invoice #"},
    {"field": "status", "label": "Status"},
    {"field": "dt_created", "label": "Date", "format": "date"},
    {"field": "terms", "label": "Terms"},
    {"field": "config.ship_via", "label": "Ship Via"},
    {"field": "config.ship_date", "label": "Ship Date", "format": "date"},
    {"field": "source.campaign_name", "label": "Cust PO#"},
]}
INVOICE_SHIPPING_FORM["sections"] = [
    shipping_meta if s.get("type") == "meta_row" else s
    for s in INVOICE_FORM["sections"]
]

ORDER_FORM = {
    "model": "order",
    "title": "Order Confirmation",
    "family": "sell",
    "paper": "letter",
    "version": 1,
    "sections": [
        {"type": "company_header", "logo": True, "show_address": True, "show_contact": True},
        {"type": "address_blocks", "columns": [
            {"title": "Sold To", "fields": [
                {"field": "attention", "label": "Attn"},
                {"field": "company", "label": "Company"},
                {"field": "address_full", "label": "Address"},
                {"field": "phone", "label": "Phone"},
                {"field": "email", "label": "Email"},
            ]},
            {"title": "Ship To", "fields": [
                {"field": "config.ship_to.attention", "label": "Attn"},
                {"field": "config.ship_to.company", "label": "Company"},
                {"field": "config.ship_to.address", "label": "Address"},
            ]},
        ]},
        {"type": "meta_row", "fields": [
            {"field": "ida", "label": "Order #"},
            {"field": "status", "label": "Status"},
            {"field": "dt_created", "label": "Date", "format": "date"},
            {"field": "terms", "label": "Terms"},
            {"field": "price_level", "label": "Price Level"},
            {"field": "source.campaign_name", "label": "Cust PO#"},
        ]},
        {"type": "line_items", "show_footer_totals": True, "columns": [
            {"field": "item.ida_item", "label": "Item #", "width": "12%"},
            {"field": "item.description", "label": "Description", "width": "38%"},
            {"field": "quantity.active", "label": "Qty Ordered", "align": "right", "width": "10%"},
            {"field": "price.unit", "label": "Unit Price", "format": "currency", "align": "right", "width": "14%"},
            {"field": "price.discount_percent", "label": "Disc %", "format": "percent", "align": "right", "width": "8%"},
            {"field": "price.extended", "label": "Extended", "format": "currency", "align": "right", "width": "18%"},
        ]},
        {"type": "comments", "source": "comments.public", "label": "Comments"},
        {"type": "totals", "left_text": "Thank you for your order.", "rows": [
            {"field": "totals.subtotal", "label": "Subtotal", "format": "currency"},
            {"field": "totals.tax", "label": "Sales Tax", "format": "currency"},
            {"field": "totals.shipping", "label": "Shipping", "format": "currency"},
            {"field": "totals.total", "label": "Order Total", "format": "currency", "bold": True},
        ]},
        {"type": "conditions", "source": "conditions_description"},
        {"type": "signature", "preamble": "By signing below, the customer authorizes this order.", "blocks": [
            {"label": "Customer", "lines": ["Signature", "Date"]},
            {"label": "Accepted By", "lines": ["Accepted By", "Date"]},
        ]},
        {"type": "footer", "fields": [
            {"field": "ida", "label": "Order #"},
            {"field": "customer_id", "label": "Customer #"},
            {"field": "source.campaign_name", "label": "PO #"},
        ]},
    ],
}

PACKING_SLIP_FORM = {
    "model": "order",
    "title": "Packing Slip",
    "family": "sell",
    "paper": "letter",
    "version": 1,
    "sections": [
        {"type": "company_header", "logo": True, "show_address": True, "show_contact": False},
        {"type": "address_blocks", "columns": [
            {"title": "Ship To", "fields": [
                {"field": "config.ship_to.attention", "label": "Attn"},
                {"field": "config.ship_to.company", "label": "Company"},
                {"field": "config.ship_to.address", "label": "Address"},
                {"field": "config.ship_to.phone", "label": "Phone"},
            ]},
            {"title": "Sold To", "fields": [
                {"field": "attention", "label": "Attn"},
                {"field": "company", "label": "Company"},
                {"field": "address_full", "label": "Address"},
            ]},
        ]},
        {"type": "meta_row", "fields": [
            {"field": "ida", "label": "Order #"},
            {"field": "dt_created", "label": "Date", "format": "date"},
            {"field": "config.ship_via", "label": "Ship Via"},
            {"field": "source.campaign_name", "label": "Cust PO#"},
        ]},
        {"type": "line_items", "columns": [
            {"field": "item.ida_item", "label": "Item #", "width": "15%"},
            {"field": "item.description", "label": "Description", "width": "55%"},
            {"field": "quantity.active", "label": "Qty Shipped", "align": "right", "width": "15%"},
            {"field": "item.uom", "label": "UOM", "width": "15%"},
        ]},
        {"type": "comments", "source": "comments.shipping", "label": "Shipping Instructions"},
        {"type": "footer", "fields": [
            {"field": "ida", "label": "Order #"},
            {"field": "customer_id", "label": "Customer #"},
        ]},
    ],
}

PICK_TICKET_FORM = {
    "model": "order",
    "title": "Pick Ticket",
    "family": "sell",
    "paper": "letter",
    "version": 1,
    "sections": [
        {"type": "company_header", "logo": False, "show_address": False, "show_contact": False},
        {"type": "meta_row", "fields": [
            {"field": "ida", "label": "Order #"},
            {"field": "dt_created", "label": "Date", "format": "date"},
            {"field": "attention", "label": "Customer"},
            {"field": "config.ship_via", "label": "Ship Via"},
        ]},
        {"type": "line_items", "columns": [
            {"field": "item.ida_item", "label": "Item #", "width": "15%"},
            {"field": "item.description", "label": "Description", "width": "40%"},
            {"field": "quantity.active", "label": "Qty", "align": "right", "width": "10%"},
            {"field": "item.location", "label": "Location", "width": "15%"},
            {"field": "item.uom", "label": "UOM", "width": "10%"},
        ]},
        {"type": "footer", "fields": [
            {"field": "ida", "label": "Order #"},
            {"field": "attention", "label": "Customer"},
        ]},
    ],
}

PROPOSAL_FORM = {
    "model": "proposal",
    "title": "Proposal",
    "family": "sell",
    "paper": "letter",
    "version": 1,
    "sections": [
        {"type": "company_header", "logo": True, "show_address": True, "show_contact": True},
        {"type": "address_blocks", "columns": [
            {"title": "Prepared For", "fields": [
                {"field": "attention", "label": "Attn"},
                {"field": "company", "label": "Company"},
                {"field": "address_full", "label": "Address"},
                {"field": "phone", "label": "Phone"},
                {"field": "email", "label": "Email"},
            ]},
        ]},
        {"type": "meta_row", "fields": [
            {"field": "ida", "label": "Proposal #"},
            {"field": "status", "label": "Status"},
            {"field": "dt_created", "label": "Date", "format": "date"},
            {"field": "terms", "label": "Terms"},
            {"field": "price_level", "label": "Price Level"},
        ]},
        {"type": "line_items", "show_footer_totals": True, "columns": [
            {"field": "item.ida_item", "label": "Item #", "width": "12%"},
            {"field": "item.description", "label": "Description", "width": "40%"},
            {"field": "quantity.active", "label": "Qty", "align": "right", "width": "10%"},
            {"field": "price.unit", "label": "Unit Price", "format": "currency", "align": "right", "width": "14%"},
            {"field": "price.extended", "label": "Extended", "format": "currency", "align": "right", "width": "18%"},
        ]},
        {"type": "comments", "source": "comments.public", "label": "Notes"},
        {"type": "totals", "rows": [
            {"field": "totals.subtotal", "label": "Subtotal", "format": "currency"},
            {"field": "totals.tax", "label": "Estimated Tax", "format": "currency"},
            {"field": "totals.shipping", "label": "Shipping", "format": "currency"},
            {"field": "totals.total", "label": "Proposal Total", "format": "currency", "bold": True},
        ]},
        {"type": "conditions", "source": "conditions_description"},
        {"type": "signature", "preamble": "Customer acceptance authorizes work to proceed.", "blocks": [
            {"label": "Customer Acceptance", "lines": ["Signature", "Print Name", "Date"]},
        ]},
        {"type": "footer", "fields": [
            {"field": "ida", "label": "Proposal #"},
            {"field": "customer_id", "label": "Customer #"},
        ]},
    ],
}

PURCHASE_ORDER_FORM = {
    "model": "purchase",
    "title": "Purchase Order",
    "family": "exec",
    "paper": "letter",
    "version": 1,
    "sections": [
        {"type": "company_header", "logo": True, "show_address": True, "show_contact": True},
        {"type": "address_blocks", "columns": [
            {"title": "Vendor", "fields": [
                {"field": "attention", "label": "Attn"},
                {"field": "company", "label": "Company"},
                {"field": "address_full", "label": "Address"},
                {"field": "phone", "label": "Phone"},
                {"field": "email", "label": "Email"},
            ]},
            {"title": "Ship To", "fields": [
                {"field": "config.ship_to.attention", "label": "Attn"},
                {"field": "config.ship_to.company", "label": "Company"},
                {"field": "config.ship_to.address", "label": "Address"},
            ]},
        ]},
        {"type": "meta_row", "fields": [
            {"field": "ida", "label": "PO #"},
            {"field": "status", "label": "Status"},
            {"field": "dt_created", "label": "Date", "format": "date"},
            {"field": "terms", "label": "Terms"},
            {"field": "config.ship_via", "label": "Ship Via"},
            {"field": "config.fob", "label": "FOB"},
        ]},
        {"type": "line_items", "show_footer_totals": True, "columns": [
            {"field": "item.ida_item", "label": "Item #", "width": "12%"},
            {"field": "item.description", "label": "Description", "width": "38%"},
            {"field": "quantity.active", "label": "Qty", "align": "right", "width": "10%"},
            {"field": "cost.unit", "label": "Unit Cost", "format": "currency", "align": "right", "width": "14%"},
            {"field": "cost.extended", "label": "Extended", "format": "currency", "align": "right", "width": "18%"},
        ]},
        {"type": "comments", "source": "comments.public", "label": "Notes"},
        {"type": "totals", "rows": [
            {"field": "totals.subtotal", "label": "Subtotal", "format": "currency"},
            {"field": "totals.tax", "label": "Tax", "format": "currency"},
            {"field": "totals.shipping", "label": "Freight", "format": "currency"},
            {"field": "totals.total", "label": "PO Total", "format": "currency", "bold": True},
        ]},
        {"type": "conditions", "source": "conditions_description"},
        {"type": "footer", "fields": [
            {"field": "ida", "label": "PO #"},
            {"field": "vendor_id", "label": "Vendor #"},
        ]},
    ],
}

WORK_ORDER_FORM = {
    "model": "workorder",
    "title": "Work Order",
    "family": "exec",
    "paper": "letter",
    "version": 1,
    "sections": [
        {"type": "company_header", "logo": True, "show_address": True, "show_contact": True},
        {"type": "address_blocks", "columns": [
            {"title": "Customer", "fields": [
                {"field": "attention", "label": "Attn"},
                {"field": "company", "label": "Company"},
                {"field": "address_full", "label": "Address"},
                {"field": "phone", "label": "Phone"},
            ]},
        ]},
        {"type": "meta_row", "fields": [
            {"field": "ida", "label": "WO #"},
            {"field": "status", "label": "Status"},
            {"field": "priority", "label": "Priority"},
            {"field": "dt_created", "label": "Date", "format": "date"},
        ]},
        {"type": "line_items", "show_footer_totals": True, "columns": [
            {"field": "item.ida_item", "label": "Item #", "width": "12%"},
            {"field": "item.description", "label": "Description", "width": "40%"},
            {"field": "quantity.active", "label": "Qty", "align": "right", "width": "10%"},
            {"field": "price.unit", "label": "Rate", "format": "currency", "align": "right", "width": "14%"},
            {"field": "price.extended", "label": "Extended", "format": "currency", "align": "right", "width": "18%"},
        ]},
        {"type": "comments", "source": "comments.public", "label": "Work Instructions"},
        {"type": "totals", "rows": [
            {"field": "totals.subtotal", "label": "Subtotal", "format": "currency"},
            {"field": "totals.tax", "label": "Tax", "format": "currency"},
            {"field": "totals.total", "label": "Total", "format": "currency", "bold": True},
        ]},
        {"type": "signature", "blocks": [
            {"label": "Completed By", "lines": ["Signature", "Date"]},
            {"label": "Accepted By", "lines": ["Signature", "Date"]},
        ]},
        {"type": "footer", "fields": [
            {"field": "ida", "label": "WO #"},
            {"field": "customer_id", "label": "Customer #"},
        ]},
    ],
}

PAYMENT_RECEIPT_FORM = {
    "model": "payment",
    "title": "Payment Receipt",
    "family": "sell",
    "paper": "letter",
    "version": 1,
    "sections": [
        {"type": "company_header", "logo": True, "show_address": True, "show_contact": True},
        {"type": "address_blocks", "columns": [
            {"title": "Received From", "fields": [
                {"field": "attention", "label": "Attn"},
                {"field": "company", "label": "Company"},
                {"field": "address_full", "label": "Address"},
            ]},
        ]},
        {"type": "meta_row", "fields": [
            {"field": "ida", "label": "Receipt #"},
            {"field": "dt_created", "label": "Date", "format": "date"},
            {"field": "config.method", "label": "Method"},
            {"field": "config.reference", "label": "Reference"},
        ]},
        {"type": "totals", "left_text": "Thank you for your payment.", "rows": [
            {"field": "total", "label": "Amount Received", "format": "currency", "bold": True},
        ]},
        {"type": "footer", "fields": [
            {"field": "ida", "label": "Receipt #"},
            {"field": "customer_id", "label": "Customer #"},
        ]},
    ],
}

STATEMENT_FORM = {
    "model": "customer",
    "title": "Statement of Account",
    "family": "sell",
    "paper": "letter",
    "version": 1,
    "sections": [
        {"type": "company_header", "logo": True, "show_address": True, "show_contact": True},
        {"type": "address_blocks", "columns": [
            {"title": "Account", "fields": [
                {"field": "attention", "label": "Attn"},
                {"field": "company", "label": "Company"},
                {"field": "address_full", "label": "Address"},
            ]},
        ]},
        {"type": "meta_row", "fields": [
            {"field": "ida", "label": "Account #"},
            {"field": "terms", "label": "Terms"},
        ]},
    ],
}

RECEIVING_REPORT_FORM = {
    "model": "purchase",
    "title": "Receiving Report",
    "family": "exec",
    "paper": "letter",
    "version": 1,
    "sections": [
        {"type": "company_header", "logo": False, "show_address": False, "show_contact": False},
        {"type": "meta_row", "fields": [
            {"field": "ida", "label": "PO #"},
            {"field": "dt_created", "label": "Date", "format": "date"},
            {"field": "attention", "label": "Vendor"},
            {"field": "company", "label": "Company"},
        ]},
        {"type": "line_items", "columns": [
            {"field": "item.ida_item", "label": "Item #", "width": "15%"},
            {"field": "item.description", "label": "Description", "width": "40%"},
            {"field": "quantity.active", "label": "Qty Ordered", "align": "right", "width": "12%"},
            {"field": "quantity.remaining", "label": "Qty Received", "align": "right", "width": "12%"},
            {"field": "item.uom", "label": "UOM", "width": "10%"},
        ]},
        {"type": "signature", "blocks": [
            {"label": "Received By", "lines": ["Signature", "Date"]},
            {"label": "Inspected By", "lines": ["Signature", "Date"]},
        ]},
        {"type": "footer", "fields": [
            {"field": "ida", "label": "PO #"},
            {"field": "vendor_id", "label": "Vendor #"},
        ]},
    ],
}

BOL_FORM = {
    "model": "order",
    "title": "Bill of Lading",
    "family": "sell",
    "paper": "letter",
    "version": 1,
    "sections": [
        {"type": "company_header", "logo": True, "show_address": True, "show_contact": True},
        {"type": "address_blocks", "columns": [
            {"title": "Shipper", "fields": [
                {"field": "config.ship_from.company", "label": "Company"},
                {"field": "config.ship_from.address", "label": "Address"},
            ]},
            {"title": "Consignee", "fields": [
                {"field": "config.ship_to.attention", "label": "Attn"},
                {"field": "config.ship_to.company", "label": "Company"},
                {"field": "config.ship_to.address", "label": "Address"},
            ]},
        ]},
        {"type": "meta_row", "fields": [
            {"field": "ida", "label": "BOL #"},
            {"field": "dt_created", "label": "Date", "format": "date"},
            {"field": "config.ship_via", "label": "Carrier"},
            {"field": "source.campaign_name", "label": "PO #"},
        ]},
        {"type": "line_items", "columns": [
            {"field": "item.ida_item", "label": "Item #", "width": "15%"},
            {"field": "item.description", "label": "Description", "width": "40%"},
            {"field": "quantity.active", "label": "Qty", "align": "right", "width": "10%"},
            {"field": "item.weight", "label": "Weight", "align": "right", "width": "12%"},
        ]},
        {"type": "signature", "blocks": [
            {"label": "Shipper", "lines": ["Signature", "Date"]},
            {"label": "Carrier", "lines": ["Signature", "Date"]},
            {"label": "Consignee", "lines": ["Signature", "Date"]},
        ]},
    ],
}

# ---------------------------------------------------------------------------
# Map: (model_name, report_name_pattern) → form layout
# Uses startswith matching so "Invoice - Standard" matches "Invoice -"
# ---------------------------------------------------------------------------

FORM_ASSIGNMENTS = [
    # Invoice forms
    ("invoice", "Invoice - Standard", INVOICE_FORM),
    ("invoice", "Invoice — Standard", INVOICE_FORM),
    ("invoice", "Standard Invoice", INVOICE_FORM),
    ("invoice", "Invoice - Shipping", INVOICE_SHIPPING_FORM),
    ("invoice", "Invoice — Shipping", INVOICE_SHIPPING_FORM),
    ("invoice", "Invoice - Shipping w/Disc", INVOICE_SHIPPING_FORM),
    ("invoice", "Invoice - PP Ship", INVOICE_SHIPPING_FORM),
    ("invoice", "Invoice - PP Standard", INVOICE_FORM),
    ("invoice", "Invoice - Foreign", INVOICE_FORM),
    ("invoice", "Invoice — Service", INVOICE_FORM),
    ("invoice", "Net Invoice", INVOICE_FORM),
    ("invoice", "Invoice Bill of Lading", BOL_FORM),
    ("invoice", "Invoice", INVOICE_FORM),  # catch-all bare "Invoice"
    # Credit memo
    ("invoice", "Credit Memo", CREDIT_MEMO_FORM),
    # Packing
    ("invoice", "Packing Slip", PACKING_SLIP_FORM),
    ("invoice", "Packing List with Load Items", PACKING_SLIP_FORM),
    ("order", "Packing Slip", PACKING_SLIP_FORM),
    # Proforma
    ("invoice", "Customs Proforma Invoice", INVOICE_FORM),
    ("order", "Proforma Invoice", INVOICE_FORM),
    # Order forms
    ("order", "Order Confirmation", ORDER_FORM),
    ("order", "Sales Order — Standard", ORDER_FORM),
    ("order", "Sales Order — Summary", ORDER_FORM),
    ("order", "Standard Order", ORDER_FORM),
    ("order", "Order - Two Address", ORDER_FORM),
    ("order", "Repair Order", ORDER_FORM),
    ("order", "Pick Ticket", PICK_TICKET_FORM),
    ("order", "Pick / Pull Request", PICK_TICKET_FORM),
    ("order", "Pick List", PICK_TICKET_FORM),
    ("order", "Bill of Lading", BOL_FORM),
    ("order", "Delivery Note", PACKING_SLIP_FORM),
    ("order", "Work Order Sheet", WORK_ORDER_FORM),
    ("order", "Work Order Confirmation", WORK_ORDER_FORM),
    # Proposal forms
    ("proposal", "Proposal 1", PROPOSAL_FORM),
    ("proposal", "Proposal 2", PROPOSAL_FORM),
    ("proposal", "Proposal 3", PROPOSAL_FORM),
    ("proposal", "Proposal 4", PROPOSAL_FORM),
    ("proposal", "Proposal / Quote", PROPOSAL_FORM),
    ("proposal", "Proposal/Quote — Standard", PROPOSAL_FORM),
    ("proposal", "Standard Proposal", PROPOSAL_FORM),
    ("proposal", "Proposal", PROPOSAL_FORM),
    ("proposal", "Customer Quote Form", PROPOSAL_FORM),
    ("proposal", "Estimate", PROPOSAL_FORM),
    ("proposal", "Bid Document", PROPOSAL_FORM),
    ("proposal", "Proposal as Proforma Invoice", INVOICE_FORM),
    # Purchase forms
    ("purchase", "Purchase Order", PURCHASE_ORDER_FORM),
    ("purchase", "Purchase Order — Standard", PURCHASE_ORDER_FORM),
    ("purchase", "Standard PO", PURCHASE_ORDER_FORM),
    ("purchase", "RFQ (Request for Quote)", PURCHASE_ORDER_FORM),
    ("purchase", "Receiving Report", RECEIVING_REPORT_FORM),
    ("purchase", "Receiving Report (GRN)", RECEIVING_REPORT_FORM),
    # Work order forms
    ("workorder", "Work Order", WORK_ORDER_FORM),
    ("work_order", "Work Order", WORK_ORDER_FORM),
    ("workorder", "WO Form (based on Order)", WORK_ORDER_FORM),
    ("work_order", "Service Report", WORK_ORDER_FORM),
    ("workorder", "Inventory Transfer WO", WORK_ORDER_FORM),
    # Payment
    ("payment", "Payment Receipt", PAYMENT_RECEIPT_FORM),
    # Statements
    ("customer", "Statement", STATEMENT_FORM),
    ("customer", "Customer Statement", STATEMENT_FORM),
    ("invoice", "Statement of Account", STATEMENT_FORM),
    ("invoice", "Customer Statement", STATEMENT_FORM),
    ("contact", "Statement", STATEMENT_FORM),
    # Receipt
    ("receipt", "Return Receipt", PAYMENT_RECEIPT_FORM),
]


def seed_report_forms(apps, schema_editor):
    Report = apps.get_model('core', 'Report')
    updated = 0
    for model_name, report_name, form in FORM_ASSIGNMENTS:
        reports = Report.objects.filter(
            model_name=model_name,
            name=report_name,
        )
        for report in reports:
            config = report.config or {}
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except Exception:
                    config = {}
            # Set the form layout, preserving other config keys
            config['form'] = form
            report.config = config
            report.save(update_fields=['config'])
            updated += 1
    print(f"  Updated {updated} Report records with form.json layouts")


def remove_report_forms(apps, schema_editor):
    Report = apps.get_model('core', 'Report')
    for report in Report.objects.exclude(config={}).exclude(config__isnull=True):
        config = report.config or {}
        if isinstance(config, dict) and 'form' in config:
            del config['form']
            report.config = config
            report.save(update_fields=['config'])


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0028_seed_print_templates'),
    ]
    operations = [
        migrations.RunPython(seed_report_forms, remove_report_forms),
    ]
