"""
seed_demo_transactions — Seed full transaction cycles for demo/training.

Usage:
    python manage.py seed_demo_transactions
    python manage.py seed_demo_transactions --force   # delete and re-seed

Creates 3 complete transaction cycles (proposal → order → invoice → payment → GL)
using the items, customers, and contacts created by seed_demo.

All demo records are tagged refs.source="demo-baseline" for clean removal.
Prerequisites: seed_demo must have run first (items, orgs, contacts required).
"""
from decimal import Decimal
from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.transactions.models import (
    Proposal, ProposalLine,
    Order, OrderLine,
    Invoice, InvoiceLine,
    Payment,
)
from apps.accounts.models import GlJournal
from apps.products.models import Item
from apps.core.models.contact import Contact
from apps.orgs.models import OrgBase


DEMO_SOURCE = 'demo-baseline'

# ─── Transaction cycle definitions ──────────────────────────────────────
# Each cycle: customer ida, contact ida, price_level, terms,
#             proposal/order/invoice/payment idas, lines spec, payment spec

CYCLES = [
    {
        'name': 'Riverside Sports — Team Equipment Order',
        'customer_ida': 'CUST-01',
        'contact_ida': 'CON-01',
        'price_level': 'B',
        'terms': 'N30',
        'proposal_ida': 'PROP-01',
        'order_ida': 'ORD-01',
        'invoice_ida': 'INV-01',
        'gl_batch': 'SJ-DEMO-01',
        'lines': [
            # (item_ida, quantity, unit_measure)
            ('BAT-01', 2, 'each'),
            ('BAG-01', 1, 'each'),
            ('BALL-01', 2, 'dozen'),
        ],
        'payments': [
            # (ida, fraction_of_total, method, status)
            ('PAY-01', Decimal('1.0'), 'check-1234', 'completed'),
        ],
    },
    {
        'name': 'Metro Baseball Academy — Training Equipment',
        'customer_ida': 'CUST-02',
        'contact_ida': 'CON-02',
        'price_level': 'A',
        'terms': 'N30',
        'proposal_ida': 'PROP-02',
        'order_ida': 'ORD-02',
        'invoice_ida': 'INV-02',
        'gl_batch': 'SJ-DEMO-02',
        'lines': [
            ('SCREEN-01', 3, 'each'),
            ('TRAIN-01', 6, 'each'),
            ('GLOVE-02', 3, 'pair'),
        ],
        'payments': [
            ('PAY-02', Decimal('0.6'), 'visa-8821', 'completed'),
            ('PAY-03', Decimal('0.4'), 'visa-8821', 'completed'),
        ],
    },
    {
        'name': 'Eastside Little League — Starter Kits',
        'customer_ida': 'CUST-03',
        'contact_ida': 'CON-03',
        'price_level': 'C',
        'terms': 'N10',
        'proposal_ida': 'PROP-03',
        'order_ida': 'ORD-03',
        'invoice_ida': 'INV-03',
        'gl_batch': 'SJ-DEMO-03',
        'lines': [
            ('KIT-01', 12, 'each'),
            ('BALL-02', 6, 'dozen'),
        ],
        'payments': [
            ('PAY-04', Decimal('1.0'), 'check-5678', 'completed'),
        ],
    },
]


def _demo_refs():
    """Return refs dict tagged as demo-baseline for clean removal."""
    from common.models import default_refs
    refs = default_refs()
    refs['source'] = DEMO_SOURCE
    return refs


def _empty_totals(subtotal=0, total=0, cost=0, received=0, balance=0):
    """Build a totals dict with sensible defaults for demo data."""
    margin = float(Decimal(str(total)) - Decimal(str(cost)))
    margin_pc = float(
        (Decimal(str(margin)) / Decimal(str(total)) * 100)
        if total else 0
    )
    return {
        'subtotal': float(subtotal),
        'discount': 0,
        'taxable': float(subtotal),
        'tax': 0,
        'shipping': 0,
        'other': 0,
        'total': float(total),
        'cost': float(cost),
        'margin': margin,
        'margin_pc': round(margin_pc, 2),
        'received': float(received),
        'balance': float(balance),
    }


def _item_json(item_obj, item_ida):
    """Build the line.item JSON envelope from an Item record."""
    return {
        'item_id': item_obj.id,
        'ida_item': item_ida,
        'description': item_obj.description or item_obj.name,
        'unit_measure': '',
    }


def _quantity_json(qty):
    """Build the line.quantity JSON envelope."""
    return {
        'staged': float(qty),
        'active': float(qty),
        'remaining': float(qty),
        'precision': 2,
        'is_fixed': False,
        'is_complete': False,
        'is_blanket': False,
        'increment': 0,
    }


def _price_json(unit_price, qty):
    """Build the line.price JSON envelope."""
    extended = float(Decimal(str(unit_price)) * Decimal(str(qty)))
    return {
        'unit': float(unit_price),
        'unit_base': float(unit_price),
        'discount_percent': 0.0,
        'discount_amount': 0.0,
        'extended': extended,
        'is_fixed': False,
        'precision': 2,
    }


def _cost_json(unit_cost, qty):
    """Build the line.cost JSON envelope."""
    extended = float(Decimal(str(unit_cost)) * Decimal(str(qty)))
    return {
        'unit': float(unit_cost),
        'unit_base': float(unit_cost),
        'discount_percent': 0.0,
        'discount_amount': 0.0,
        'extended': extended,
        'shipping': 0.0,
        'handling': 0.0,
        'freight': 0.0,
        'commissions': 0.0,
        'tax_rate': 0.0,
        'tax': 0.0,
        'is_fixed': False,
        'precision': 2,
        'tax_code': '',
        'tax_code_id': 0,
        'tax_lookup_id': 0,
    }


class Command(BaseCommand):
    help = (
        'Seed 3 complete transaction cycles: '
        'proposal → order → invoice → payment → GL journal entries'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Delete existing demo transactions and re-seed',
        )

    def handle(self, *args, **options):
        if options.get('force'):
            self._delete_demo()

        counts = {
            'proposals': 0, 'orders': 0, 'invoices': 0,
            'payments': 0, 'gl_entries': 0, 'lines': 0,
        }

        for cycle in CYCLES:
            result = self._seed_cycle(cycle)
            for k in counts:
                counts[k] += result.get(k, 0)

        self.stdout.write(self.style.SUCCESS(
            f"\nDemo transactions: {counts['proposals']} proposals, "
            f"{counts['orders']} orders, {counts['invoices']} invoices, "
            f"{counts['lines']} lines, {counts['payments']} payments, "
            f"{counts['gl_entries']} GL entries"
        ))

    # ─── Cleanup ────────────────────────────────────────────────────────
    def _delete_demo(self):
        """Delete all demo transaction data by refs.source tag."""
        # Delete in dependency order: GL → payments → invoice lines → invoices →
        # order lines → orders → proposal lines → proposals
        del_gl = GlJournal.objects.filter(refs__source=DEMO_SOURCE).delete()[0]
        del_pay = Payment.objects.filter(refs__source=DEMO_SOURCE).delete()[0]
        del_il = InvoiceLine.objects.filter(refs__source=DEMO_SOURCE).delete()[0]
        del_inv = Invoice.objects.filter(refs__source=DEMO_SOURCE).delete()[0]
        del_ol = OrderLine.objects.filter(refs__source=DEMO_SOURCE).delete()[0]
        del_ord = Order.objects.filter(refs__source=DEMO_SOURCE).delete()[0]
        del_pl = ProposalLine.objects.filter(refs__source=DEMO_SOURCE).delete()[0]
        del_prop = Proposal.objects.filter(refs__source=DEMO_SOURCE).delete()[0]
        self.stdout.write(
            f'Deleted demo transactions: {del_prop} proposals, {del_ord} orders, '
            f'{del_inv} invoices, {del_pay} payments, {del_gl} GL entries, '
            f'{del_pl + del_ol + del_il} lines'
        )

    # ─── Single cycle ───────────────────────────────────────────────────
    def _seed_cycle(self, cycle):
        """Create one complete transaction cycle. Returns count dict."""
        result = {
            'proposals': 0, 'orders': 0, 'invoices': 0,
            'payments': 0, 'gl_entries': 0, 'lines': 0,
        }

        # Look up customer and contact
        customer = OrgBase.objects.filter(ida=cycle['customer_ida']).first()
        contact = Contact.objects.filter(ida=cycle['contact_ida']).first()
        if not customer or not contact:
            self.stdout.write(self.style.WARNING(
                f"  SKIP {cycle['name']}: customer or contact not found "
                f"({cycle['customer_ida']}, {cycle['contact_ida']})"
            ))
            return result

        # Resolve items and calculate line data
        line_data = []
        for item_ida, qty, unit_measure in cycle['lines']:
            item_obj = Item.objects.filter(ida=item_ida).first()
            if not item_obj:
                self.stdout.write(self.style.WARNING(
                    f"  SKIP line: item {item_ida} not found"
                ))
                continue

            # Get price at customer's price level
            price_dict = item_obj.price or {}
            unit_price = Decimal(str(
                price_dict.get(cycle['price_level'], price_dict.get('base', '0'))
            ))
            # Get cost
            cost_dict = item_obj.cost or {}
            unit_cost = Decimal(str(cost_dict.get('standard', '0')))

            extended_price = unit_price * qty
            extended_cost = unit_cost * qty

            line_data.append({
                'item_obj': item_obj,
                'item_ida': item_ida,
                'qty': qty,
                'unit_measure': unit_measure,
                'unit_price': unit_price,
                'unit_cost': unit_cost,
                'extended_price': extended_price,
                'extended_cost': extended_cost,
            })

        if not line_data:
            return result

        # Calculate totals
        subtotal = sum(ld['extended_price'] for ld in line_data)
        total_cost = sum(ld['extended_cost'] for ld in line_data)
        total = subtotal  # no tax in demo
        now_ms = int(timezone.now().timestamp() * 1000)
        today = date.today()

        # Shared header fields
        header_fields = dict(
            customer=customer,
            contact=contact,
            attention=contact.attention or '',
            email=contact.email or '',
            price_level=cycle['price_level'],
            terms=cycle['terms'],
            total=total,
            dt_needed=now_ms,
            is_active=True,
        )

        # ── Proposal ────────────────────────────────────────────────────
        proposal = Proposal.objects.filter(ida=cycle['proposal_ida']).first()
        if not proposal:
            proposal = Proposal.objects.create(
                ida=cycle['proposal_ida'],
                customer_id=customer.id,
                contact_id=contact.id,
                attention=contact.attention or '',
                email=contact.email or '',
                price_level=cycle['price_level'],
                terms=cycle['terms'],
                total=total,
                dt_needed=now_ms,
                is_active=True,
                status='complete',
                balance=Decimal('0'),
                totals=_empty_totals(subtotal, total, total_cost,
                                     received=0, balance=float(total)),
                refs=_demo_refs(),
            )
            result['proposals'] = 1
            result['lines'] += self._create_lines(
                ProposalLine, 'proposal', proposal, line_data, cycle,
            )

        # ── Order ───────────────────────────────────────────────────────
        order = Order.objects.filter(ida=cycle['order_ida']).first()
        if not order:
            order = Order.objects.create(
                ida=cycle['order_ida'],
                customer_id=customer.id,
                contact_id=contact.id,
                attention=contact.attention or '',
                email=contact.email or '',
                price_level=cycle['price_level'],
                terms=cycle['terms'],
                total=total,
                dt_needed=now_ms,
                is_active=True,
                status='released',
                balance=total,
                parent_id=proposal.id,
                parent_model='proposal',
                totals=_empty_totals(subtotal, total, total_cost,
                                     received=0, balance=float(total)),
                refs=_demo_refs(),
            )
            result['orders'] = 1
            result['lines'] += self._create_lines(
                OrderLine, 'order', order, line_data, cycle,
            )

        # ── Invoice ─────────────────────────────────────────────────────
        invoice = Invoice.objects.filter(ida=cycle['invoice_ida']).first()
        if not invoice:
            invoice = Invoice.objects.create(
                ida=cycle['invoice_ida'],
                customer_id=customer.id,
                contact_id=contact.id,
                attention=contact.attention or '',
                email=contact.email or '',
                price_level=cycle['price_level'],
                terms=cycle['terms'],
                total=total,
                dt_needed=now_ms,
                is_active=True,
                status='released',
                balance=total,
                parent_id=order.id,
                parent_model='order',
                invoice_type='invoice',
                totals=_empty_totals(subtotal, total, total_cost,
                                     received=0, balance=float(total)),
                refs=_demo_refs(),
            )
            result['invoices'] = 1
            result['lines'] += self._create_lines(
                InvoiceLine, 'invoice', invoice, line_data, cycle,
            )

        # ── Payments ────────────────────────────────────────────────────
        running_received = Decimal('0')
        for pay_spec in cycle['payments']:
            pay_ida, fraction, method, pay_status = pay_spec
            pay_amount = (total * fraction).quantize(Decimal('0.01'))
            running_received += pay_amount

            if not Payment.objects.filter(ida=pay_ida).exists():
                Payment.objects.create(
                    ida=pay_ida,
                    type='received',
                    invoice_id=invoice.id,
                    contact_id=contact.id,
                    customer_id=customer.id,
                    amount=pay_amount,
                    dt_payment=timezone.now(),
                    method=method,
                    category='Sales',
                    reference_number=method,
                    notes=f'Demo payment for {cycle["invoice_ida"]}',
                    status=pay_status,
                    is_active=True,
                    refs=_demo_refs(),
                )
                result['payments'] += 1

        # Update invoice totals with payment info
        remaining_balance = total - running_received
        invoice.totals = _empty_totals(
            subtotal, total, total_cost,
            received=float(running_received),
            balance=float(remaining_balance),
        )
        invoice.balance = remaining_balance
        invoice.save(update_fields=['totals', 'balance'])

        # ── GL Journal Entries ──────────────────────────────────────────
        batch_id = cycle['gl_batch']

        # Invoice GL: debit AR, credit Sales
        result['gl_entries'] += self._create_gl(
            ida=f"GL-{batch_id}-AR",
            account='1200-AR',
            debit=float(total),
            credit=None,
            source='invoice',
            source_id=invoice.id,
            source_model='invoice',
            batch_id=batch_id,
            date_posted=today,
            note=f'AR from {cycle["invoice_ida"]}',
        )
        result['gl_entries'] += self._create_gl(
            ida=f"GL-{batch_id}-SALES",
            account='4000-Sales',
            debit=None,
            credit=float(total),
            source='invoice',
            source_id=invoice.id,
            source_model='invoice',
            batch_id=batch_id,
            date_posted=today,
            note=f'Revenue from {cycle["invoice_ida"]}',
        )

        # Payment GL: debit Cash, credit AR — one pair per payment
        for i, pay_spec in enumerate(cycle['payments']):
            pay_ida, fraction, method, _ = pay_spec
            pay_amount = float((total * fraction).quantize(Decimal('0.01')))
            pay_obj = Payment.objects.filter(ida=pay_ida).first()
            pay_src_id = pay_obj.id if pay_obj else 0
            suffix = f'-P{i + 1}' if len(cycle['payments']) > 1 else '-P'

            result['gl_entries'] += self._create_gl(
                ida=f"GL-{batch_id}{suffix}-CASH",
                account='1000-Cash',
                debit=pay_amount,
                credit=None,
                source='payment',
                source_id=pay_src_id,
                source_model='payment',
                batch_id=batch_id,
                date_posted=today,
                note=f'Cash from {pay_ida} ({method})',
            )
            result['gl_entries'] += self._create_gl(
                ida=f"GL-{batch_id}{suffix}-AR",
                account='1200-AR',
                debit=None,
                credit=pay_amount,
                source='payment',
                source_id=pay_src_id,
                source_model='payment',
                batch_id=batch_id,
                date_posted=today,
                note=f'AR cleared by {pay_ida} ({method})',
            )

        self.stdout.write(f'  {cycle["name"]}: cycle complete')
        return result

    # ─── Line creation ──────────────────────────────────────────────────
    def _create_lines(self, LineModel, fk_name, parent, line_data, cycle):
        """Create line items for a transaction header. Returns count.

        Uses bulk_create to bypass post_save signals that expect live
        transaction context (inventory pending, source dict parsing).
        Demo data doesn't need those side effects.
        """
        import uuid as _uuid
        now_ms = int(timezone.now().timestamp() * 1000)
        lines_to_create = []
        for idx, ld in enumerate(line_data):
            line_ida = f"{fk_name.upper()}-{cycle[f'{fk_name}_ida'].split('-')[-1]}-L{idx + 1}"
            if LineModel.objects.filter(ida=line_ida).exists():
                continue

            item_json = _item_json(ld['item_obj'], ld['item_ida'])
            item_json['unit_measure'] = ld['unit_measure']

            fields = {
                'ida': line_ida,
                f'{fk_name}_id': parent.id,
                'line_number': (idx + 1) * 10,
                'line_type': 'product',
                'item_fk_id': ld['item_obj'].id,
                'item': item_json,
                'quantity': _quantity_json(ld['qty']),
                'price': _price_json(ld['unit_price'], ld['qty']),
                'cost': _cost_json(ld['unit_cost'], ld['qty']),
                'price_level': cycle['price_level'],
                'status': 'released',
                'is_active': True,
                'refs': _demo_refs(),
                'uuid': _uuid.uuid4(),
                'dt_created': now_ms,
                'dt_modified': now_ms,
            }
            lines_to_create.append(LineModel(**fields))
        if lines_to_create:
            LineModel.objects.bulk_create(lines_to_create)
        return len(lines_to_create)

    # ─── GL entry creation ──────────────────────────────────────────────
    def _create_gl(self, ida, account, debit, credit, source, source_id,
                   source_model, batch_id, date_posted, note):
        """Create a single GL journal entry. Returns 1 if created, 0 if exists."""
        if GlJournal.objects.filter(ida=ida).exists():
            return 0
        import datetime as _dt
        # Convert date to epoch ms for dt_journaled
        if isinstance(date_posted, _dt.date):
            dt_j = int(_dt.datetime.combine(date_posted, _dt.time.min,
                        tzinfo=_dt.timezone.utc).timestamp() * 1000)
        else:
            dt_j = int(date_posted) if date_posted else 0
        GlJournal.objects.create(
            ida=ida,
            account=account,
            debit=debit,
            credit=credit,
            source=source,
            type='sales',
            source_id=source_id,
            source_model=source_model,
            division='',
            batch_id=batch_id,
            dt_journaled=dt_j,
            note=note,
            is_active=True,
            refs=_demo_refs(),
        )
        return 1
