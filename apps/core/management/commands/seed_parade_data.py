"""
Seed sample data into Report.config.sample_data for the parade-of-reports.

Loops through all active print reports, loads the base sample JSON for
the report's model, customizes it for the specific report type, and
writes it to config.sample_data.

Usage:
    python manage.py seed_parade_data           # seed all
    python manage.py seed_parade_data --model invoice  # seed one model
    python manage.py seed_parade_data --dry-run # show what would be seeded
    python manage.py seed_parade_data --force   # overwrite existing sample_data
"""
import json
import copy
from pathlib import Path

from django.core.management.base import BaseCommand

SAMPLE_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "sample_data"


# ---------------------------------------------------------------------------
# Per-report customizations — keyed by report name patterns
# ---------------------------------------------------------------------------

def _customize_for_report(base_data: dict, report_name: str, model_name: str) -> dict:
    """Apply report-specific tweaks to the base sample data.

    The base data is a polished, realistic record for the model.
    Some reports need specific fields filled, labels changed, or
    lines adjusted to show the report's unique features.
    """
    data = copy.deepcopy(base_data)
    name_lower = report_name.lower()

    # ── Invoice variants ──
    if model_name == "invoice":
        if "credit" in name_lower or "memo" in name_lower:
            data["ida"] = "CM-2026-0103"
            data["status"] = "applied"
            # Make quantities and amounts negative for credit memo
            for ln in data.get("lines", []):
                qty = ln.get("quantity", {})
                if isinstance(qty, dict) and "active" in qty:
                    qty["active"] = -abs(qty["active"])
                price = ln.get("price", {})
                if isinstance(price, dict) and "extended" in price:
                    price["extended"] = -abs(price["extended"])
            totals = data.get("totals", {})
            if totals:
                for k in ("subtotal", "tax", "shipping", "total", "balance"):
                    if k in totals:
                        totals[k] = -abs(totals[k])

        elif "shipping" in name_lower or "ship" in name_lower:
            data.setdefault("config", {})["ship_via"] = "FedEx Freight"
            data["config"]["ship_date"] = 1785801600000
            data["config"]["tracking_number"] = "7489 3920 4831"
            data["config"]["weight_total"] = "247 lbs"

        elif "foreign" in name_lower or "international" in name_lower:
            data["attention"] = "Hans Mueller"
            data["company"] = "Werkzeug GmbH"
            data["address_full"] = "Industriestr. 42\n70173 Stuttgart\nGermany"
            data["phone"] = "+49 711 555 0188"
            data["email"] = "mueller@werkzeug-gmbh.de"
            data.setdefault("config", {})["currency"] = "EUR"
            data["config"]["incoterms"] = "FOB Origin"
            # Add international fields to lines
            for i, ln in enumerate(data.get("lines", [])):
                ln.setdefault("item", {})["country_of_origin"] = "US"
                ln["item"]["hs_code"] = f"8467.{11 + i:02d}.0000"

        elif "proforma" in name_lower or "customs" in name_lower:
            data["ida"] = "PI-2026-0047"
            data.setdefault("config", {})["incoterms"] = "CIF"
            data["config"]["currency"] = "USD"
            for i, ln in enumerate(data.get("lines", [])):
                ln.setdefault("item", {})["country_of_origin"] = "US"
                ln["item"]["hs_code"] = f"8467.{11 + i:02d}.0000"
                ln.setdefault("quantity", {}).setdefault("weight", 18.5 + i * 3)

        elif "bill of lading" in name_lower or "bol" in name_lower:
            data.setdefault("config", {})["ship_via"] = "Consolidated Freight"
            data["config"]["bol_number"] = "BOL-2026-9472"
            data["config"]["freight_class"] = "85"
            data["config"]["pieces"] = 4
            data["config"]["weight_total"] = "247 lbs"
            data["config"]["hazmat"] = False

        elif "net" in name_lower:
            # Net invoice — show cost and margin
            for ln in data.get("lines", []):
                ln.setdefault("cost", {})["unit"] = round(
                    ln.get("price", {}).get("unit", 0) * 0.6, 2
                )

        elif "paid by" in name_lower:
            data["status"] = "paid"
            data.setdefault("totals", {})["balance"] = 0
            data.setdefault("config", {})["payments"] = [
                {"ida": "PMT-2026-0512", "amount": 4263.35, "method": "Check #4892",
                 "date": "2026-07-15"},
            ]

        elif "daily" in name_lower:
            data["_list_mode"] = True  # hint that this is a list report

        elif "commission" in name_lower or "comm" in name_lower:
            data.setdefault("config", {})["rep_name"] = "Tom Hargrove"
            data["config"]["commission_rate"] = 0.05
            for ln in data.get("lines", []):
                ext = ln.get("price", {}).get("extended", 0)
                ln.setdefault("commission", {})["rate"] = 0.05
                ln["commission"]["amount"] = round(ext * 0.05, 2)

        elif "service" in name_lower:
            data["lines"] = [
                {
                    "line_number": 1,
                    "item": {"ida_item": "SVC-INSTALL", "description": "On-site installation labor", "uom": "Hour"},
                    "quantity": {"active": 8},
                    "price": {"unit": 125.00, "extended": 1000.00},
                },
                {
                    "line_number": 2,
                    "item": {"ida_item": "SVC-TRAVEL", "description": "Travel — round trip", "uom": "Trip"},
                    "quantity": {"active": 1},
                    "price": {"unit": 175.00, "extended": 175.00},
                },
                {
                    "line_number": 3,
                    "item": {"ida_item": "MAT-WIRE-14", "description": "14/2 NM-B Romex, 250ft", "uom": "Roll"},
                    "quantity": {"active": 2},
                    "price": {"unit": 89.50, "extended": 179.00},
                },
            ]
            data["totals"] = {"subtotal": 1354.00, "tax": 12.07, "shipping": 0, "total": 1366.07, "balance": 1366.07}

    # ── Order variants ──
    elif model_name == "order":
        if "pick" in name_lower:
            # Pick ticket — add bin locations, remove pricing
            for ln in data.get("lines", []):
                ln.setdefault("item", {})["bin_location"] = f"A-{ln.get('line_number', 1):02d}-3"
                ln.get("price", {}).pop("unit", None)
                ln.get("price", {}).pop("extended", None)

        elif "packing" in name_lower:
            # Packing slip — no prices, add weight
            for ln in data.get("lines", []):
                ln.get("price", {}).pop("unit", None)
                ln.get("price", {}).pop("extended", None)
                ln.get("price", {}).pop("discount_percent", None)
                ln.setdefault("item", {}).setdefault("weight", "12.5 lbs")

        elif "work order" in name_lower or "wo " in name_lower:
            data["ida"] = "WO-2026-0389"
            data.setdefault("config", {})["assigned_to"] = "Tony Reyes"
            data["config"]["due_date"] = 1786060800000
            data["config"]["priority"] = "Normal"
            data["config"]["instructions"] = "Install per drawing rev C. Customer on-site during install."

        elif "bill of lading" in name_lower or "bol" in name_lower:
            data.setdefault("config", {})["bol_number"] = "BOL-2026-8741"
            data["config"]["carrier"] = "ABF Freight"
            data["config"]["pro_number"] = "PRO-5529841"

        elif "backorder" in name_lower or "back order" in name_lower:
            data["status"] = "backordered"
            for ln in data.get("lines", []):
                qty = ln.get("quantity", {})
                ordered = qty.get("active", 10)
                qty["shipped"] = int(ordered * 0.6)
                qty["backordered"] = ordered - qty["shipped"]

        elif "delivery" in name_lower:
            data.setdefault("config", {})["delivery_window"] = "Mon-Fri 7am-3pm"
            data["config"]["requires_signature"] = True

        elif "embroidery" in name_lower:
            data["lines"] = [
                {
                    "line_number": 1,
                    "item": {"ida_item": "EMB-POLO-BLK-M", "description": "Polo Shirt, Black, Medium — embroidered", "uom": "Each"},
                    "quantity": {"active": 24},
                    "price": {"unit": 32.00, "extended": 768.00},
                },
                {
                    "line_number": 2,
                    "item": {"ida_item": "EMB-POLO-BLK-L", "description": "Polo Shirt, Black, Large — embroidered", "uom": "Each"},
                    "quantity": {"active": 36},
                    "price": {"unit": 32.00, "extended": 1152.00},
                },
            ]
            data.setdefault("config", {})["embroidery"] = {
                "logo": "Ridgeline Hardware",
                "position": "Left chest",
                "thread_colors": ["White", "Red"],
                "stitch_count": 8500,
            }

        elif "repair" in name_lower:
            data["ida"] = "RO-2026-0112"
            data.setdefault("config", {})["equipment"] = "DeWalt DW735X Planer"
            data["config"]["serial_number"] = "DW735X-20240818-7294"
            data["config"]["problem_description"] = "Snipe on last 2 inches of board. Knife marks visible."

        elif "schedule" in name_lower:
            data.setdefault("config", {})["schedule_date"] = 1786060800000
            data["config"]["time_slot"] = "AM"

    # ── Purchase variants ──
    elif model_name == "purchase":
        if "blanket" in name_lower:
            data["ida"] = "BPO-2026-0021"
            data.setdefault("config", {})["blanket_total"] = 50000.00
            data["config"]["release_schedule"] = "Monthly"
            data["config"]["expires"] = 1801526400000  # 12 months out

        elif "receiving" in name_lower or "grn" in name_lower or "receipt" in name_lower:
            data.setdefault("config", {})["received_by"] = "Bay 3 — Carlos"
            data["config"]["received_date"] = 1785888000000
            for ln in data.get("lines", []):
                qty = ln.get("quantity", {})
                qty["received"] = qty.get("active", 0)
                qty["damaged"] = 0

        elif "rfq" in name_lower or "request for quote" in name_lower:
            data["ida"] = "RFQ-2026-0088"
            data["status"] = "sent"
            data.setdefault("config", {})["respond_by"] = 1786320000000
            # Remove pricing for RFQ
            for ln in data.get("lines", []):
                ln.get("price", {}).pop("unit", None)
                ln.get("price", {}).pop("extended", None)
                ln.get("price", {}).pop("discount_percent", None)

        elif "variance" in name_lower:
            for ln in data.get("lines", []):
                price = ln.get("price", {})
                price["po_unit"] = price.get("unit", 0)
                price["actual_unit"] = round(price.get("unit", 0) * 1.03, 2)  # 3% over
                price["variance"] = round(price["actual_unit"] - price["po_unit"], 2)

        elif "scorecard" in name_lower:
            data.setdefault("config", {})["scorecard"] = {
                "on_time_delivery": 0.92,
                "quality_rating": 0.97,
                "price_competitiveness": 0.88,
                "overall_score": 0.92,
                "period_days": 90,
            }

    # ── Payment variants ──
    elif model_name == "payment":
        if "receipt" in name_lower:
            pass  # base data is fine for receipt
        elif "journal" in name_lower:
            data["_list_mode"] = True
        elif "deposit" in name_lower:
            data.setdefault("config", {})["deposit_date"] = 1785801600000
            data["config"]["bank_account"] = "Operating — ****4821"
        elif "disbursement" in name_lower:
            data["ida"] = "DSB-2026-0294"
            data.setdefault("config", {})["payment_method"] = "ACH"
            data["config"]["check_number"] = ""
            data["totals"]["total"] = -3200.00  # outbound
        elif "reconciliation" in name_lower:
            data.setdefault("config", {})["bank_statement_date"] = "2026-07-31"
            data["config"]["bank_balance"] = 47892.15
            data["config"]["book_balance"] = 48102.35
            data["config"]["outstanding_checks"] = 210.20
        elif "refund" in name_lower:
            data["ida"] = "REF-2026-0019"
            data["totals"]["total"] = -425.00
            data.setdefault("config", {})["reason"] = "Returned merchandise — defective"
        elif "cash flow" in name_lower:
            data["_list_mode"] = True

    # ── Proposal variants ──
    elif model_name == "proposal":
        if "bid" in name_lower:
            data["ida"] = "BID-2026-0034"
            data.setdefault("config", {})["bid_deadline"] = 1787616000000
            data["config"]["bond_required"] = True
        elif "proforma" in name_lower:
            data["ida"] = "PI-2026-0067"
        elif "checklist" in name_lower:
            data.setdefault("config", {})["checklist"] = [
                {"item": "Site survey complete", "checked": True},
                {"item": "Permits applied for", "checked": False},
                {"item": "Materials ordered", "checked": False},
                {"item": "Customer deposit received", "checked": True},
                {"item": "Schedule confirmed", "checked": False},
            ]
        elif "follow-up" in name_lower or "followup" in name_lower:
            data["_list_mode"] = True
        elif "conversion" in name_lower:
            data["_list_mode"] = True

    # ── Contact variants ──
    elif model_name in ("contact", "customer"):
        if "aging" in name_lower or "receivable" in name_lower or "ar " in name_lower:
            data.setdefault("totals", {})["current"] = 4263.35
            data["totals"]["over_30"] = 3577.85
            data["totals"]["over_60"] = 1892.40
            data["totals"]["over_90"] = 0.00
        elif "profitability" in name_lower:
            data.setdefault("totals", {})["gross_margin"] = 0.38
            data["totals"]["contribution_margin"] = 12450.00
        elif "statement" in name_lower:
            # Use the statement sample data instead
            stmt_file = SAMPLE_DATA_DIR / "statement.json"
            if stmt_file.exists():
                stmt = json.loads(stmt_file.read_text())
                stmt.pop("_meta", None)
                return stmt
        elif "overdue" in name_lower or "past due" in name_lower:
            data.setdefault("config", {})["days_overdue"] = 45
            data["config"]["overdue_amount"] = 5470.25
        elif "call list" in name_lower:
            data["_list_mode"] = True

    # ── Vendor variants ──
    elif model_name == "vendor":
        data["ida"] = "MTD-56"
        data["attention"] = "Accounts Receivable"
        data["company"] = "Milwaukee Tool Distribution"
        data["address_full"] = "13135 W Lisbon Rd\nBrookfield, WI 53005"
        data["phone"] = "(800) 555-0462"
        data["email"] = "orders@milwaukeetool-dist.com"
        data["terms"] = "2% 10 Net 30"
        if "scorecard" in name_lower:
            data.setdefault("config", {})["scorecard"] = {
                "on_time_delivery": 0.92, "quality_rating": 0.97,
                "price_competitiveness": 0.88, "overall_score": 0.92,
            }
        elif "aging" in name_lower or "ap " in name_lower:
            data.setdefault("totals", {})["current"] = 12805.00
            data["totals"]["over_30"] = 0
            data["totals"]["over_60"] = 0

    # ── Item variants ──
    elif model_name == "item":
        if "price list" in name_lower:
            data["_list_mode"] = True
        elif "reorder" in name_lower:
            data["totals"]["on_hand"] = 3  # below reorder point of 5
            data["totals"]["available"] = -2
        elif "bom" in name_lower or "bill of material" in name_lower:
            data.setdefault("config", {})["bom"] = [
                {"item": "DW735-BLADE", "description": "Replacement Knife Set", "qty": 3, "uom": "Set"},
                {"item": "DW735-BELT", "description": "Drive Belt", "qty": 1, "uom": "Each"},
                {"item": "DW735-DUST", "description": "Dust Collection Adapter", "qty": 1, "uom": "Each"},
            ]
        elif "margin" in name_lower or "velocity" in name_lower:
            data.setdefault("config", {})["margin_velocity"] = {
                "margin_pct": 0.29, "turns_per_year": 4.8,
                "carry_cost_pct": 0.18, "velocity_score": 7.73,
            }

    # ── GL / Accounting ──
    elif model_name in ("gl_journal", "gl_account", "ledger"):
        data = {
            "ida": "JE-2026-07-001",
            "status": "posted",
            "dt_created": 1785715200000,
            "description": "Monthly sales accrual — July 2026",
            "lines": [
                {"account": "1200 — Accounts Receivable", "debit": 4263.35, "credit": 0},
                {"account": "4100 — Sales Revenue", "debit": 0, "credit": 3847.50},
                {"account": "2100 — Sales Tax Payable", "debit": 0, "credit": 230.85},
                {"account": "4200 — Shipping Income", "debit": 0, "credit": 185.00},
            ],
            "totals": {"total_debits": 4263.35, "total_credits": 4263.35},
            "refs": {"links": {"contact": {"id": 142, "name": "Ridgeline Hardware & Supply"}}},
        }
        if "trial balance" in name_lower:
            data["_list_mode"] = True
        elif "chart" in name_lower:
            data["_list_mode"] = True

    # ── Work order ──
    elif model_name in ("work_order", "workorder"):
        data = {
            "ida": "WO-2026-0389",
            "status": "in_progress",
            "dt_created": 1785542400000,
            "attention": "Tony Reyes",
            "company": "Pacific Coast Building Materials",
            "address_full": "2100 Main Street\nAlameda, CA 94501",
            "phone": "(510) 555-0341",
            "config": {
                "assigned_to": "Tony Reyes",
                "due_date": 1786060800000,
                "priority": "Normal",
                "equipment": "Jobsite — Alameda Point Phase 2",
                "instructions": "Install per drawing rev C. Customer on-site during install.",
            },
            "lines": [
                {"line_number": 1, "item": {"ida_item": "LABOR-INSTALL", "description": "Installation labor", "uom": "Hour"}, "quantity": {"active": 16, "completed": 8}, "price": {"unit": 95.00, "extended": 1520.00}},
                {"line_number": 2, "item": {"ida_item": "MAT-BRACKET", "description": "Steel mounting brackets", "uom": "Each"}, "quantity": {"active": 24, "completed": 24}, "price": {"unit": 12.50, "extended": 300.00}},
                {"line_number": 3, "item": {"ida_item": "MAT-BOLT-SS", "description": "Stainless hex bolts 3/8x2", "uom": "Box/50"}, "quantity": {"active": 4, "completed": 2}, "price": {"unit": 34.00, "extended": 136.00}},
            ],
            "totals": {"subtotal": 1956.00, "tax": 0, "total": 1956.00},
            "refs": {"links": {"contact": {"id": 287, "name": "Pacific Coast Building Materials"}}},
        }
        if "job cost" in name_lower:
            data["config"]["labor_cost"] = 1520.00
            data["config"]["material_cost"] = 436.00
            data["config"]["overhead"] = 195.60
            data["config"]["total_cost"] = 2151.60
            data["config"]["revenue"] = 2800.00
            data["config"]["margin"] = 0.232

    # ── Warehouse / inventory ──
    elif model_name in ("warehouse", "inventory", "inventory_layer"):
        item_data = _load_base("item")
        if item_data:
            data = item_data
        data.setdefault("config", {})["warehouse"] = "Main — Portland"
        if "count" in name_lower or "cycle" in name_lower:
            data["config"]["count_date"] = "2026-07-31"
            data["config"]["counted_by"] = "Carlos M."

    # ── Employee ──
    elif model_name == "employee":
        data = {
            "ida": "EMP-0024",
            "attention": "Karen Bell",
            "company": "",
            "address_full": "1847 Oak Lane\nPortland, OR 97209",
            "phone": "(503) 555-0188",
            "email": "karen.bell@company.com",
            "config": {
                "department": "Sales",
                "title": "Regional Sales Manager",
                "hire_date": "2019-03-15",
                "territory": "Pacific Northwest",
            },
        }

    # ── Serial ──
    elif model_name == "serial":
        data = {
            "ida": "DW735X-20240818-7294",
            "status": "active",
            "dt_created": 1743552000000,
            "config": {
                "item_ida": "DW-735X",
                "item_description": "DeWalt 13\" Three Knife Two-Speed Planer",
                "warranty_months": 36,
                "warranty_expires": "2027-08-18",
                "customer": "Ridgeline Hardware & Supply",
            },
        }

    # ── Action / Project ──
    elif model_name in ("action", "project"):
        data = {
            "ida": "ACT-2026-0847",
            "status": "open",
            "dt_created": 1785542400000,
            "attention": "Bill James",
            "description": "Review Q3 pricing strategy with Milwaukee rep",
            "config": {
                "due_date": 1786060800000,
                "priority": "Normal",
                "assigned_to": "Karen Bell",
                "project": "Vendor Relations",
                "category": "Sales",
            },
        }

    # ── Document ──
    elif model_name == "document":
        data = {
            "ida": "DOC-2026-0392",
            "status": "active",
            "dt_created": 1785542400000,
            "description": "Q3 Pricing Agreement — Milwaukee Tool",
            "config": {
                "document_type": "agreement",
                "effective_date": "2026-07-01",
                "expiration_date": "2026-09-30",
            },
        }

    # ── Campaign ──
    elif model_name == "campaign":
        data = {
            "ida": "CMP-2026-HOMESHOW",
            "status": "active",
            "dt_created": 1780358400000,
            "description": "2026 Home & Garden Show — Charlotte Convention Center",
            "config": {
                "channel": "Trade Show",
                "budget": 15000.00,
                "spend_to_date": 12450.00,
                "start_date": "2026-03-15",
                "end_date": "2026-03-17",
            },
            "totals": {
                "leads": 142,
                "conversions": 23,
                "revenue": 48720.00,
                "roi": 2.25,
                "cac": 541.30,
            },
        }

    # ── Question/Answer ──
    elif model_name == "question_answer":
        data = {
            "ida": "QA-2026-0088",
            "status": "complete",
            "dt_created": 1785542400000,
            "description": "Installation inspection — Alameda Point Phase 2",
            "config": {
                "inspector": "Tom Hargrove",
                "inspection_date": "2026-07-15",
                "questions": [
                    {"q": "Mounting brackets torqued to spec?", "a": "Yes", "pass": True},
                    {"q": "Grounding wire connected?", "a": "Yes", "pass": True},
                    {"q": "Safety shield in place?", "a": "No — ordered replacement", "pass": False},
                    {"q": "Test run completed?", "a": "Yes — 15 min at full speed", "pass": True},
                ],
            },
        }

    # ── Tax jurisdiction ──
    elif model_name == "tax_jurisdiction":
        data = {
            "ida": "TAX-VT-001",
            "description": "Vermont — State Sales Tax",
            "config": {
                "jurisdiction": "Vermont",
                "rate": 0.06,
                "effective_date": "2024-01-01",
                "type": "state",
            },
        }

    # ── Rep ──
    elif model_name == "rep":
        data = {
            "ida": "REP-TH",
            "attention": "Tom Hargrove",
            "config": {
                "territory": "New England",
                "commission_rate": 0.05,
                "ytd_sales": 287450.00,
                "ytd_commission": 14372.50,
            },
        }

    # ── Bill of Material ──
    elif model_name == "bill_of_material":
        item_data = _load_base("item")
        if item_data:
            data = item_data
        data.setdefault("config", {})["bom"] = [
            {"item": "DW735-BLADE", "description": "Replacement Knife Set (3 pk)", "qty": 1, "uom": "Set", "cost": 45.00},
            {"item": "DW735-TABLE-IN", "description": "Infeed/Outfeed Table Set", "qty": 1, "uom": "Set", "cost": 89.00},
            {"item": "DW735-DUST", "description": "Dust Collection Adapter", "qty": 1, "uom": "Each", "cost": 24.00},
            {"item": "DW735-BELT", "description": "Drive Belt", "qty": 1, "uom": "Each", "cost": 18.50},
        ]

    # ── Requisition ──
    elif model_name == "requisition":
        data = {
            "ida": "REQ-2026-0147",
            "status": "approved",
            "dt_created": 1785542400000,
            "attention": "Carlos Martinez",
            "description": "Restock request — power tool batteries",
            "config": {
                "department": "Warehouse",
                "approved_by": "Karen Bell",
                "approved_date": 1785628800000,
            },
            "lines": [
                {"line_number": 1, "item": {"ida_item": "MIL-48-11-1850", "description": "M18 REDLITHIUM XC5.0 Battery 2-Pack"}, "quantity": {"active": 12}},
                {"line_number": 2, "item": {"ida_item": "MIL-48-11-2450", "description": "M12 REDLITHIUM XC4.0 Battery 2-Pack"}, "quantity": {"active": 8}},
            ],
        }

    # ── Receipt ──
    elif model_name == "receipt":
        data = {
            "ida": "RCV-2026-0203",
            "status": "received",
            "dt_created": 1785888000000,
            "company": "Milwaukee Tool Distribution",
            "config": {
                "po_reference": "PO-2026-0394",
                "received_by": "Carlos Martinez",
                "carrier": "UPS Freight",
                "condition": "Good — no damage noted",
            },
            "lines": [
                {"line_number": 1, "item": {"ida_item": "MIL-2804-22", "description": "M18 FUEL 1/2\" Hammer Drill/Driver Kit"}, "quantity": {"active": 12, "received": 12, "damaged": 0}},
                {"line_number": 2, "item": {"ida_item": "MIL-48-22-8426", "description": "PACKOUT Rolling Tool Box"}, "quantity": {"active": 15, "received": 14, "damaged": 1}},
            ],
        }

    return data


def _load_base(model_name: str) -> dict | None:
    """Load the base sample JSON file for a model, if it exists."""
    # Map variant model names to base files
    MODEL_MAP = {
        "customer": "contact",
        "vendor": "contact",
        "invoice_line": "invoice",
        "order_line": "order",
        "work_order": "order",
        "workorder": "order",
        "inventory": "item",
        "inventory_layer": "item",
        "bill_of_material": "item",
    }
    file_model = MODEL_MAP.get(model_name, model_name)
    path = SAMPLE_DATA_DIR / f"{file_model}.json"
    if path.exists():
        data = json.loads(path.read_text())
        data.pop("_meta", None)
        return data
    return None


class Command(BaseCommand):
    help = "Seed Report.config.sample_data for parade-of-reports onboarding"

    def add_arguments(self, parser):
        parser.add_argument("--model", type=str, help="Only seed reports for this model_name")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be seeded")
        parser.add_argument("--force", action="store_true", help="Overwrite existing sample_data")

    def handle(self, *args, **options):
        from apps.core.models import Report

        qs = Report.objects.filter(is_active=True, is_deleted=False, output_type="print")
        if options["model"]:
            qs = qs.filter(model_name=options["model"])
        qs = qs.order_by("model_name", "sort_order", "name")

        seeded = 0
        skipped = 0
        no_base = 0

        for report in qs:
            model = report.model_name or ""
            config = report.config or {}

            # Skip if already has sample_data and not forcing
            if config.get("sample_data") and not options["force"]:
                skipped += 1
                if options["dry_run"]:
                    self.stdout.write(f"  SKIP  [{report.id}] {report.name} ({model}) — already has sample_data")
                continue

            # Load base data
            base = _load_base(model)
            if base is None:
                # Create minimal fallback
                base = {
                    "ida": f"SAMPLE-{model.upper()}-001",
                    "status": "active",
                    "dt_created": 1785542400000,
                    "description": f"Sample {model} record",
                }

            # Customize for this specific report
            sample = _customize_for_report(base, report.name, model)

            if options["dry_run"]:
                lines = len(sample.get("lines", []))
                self.stdout.write(
                    f"  SEED  [{report.id}] {report.name} ({model}) "
                    f"— {len(json.dumps(sample))} bytes, {lines} lines"
                )
            else:
                config["sample_data"] = sample
                report.config = config
                report.save(update_fields=["config", "dt_modified"])

            seeded += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n{'Would seed' if options['dry_run'] else 'Seeded'}: {seeded}  "
            f"Skipped (existing): {skipped}  "
            f"No base data: {no_base}"
        ))
