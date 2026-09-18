"""
seed_demo_observer — Set up observer mode for WC3 demos.

Creates:
  1. demo- transaction records (orders, invoices, cash, expenses, actions, statement lines)
  2. Observer user (demo@webclerk.com) — read-only, no saves
  3. Date-relative refresh — all dates pivot around today

Usage:
    python manage.py seed_demo_observer              # create demo data + observer user
    python manage.py seed_demo_observer --refresh     # update all demo dates to today-relative
    python manage.py seed_demo_observer --clean       # remove all demo data

Prerequisites: seed_demo must have run first (items, orgs, contacts).

All demo records use ida prefix 'demo-' and are excluded from reports/tallies
by the zz/qq exclusion rule.
"""
from datetime import timedelta
from decimal import Decimal
import time

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


DEMO_PREFIX = 'qqdemo-'


def _ms(dt):
    """Convert datetime to epoch milliseconds."""
    return int(dt.timestamp() * 1000)


# ─── Day offsets from today ─────────────────────────────────────────
# Negative = past, positive = future
ORDER_OFFSETS   = [-14, -10, -7, -5, -3, -2, -1, 0, 1, 3]
INVOICE_OFFSETS = [-12, -8, -5, -3, -1]
CASH_OFFSETS = [-10, -6, -3, -1, 0]
EXPENSE_OFFSETS = [-9, -7, -4, -2, -1, 0, 1, 2, 3, 5]
ACTION_OFFSETS  = [-2, -1, 0, 0, 1, 2, 3, 4, 5, 5]
STMT_OFFSETS    = [-15, -14, -12, -10, -8, -7, -5, -3, -2, -1]

EXPENSE_ENTRIES = [
    {'desc': 'DigitalOcean hosting', 'amount': -12.37, 'category': 'Hosting', 'method': 'visa_3425'},
    {'desc': 'Office Depot supplies', 'amount': -47.82, 'category': 'Office Supplies', 'method': 'visa_3425'},
    {'desc': 'Xcel Energy electric', 'amount': -247.83, 'category': 'Utilities', 'method': 'check'},
    {'desc': 'AT&T internet', 'amount': -89.99, 'category': 'Utilities', 'method': 'ach'},
    {'desc': 'Southwest Airlines', 'amount': -327.40, 'category': 'Travel', 'method': 'visa_3425'},
    {'desc': 'Hilton Garden Inn', 'amount': -189.00, 'category': 'Travel', 'method': 'visa_3425'},
    {'desc': 'GoDaddy domains', 'amount': -358.08, 'category': 'Hosting', 'method': 'visa_3425'},
    {'desc': 'State Farm insurance', 'amount': -142.50, 'category': 'Insurance', 'method': 'ach'},
    {'desc': 'Staples toner', 'amount': -34.99, 'category': 'Office Supplies', 'method': 'visa_3425'},
    {'desc': 'Wise transfer intl', 'amount': -691.74, 'category': 'Professional Services', 'method': 'wire'},
]

ACTION_ENTRIES = [
    {'title': 'Follow up with Tulsa Baseball Academy on team order', 'project': 'Sales', 'priority': 2},
    {'title': 'Prepare Q3 invoice batch for wholesale accounts', 'project': 'Accounting', 'priority': 1},
    {'title': 'Review new bat catalog from National Baseball Supply', 'project': 'Purchasing', 'priority': 1},
    {'title': 'Update price levels for fall season', 'project': 'Sales', 'priority': 2},
    {'title': 'Schedule equipment delivery to Metro High School', 'project': 'Fulfillment', 'priority': 3},
    {'title': 'Reconcile July credit card statement', 'project': 'Accounting', 'priority': 2},
    {'title': 'Send proposal to Oklahoma City Parks Dept', 'project': 'Sales', 'priority': 3},
    {'title': 'Inventory count — gloves and bags', 'project': 'Warehouse', 'priority': 1},
    {'title': 'Call back Mike Torres about league discount', 'project': 'Sales', 'priority': 2},
    {'title': 'File sales tax return for Q2', 'project': 'Accounting', 'priority': 3},
]

STMT_ENTRIES = [
    {'desc': 'DIGITALOCEAN.COM NEW YORK NY', 'amount': -12.37, 'source': 'wellsfargo_cc'},
    {'desc': 'OFFICE DEPOT #1234 TULSA OK', 'amount': -47.82, 'source': 'wellsfargo_cc'},
    {'desc': 'XCEL ENERGY CASH 800-895-4999 CO', 'amount': -247.83, 'source': 'wellsfargo_checking'},
    {'desc': 'AT&T*BILL CASH 800-288-2020 TX', 'amount': -89.99, 'source': 'usaa'},
    {'desc': 'SOUTHWEST AIRLINES 800-435-9792 TX', 'amount': -327.40, 'source': 'wellsfargo_cc'},
    {'desc': 'HILTON GARDEN INN TULSA OK', 'amount': -189.00, 'source': 'wellsfargo_cc'},
    {'desc': 'DNH*GODADDY.COM 480-5058855 AZ', 'amount': -358.08, 'source': 'wellsfargo_cc'},
    {'desc': 'METRO HIGH SCHOOL DEPOSIT', 'amount': 1500.00, 'source': 'wellsfargo_checking'},
    {'desc': 'TULSA BASEBALL ACAD CASH', 'amount': 2847.50, 'source': 'wellsfargo_checking'},
    {'desc': 'ONLINE CASH THANK YOU', 'amount': -500.00, 'source': 'wellsfargo_cc'},
]


class Command(BaseCommand):
    help = 'Set up observer mode: demo transactions + read-only user + date-relative refresh'

    def add_arguments(self, parser):
        parser.add_argument('--refresh', action='store_true', help='Update all demo dates to today-relative')
        parser.add_argument('--clean', action='store_true', help='Remove all demo transaction data')

    def handle(self, *args, **options):
        if options.get('clean'):
            self._clean()
            return

        if options.get('refresh'):
            self._refresh_dates()
            return

        self._seed_transactions()
        self._seed_observer_user()
        self.stdout.write(self.style.SUCCESS('\nDemo observer mode ready.'))
        self.stdout.write('  Login: demo@webclerk.com / demo2026')
        self.stdout.write('  Run --refresh before each demo to update dates.')

    def _clean(self):
        from apps.transactions.models import Cash, Order, Invoice
        from apps.transactions.models.statement_line import StatementLine
        from apps.core.models.action import Action

        counts = {}
        for model, name in [(Cash, 'cash_entries'), (Order, 'orders'), (Invoice, 'invoices'),
                            (StatementLine, 'statement_lines'), (Action, 'actions')]:
            c = model.objects.filter(ida__startswith=DEMO_PREFIX).delete()[0]
            counts[name] = c

        User.objects.filter(email='demo@webclerk.com').delete()
        self.stdout.write(f'Cleaned: {counts}')

    def _refresh_dates(self):
        """Update all demo record dates to be relative to today."""
        from apps.transactions.models import Cash, Order, Invoice
        from apps.transactions.models.statement_line import StatementLine
        from apps.core.models.action import Action

        now = timezone.now()
        updated = 0

        # Orders
        for i, obj in enumerate(Order.objects.filter(ida__startswith=DEMO_PREFIX).order_by('id')):
            offset = ORDER_OFFSETS[i % len(ORDER_OFFSETS)]
            dt = now + timedelta(days=offset)
            Order.objects.filter(pk=obj.pk).update(dt_created=_ms(dt), dt_modified=_ms(dt))
            updated += 1

        # Invoices
        for i, obj in enumerate(Invoice.objects.filter(ida__startswith=DEMO_PREFIX).order_by('id')):
            offset = INVOICE_OFFSETS[i % len(INVOICE_OFFSETS)]
            dt = now + timedelta(days=offset)
            Invoice.objects.filter(pk=obj.pk).update(dt_created=_ms(dt), dt_modified=_ms(dt))
            updated += 1

        # Cash
        for i, obj in enumerate(Cash.objects.filter(ida__startswith=DEMO_PREFIX).order_by('id')):
            offset = CASH_OFFSETS[i % len(CASH_OFFSETS)] if obj.type == 'cash_in' \
                     else EXPENSE_OFFSETS[i % len(EXPENSE_OFFSETS)]
            dt = now + timedelta(days=offset)
            Cash.objects.filter(pk=obj.pk).update(dt_cash=dt, dt_created=_ms(dt), dt_modified=_ms(dt))
            updated += 1

        # Actions
        for i, obj in enumerate(Action.objects.filter(ida__startswith=DEMO_PREFIX).order_by('id')):
            offset = ACTION_OFFSETS[i % len(ACTION_OFFSETS)]
            dt = now + timedelta(days=offset)
            Action.objects.filter(pk=obj.pk).update(
                dt_deadline=_ms(dt), dt_created=_ms(now - timedelta(days=7)), dt_modified=_ms(dt))
            updated += 1

        # Statement lines
        for i, obj in enumerate(StatementLine.objects.filter(ida__startswith=DEMO_PREFIX).order_by('id')):
            offset = STMT_OFFSETS[i % len(STMT_OFFSETS)]
            dt = now + timedelta(days=offset)
            StatementLine.objects.filter(pk=obj.pk).update(
                dt_transaction=dt, dt_created=_ms(dt), dt_modified=_ms(dt))
            updated += 1

        self.stdout.write(self.style.SUCCESS(f'Refreshed {updated} demo records to today-relative dates.'))

    def _seed_transactions(self):
        from apps.transactions.models import Cash
        from apps.transactions.models.statement_line import StatementLine
        from apps.core.models.action import Action
        from apps.orgs.models import OrgBase

        now = timezone.now()

        # Get a demo customer and vendor for FK links
        customer = OrgBase.objects.filter(ida__startswith=DEMO_PREFIX, org_type='customer').first()
        vendor = OrgBase.objects.filter(ida__startswith=DEMO_PREFIX, org_type='vendor').first()

        # ── Expense cash ──
        created_pay = 0
        for i, exp in enumerate(EXPENSE_ENTRIES):
            ida = f'qqdemo-EXP-{i+1:02d}'
            if Cash.objects.filter(ida=ida).exists():
                continue
            offset = EXPENSE_OFFSETS[i % len(EXPENSE_OFFSETS)]
            dt = now + timedelta(days=offset)
            Cash.objects.create(
                ida=ida,
                type='cash_out',
                amount=Decimal(str(exp['amount'])),
                category=exp['category'],
                method=exp['method'],
                notes=exp['desc'],
                dt_cash=dt,
                status='completed',
                vendor=vendor,
            )
            created_pay += 1
        self.stdout.write(f'  Expense cash: {created_pay} created')

        # ── Received cash ──
        received_entries = [
            {'desc': 'Metro High School deposit', 'amount': 1500.00, 'method': 'check', 'ref': '4821'},
            {'desc': 'Tulsa Baseball Academy cash', 'amount': 2847.50, 'method': 'visa_3425', 'ref': ''},
            {'desc': 'Mike Torres league order', 'amount': 599.85, 'method': 'cash', 'ref': ''},
            {'desc': 'Online store order #1047', 'amount': 249.90, 'method': 'visa_3425', 'ref': 'ORD-1047'},
            {'desc': 'Broken Arrow Parks Dept', 'amount': 4200.00, 'method': 'check', 'ref': '9012'},
        ]
        created_recv = 0
        for i, recv in enumerate(received_entries):
            ida = f'qqdemo-RECV-{i+1:02d}'
            if Cash.objects.filter(ida=ida).exists():
                continue
            offset = CASH_OFFSETS[i % len(CASH_OFFSETS)]
            dt = now + timedelta(days=offset)
            Cash.objects.create(
                ida=ida,
                type='cash_in',
                amount=Decimal(str(recv['amount'])),
                method=recv['method'],
                reference_number=recv.get('ref', ''),
                notes=recv['desc'],
                dt_cash=dt,
                status='completed',
                customer=customer,
            )
            created_recv += 1
        self.stdout.write(f'  Received cash: {created_recv} created')

        # ── Actions ──
        created_act = 0
        for i, act in enumerate(ACTION_ENTRIES):
            ida = f'qqdemo-ACT-{i+1:02d}'
            if Action.objects.filter(ida=ida).exists():
                continue
            offset = ACTION_OFFSETS[i % len(ACTION_OFFSETS)]
            dt = now + timedelta(days=offset)
            kanban = 'In Progress' if offset <= 0 else 'Backlog'
            status = 'in_progress' if offset <= 0 else 'created'
            Action.objects.create(
                ida=ida,
                action={'en': act['title']},
                project_name=act['project'],
                priority=act['priority'],
                kanban_column=kanban,
                status=status,
                dt_deadline=_ms(dt),
            )
            created_act += 1
        self.stdout.write(f'  Actions: {created_act} created')

        # ── Statement lines ──
        created_stmt = 0
        for i, stmt in enumerate(STMT_ENTRIES):
            ida = f'qqdemo-STMT-{i+1:02d}'
            if StatementLine.objects.filter(ida=ida).exists():
                continue
            offset = STMT_OFFSETS[i % len(STMT_OFFSETS)]
            dt = now + timedelta(days=offset)
            classification = 'business' if stmt['amount'] < 0 else 'unknown'
            StatementLine.objects.create(
                ida=ida,
                dt_transaction=dt,
                description=stmt['desc'],
                amount=Decimal(str(stmt['amount'])),
                source=stmt['source'],
                raw_text=f"{dt.strftime('%m/%d/%Y')},{stmt['amount']},*,,{stmt['desc']}",
                classification=classification,
                ledger='post',
            )
            created_stmt += 1
        self.stdout.write(f'  Statement lines: {created_stmt} created')

    def _seed_observer_user(self):
        """Create a read-only demo user."""
        email = 'demo@webclerk.com'
        if User.objects.filter(email=email).exists():
            self.stdout.write('  Observer user already exists: demo@webclerk.com')
            return

        user = User.objects.create_user(
            username='demo',
            email=email,
            password='demo2026',  # secret-guard:allow — seeded demo account
            is_staff=False,
            is_superuser=False,
        )
        # Set role via UserProfile if it exists
        try:
            from apps.core.models import UserProfile
            UserProfile.objects.update_or_create(
                user=user,
                defaults={'role': 'observer', 'display_name': 'Demo Observer'},
            )
        except Exception:
            pass

        self.stdout.write(f'  Observer user created: {email} / demo2026')
