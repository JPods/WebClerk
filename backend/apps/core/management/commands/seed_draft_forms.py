"""Draft layouts for print reports that have none.

Of 69 print reports, 13 carried a form layout. The rest pointed at a template name
that nothing defines. This command drafts layouts for the ones whose model already
has sample data, in the same section vocabulary the existing MVP forms use:

    company_header · meta_row · address_blocks · detail_fields · line_items
    data_table · comments · totals · conditions · signature · footer

Every layout here is marked ``"draft": true``. They exist to be judged in the Form
Parade — Keep, Modify or Don't Need — not to be trusted. A draft that nobody keeps
should be deleted along with its report.

    python manage.py seed_draft_forms            # only reports with no layout
    python manage.py seed_draft_forms --force    # overwrite existing drafts
    python manage.py seed_draft_forms --list     # show what would be drafted
"""
from django.core.management.base import BaseCommand

from apps.core.models import Report


def company_header(address=True, contact=True):
    return {"type": "company_header", "logo": True,
            "show_address": address, "show_contact": contact}


def meta_row(*pairs):
    return {"type": "meta_row",
            "fields": [{"field": f, "label": l, **(x or {})} for f, l, *rest in pairs
                       for x in [rest[0] if rest else {}]]}


def bill_ship():
    return {"type": "address_blocks", "columns": [
        {"title": "Bill To", "fields": [
            {"field": "company", "label": "Company"},
            {"field": "attention", "label": "Attn"},
            {"field": "address_full", "label": "Address"},
        ]},
        {"title": "Ship To", "fields": [
            {"field": "config.ship_to.company", "label": "Company"},
            {"field": "config.ship_to.attention", "label": "Attn"},
            {"field": "config.ship_to.address", "label": "Address"},
        ]},
    ]}


def sold_to():
    return {"type": "address_blocks", "columns": [
        {"title": "To", "fields": [
            {"field": "company", "label": "Company"},
            {"field": "attention", "label": "Attn"},
            {"field": "address_full", "label": "Address"},
            {"field": "phone", "label": "Phone"},
        ]},
    ]}


def priced_lines(qty_field="quantity.active", show_totals=True):
    return {"type": "line_items", "show_footer_totals": show_totals, "columns": [
        {"field": "item.ida_item", "label": "Item #", "align": "left", "width": "18%"},
        {"field": "item.description", "label": "Description", "align": "left", "width": "42%"},
        {"field": qty_field, "label": "Qty", "align": "right", "format": "number"},
        {"field": "price.unit", "label": "Unit", "align": "right", "format": "currency"},
        {"field": "totals.amount", "label": "Amount", "align": "right", "format": "currency"},
    ]}


def totals(kind="full"):
    rows = [{"field": "totals.amount", "label": "Subtotal", "format": "currency"}]
    if kind == "full":
        rows += [
            {"field": "totals.tax", "label": "Tax", "format": "currency"},
            {"field": "totals.shipping", "label": "Shipping", "format": "currency"},
        ]
    rows += [{"field": "totals.total", "label": "Total", "format": "currency", "emphasis": True}]
    return {"type": "totals", "rows": rows}


def conditions():
    return {"type": "conditions", "field": "conditions_description", "label": "Terms and Conditions"}


def signature(*labels):
    return {"type": "signature", "blocks": [{"label": l} for l in labels]}


def footer(*fields):
    return {"type": "footer", "fields": [{"field": f, "label": l} for f, l in fields]}


# ── the drafts ───────────────────────────────────────────────────────────────
# ida → (model, paper title, sections)

DRAFTS = {
    # ---- order ----
    "482": ("order", "Pick / Pull Request", [
        company_header(address=False, contact=False),
        meta_row(("ida", "Order #"), ("company", "Customer"),
                 ("dt_created", "Date", {"format": "date"}),
                 ("config.ship_via", "Ship Via")),
        {"type": "address_blocks", "columns": [
            {"title": "Pull For", "fields": [
                {"field": "config.ship_to.company", "label": "Company"},
                {"field": "config.ship_to.address", "label": "Address"},
                {"field": "config.ship_date", "label": "Needed", "format": "date"},
            ]},
        ]},
        {"type": "line_items", "show_footer_totals": False, "columns": [
            {"field": "item.ida_item", "label": "Item #", "align": "left", "width": "20%"},
            {"field": "item.description", "label": "Description", "align": "left", "width": "40%"},
            {"field": "item.uom", "label": "Unit", "align": "left", "width": "10%"},
            {"field": "quantity.active", "label": "Requested", "align": "right", "format": "number"},
            {"field": "item.bin", "label": "Bin", "align": "left", "width": "12%"},
        ]},
        {"type": "comments", "source": "comments.shipping", "label": "Handling"},
        signature("Pulled by", "Checked by"),
        footer(("ida", "Order #")),
    ]),
    "483": ("order", "Proforma Invoice", [
        company_header(),
        meta_row(("ida", "Proforma #"), ("dt_created", "Date", {"format": "date"}),
                 ("terms", "Terms"), ("config.ship_via", "Ship Via")),
        bill_ship(),
        priced_lines(),
        totals(),
        {"type": "detail_fields", "fields": [
            {"field": "source.campaign_name", "label": "Reference"},
        ]},
        conditions(),
        footer(("ida", "Proforma #")),
    ]),

    # ---- invoice ----
    "487": ("invoice", "Past Due Notice", [
        company_header(),
        meta_row(("ida", "Invoice #"), ("dt_created", "Invoice Date", {"format": "date"}),
                 ("terms", "Terms"), ("status", "Status")),
        sold_to(),
        {"type": "detail_fields", "fields": [
            {"field": "totals.total", "label": "Amount invoiced", "format": "currency"},
            {"field": "totals.balance", "label": "Amount still due", "format": "currency"},
        ]},
        priced_lines(show_totals=False),
        totals(),
        {"type": "comments", "source": "comments.public", "label": "Note"},
        conditions(),
        footer(("ida", "Invoice #")),
    ]),

    # ---- quote ----
    "490": ("quote", "Quote / Quote", [
        company_header(),
        meta_row(("ida", "Quote #"), ("dt_created", "Date", {"format": "date"}),
                 ("config.valid_until", "Valid Until", {"format": "date"}),
                 ("config.salesperson", "Prepared By")),
        sold_to(),
        {"type": "detail_fields", "fields": [
            {"field": "config.project_name", "label": "Project"},
            {"field": "price_level", "label": "Price level"},
        ]},
        priced_lines(),
        totals(),
        {"type": "comments", "source": "comments.public", "label": "Notes"},
        conditions(),
        signature("Accepted by", "Date"),
        footer(("ida", "Quote #")),
    ]),
    "491": ("quote", "Estimate", [
        company_header(contact=False),
        meta_row(("ida", "Estimate #"), ("dt_created", "Date", {"format": "date"}),
                 ("config.valid_until", "Valid Until", {"format": "date"})),
        sold_to(),
        priced_lines(),
        totals(kind="short"),
        {"type": "comments", "source": "comments.public", "label": "Assumptions"},
        footer(("ida", "Estimate #")),
    ]),
    "492": ("quote", "Bid Document", [
        company_header(),
        meta_row(("ida", "Bid #"), ("dt_created", "Date", {"format": "date"}),
                 ("config.project_name", "Project"),
                 ("config.valid_until", "Bid Valid Until", {"format": "date"})),
        sold_to(),
        {"type": "detail_fields", "fields": [
            {"field": "config.salesperson", "label": "Bid prepared by"},
            {"field": "terms", "label": "Payment terms"},
        ]},
        priced_lines(),
        totals(),
        conditions(),
        signature("Authorized signature", "Date", "Title"),
        footer(("ida", "Bid #")),
    ]),

    # ---- work order ----
    "496": ("workorder", "Service Report", [
        company_header(),
        meta_row(("ida", "Work Order #"), ("dt_created", "Date", {"format": "date"}),
                 ("company", "Customer"), ("status", "Status")),
        sold_to(),
        {"type": "detail_fields", "fields": [
            {"field": "description", "label": "Work performed"},
        ]},
        {"type": "line_items", "show_footer_totals": False, "columns": [
            {"field": "item.ida_item", "label": "Part / Task", "align": "left", "width": "20%"},
            {"field": "item.category", "label": "Type", "align": "left", "width": "16%"},
            {"field": "item.description", "label": "Description", "align": "left", "width": "44%"},
            {"field": "quantity.staged", "label": "Qty / Hrs", "align": "right", "format": "number"},
        ]},
        {"type": "comments", "source": "comments.public", "label": "Technician notes"},
        signature("Technician", "Customer acceptance"),
        footer(("ida", "Work Order #")),
    ]),
    "497": ("workorder", "Time & Materials Summary", [
        company_header(contact=False),
        meta_row(("ida", "Work Order #"), ("company", "Customer"),
                 ("dt_created", "Date", {"format": "date"})),
        {"type": "data_table", "grand_totals": True, "columns": [
            {"field": "item.ida_item", "label": "Item", "align": "left", "width": "20%"},
            {"field": "item.description", "label": "Description", "align": "left", "width": "44%"},
            {"field": "quantity.staged", "label": "Qty / Hrs", "align": "right", "format": "number"},
            {"field": "cost.unit", "label": "Rate", "align": "right", "format": "currency"},
            {"field": "totals.cost", "label": "Amount", "align": "right", "format": "currency"},
        ]},
        {"type": "detail_fields", "fields": [
            {"field": "description", "label": "Scope"},
        ]},
        footer(("ida", "Work Order #")),
    ]),

    # ---- cash ----
    "524": ("cash", "Cash Journal", [
        company_header(address=False),
        meta_row(("ida", "Entry #"), ("dt_created", "Date", {"format": "date"}),
                 ("status", "Status")),
        {"type": "data_table", "grand_totals": True, "columns": [
            {"field": "item.ida_item", "label": "Account", "align": "left", "width": "22%"},
            {"field": "item.description", "label": "Description", "align": "left", "width": "46%"},
            {"field": "totals.amount", "label": "Amount", "align": "right", "format": "currency"},
        ]},
        totals(kind="short"),
        footer(("ida", "Entry #")),
    ]),
    "525": ("cash", "Disbursement Report", [
        company_header(address=False),
        meta_row(("ida", "Reference"), ("dt_created", "Date", {"format": "date"}),
                 ("company", "Paid To")),
        {"type": "data_table", "grand_totals": True, "columns": [
            {"field": "item.ida_item", "label": "Account", "align": "left", "width": "22%"},
            {"field": "item.description", "label": "Description", "align": "left", "width": "46%"},
            {"field": "totals.amount", "label": "Amount", "align": "right", "format": "currency"},
        ]},
        {"type": "comments", "source": "comments.public", "label": "Note"},
        footer(("ida", "Reference")),
    ]),

    # ---- item ----
    "506": ("item", "Product Spec Sheet", [
        company_header(),
        meta_row(("ida_item", "Item #"), ("uom", "Unit"), ("status", "Status")),
        {"type": "detail_fields", "fields": [
            {"field": "description", "label": "Description"},
            {"field": "long_description", "label": "Detail"},
            {"field": "sell.price", "label": "List price", "format": "currency"},
            {"field": "config.weight", "label": "Weight"},
            {"field": "config.dimensions", "label": "Dimensions"},
        ]},
        footer(("ida_item", "Item #")),
    ]),
    "507": ("item", "Price List", [
        company_header(contact=False),
        meta_row(("dt_created", "As of", {"format": "date"})),
        {"type": "detail_fields", "fields": [
            {"field": "ida_item", "label": "Item #"},
            {"field": "description", "label": "Description"},
            {"field": "uom", "label": "Unit"},
            {"field": "sell.price", "label": "Price", "format": "currency"},
        ]},
        footer(("ida_item", "Item #")),
    ]),
}


class Command(BaseCommand):
    help = "Draft form layouts for print reports that have none"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true",
                            help="Replace a layout that is already there")
        parser.add_argument("--list", action="store_true",
                            help="Show what would be drafted and stop")

    def handle(self, *args, **options):
        if options["list"]:
            for ida, (model, title, sections) in DRAFTS.items():
                report = Report.objects.filter(ida=ida).first()
                state = "missing report" if not report else (
                    "has layout" if (report.config or {}).get("form") else "no layout")
                self.stdout.write(f"  {ida:20} {title:28} {model:10} {state}")
            return

        drafted = skipped = missing = 0
        for ida, (model, title, sections) in DRAFTS.items():
            report = Report.objects.filter(ida=ida).first()
            if not report:
                self.stdout.write(self.style.WARNING(f"  {ida}: no such report"))
                missing += 1
                continue

            config = report.config or {}
            if config.get("form") and not options["force"]:
                skipped += 1
                continue

            config["form"] = {
                "model": model,
                "title": title,
                "paper": "letter",
                "draft": True,
                "sections": sections,
            }
            report.config = config
            report.explanation = (report.explanation or "").strip() or (
                f"Draft layout — {title} rendered from {model} sample data. "
                "Judge it in the Form Parade: Keep, Modify or Don't Need."
            )
            report.save()
            drafted += 1
            self.stdout.write(self.style.SUCCESS(f"  {ida}: drafted {title}"))

        self.stdout.write(
            f"Drafts: {drafted} written, {skipped} left alone, {missing} reports missing")
