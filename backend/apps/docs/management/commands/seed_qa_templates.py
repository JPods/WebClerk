"""
seed_qa_templates — Seed universal QA template Documents.

Usage:
    python manage.py seed_qa_templates
    python manage.py seed_qa_templates --force   # overwrite existing

Each Document record represents one checklist/inspection type.
Questions and answer choices live in Document.config.questions[].
Every question and every answer has a stable unique ID for metrics.

When a user fills out a checklist, QuestionAnswer records are created
with document FK + question_id + answer_id linking back to these IDs.

ID scheme:
  - question ids: {template_prefix}{sequence} (e.g., RCV-1, RCV-2)
  - answer ids: {question_id}-{sequence} (e.g., RCV-1-1, RCV-1-2)
  This makes every answer globally unique and traceable in metrics.
"""
from django.core.management.base import BaseCommand
from apps.docs.models.document import Document


# ─── Template definitions ────────────────────────────────────────────────
# Universal templates that any business can use.
# Company-specific templates (printing checklists, JPods inspections)
# are added by the company after setup.

TEMPLATES = [
    {
        'ida': 'qa-receiving',
        'name': 'Receiving Inspection',
        'description': 'Inspect incoming goods against PO — quantity, condition, documentation',
        'body': 'Verify that received goods match the purchase order in quantity, condition, and documentation. '
                'Any discrepancy creates an NCR. Damaged goods are segregated immediately.',
        'config': {
            'pass_threshold': 100,
            'questions': [
                {'id': 'RCV-1', 'question': 'PO number matches packing slip?', 'sequence': 1, 'type': 'select',
                 'answers': [{'id': 'RCV-1-1', 'answer': 'Yes'}, {'id': 'RCV-1-2', 'answer': 'No'}, {'id': 'RCV-1-3', 'answer': 'N/A'}]},
                {'id': 'RCV-2', 'question': 'Quantity received matches PO quantity?', 'sequence': 2, 'type': 'select',
                 'answers': [{'id': 'RCV-2-1', 'answer': 'Yes'}, {'id': 'RCV-2-2', 'answer': 'No — short'}, {'id': 'RCV-2-3', 'answer': 'No — over'}]},
                {'id': 'RCV-3', 'question': 'Packaging intact — no visible damage?', 'sequence': 3, 'type': 'select', 'photo_required': True,
                 'answers': [{'id': 'RCV-3-1', 'answer': 'Yes'}, {'id': 'RCV-3-2', 'answer': 'Minor damage'}, {'id': 'RCV-3-3', 'answer': 'Major damage — segregate'}]},
                {'id': 'RCV-4', 'question': 'Items match description on PO?', 'sequence': 4, 'type': 'select',
                 'answers': [{'id': 'RCV-4-1', 'answer': 'Yes'}, {'id': 'RCV-4-2', 'answer': 'No — wrong item'}, {'id': 'RCV-4-3', 'answer': 'Partial match'}]},
                {'id': 'RCV-5', 'question': 'Certificate of conformance / test report included?', 'sequence': 5, 'type': 'select',
                 'answers': [{'id': 'RCV-5-1', 'answer': 'Yes'}, {'id': 'RCV-5-2', 'answer': 'No'}, {'id': 'RCV-5-3', 'answer': 'Not required'}]},
                {'id': 'RCV-6', 'question': 'Lot/serial numbers recorded?', 'sequence': 6, 'type': 'select',
                 'answers': [{'id': 'RCV-6-1', 'answer': 'Yes'}, {'id': 'RCV-6-2', 'answer': 'No'}, {'id': 'RCV-6-3', 'answer': 'Not applicable'}]},
                {'id': 'RCV-7', 'question': 'Notes', 'sequence': 7, 'type': 'text', 'answers': []},
            ],
        },
        'refs': {'keywords': ['qa_template', 'receiving', 'inspection'], 'standards': ['QM-10']},
    },

    {
        'ida': 'qa-shipping',
        'name': 'Shipping Verification',
        'description': 'Verify outbound shipment before carrier pickup',
        'body': 'Confirm correct items, quantities, packaging, and documentation before releasing shipment to carrier.',
        'config': {
            'pass_threshold': 100,
            'questions': [
                {'id': 'SHP-1', 'question': 'Order number matches packing slip?', 'sequence': 1, 'type': 'select',
                 'answers': [{'id': 'SHP-1-1', 'answer': 'Yes'}, {'id': 'SHP-1-2', 'answer': 'No'}]},
                {'id': 'SHP-2', 'question': 'All line items picked and packed?', 'sequence': 2, 'type': 'select',
                 'answers': [{'id': 'SHP-2-1', 'answer': 'Yes — complete'}, {'id': 'SHP-2-2', 'answer': 'Partial — backorder noted'}, {'id': 'SHP-2-3', 'answer': 'No — missing items'}]},
                {'id': 'SHP-3', 'question': 'Packaging adequate for shipping method?', 'sequence': 3, 'type': 'select',
                 'answers': [{'id': 'SHP-3-1', 'answer': 'Yes'}, {'id': 'SHP-3-2', 'answer': 'No — repack needed'}]},
                {'id': 'SHP-4', 'question': 'Ship-to address verified?', 'sequence': 4, 'type': 'select',
                 'answers': [{'id': 'SHP-4-1', 'answer': 'Yes'}, {'id': 'SHP-4-2', 'answer': 'No — address issue'}]},
                {'id': 'SHP-5', 'question': 'Weight recorded?', 'sequence': 5, 'type': 'text', 'answers': []},
                {'id': 'SHP-6', 'question': 'Tracking number', 'sequence': 6, 'type': 'text', 'answers': []},
            ],
        },
        'refs': {'keywords': ['qa_template', 'shipping', 'verification'], 'standards': []},
    },

    {
        'ida': 'qa-customer-onboarding',
        'name': 'New Customer Setup',
        'description': 'Checklist for setting up a new customer account',
        'body': 'Ensure all required information is collected and verified before activating a new customer account. '
                'Credit check, tax status, and terms must be confirmed.',
        'config': {
            'pass_threshold': 80,
            'questions': [
                {'id': 'NCO-1', 'question': 'Legal business name verified?', 'sequence': 1, 'type': 'select',
                 'answers': [{'id': 'NCO-1-1', 'answer': 'Yes'}, {'id': 'NCO-1-2', 'answer': 'Pending'}]},
                {'id': 'NCO-2', 'question': 'Tax ID / resale certificate on file?', 'sequence': 2, 'type': 'select',
                 'answers': [{'id': 'NCO-2-1', 'answer': 'Yes'}, {'id': 'NCO-2-2', 'answer': 'No — taxable'}, {'id': 'NCO-2-3', 'answer': 'Pending'}]},
                {'id': 'NCO-3', 'question': 'Credit application received?', 'sequence': 3, 'type': 'select',
                 'answers': [{'id': 'NCO-3-1', 'answer': 'Yes — approved'}, {'id': 'NCO-3-2', 'answer': 'Yes — pending review'}, {'id': 'NCO-3-3', 'answer': 'No — COD'}]},
                {'id': 'NCO-4', 'question': 'Payment terms assigned?', 'sequence': 4, 'type': 'select',
                 'answers': [{'id': 'NCO-4-1', 'answer': 'Yes'}, {'id': 'NCO-4-2', 'answer': 'No'}]},
                {'id': 'NCO-5', 'question': 'Price level assigned?', 'sequence': 5, 'type': 'select',
                 'answers': [{'id': 'NCO-5-1', 'answer': 'A'}, {'id': 'NCO-5-2', 'answer': 'B'}, {'id': 'NCO-5-3', 'answer': 'C'}, {'id': 'NCO-5-4', 'answer': 'D'}]},
                {'id': 'NCO-6', 'question': 'Ship-to address confirmed?', 'sequence': 6, 'type': 'select',
                 'answers': [{'id': 'NCO-6-1', 'answer': 'Yes'}, {'id': 'NCO-6-2', 'answer': 'Pending'}]},
                {'id': 'NCO-7', 'question': 'Sales rep assigned?', 'sequence': 7, 'type': 'select',
                 'answers': [{'id': 'NCO-7-1', 'answer': 'Yes'}, {'id': 'NCO-7-2', 'answer': 'No — house account'}]},
                {'id': 'NCO-8', 'question': 'Welcome communication sent?', 'sequence': 8, 'type': 'select',
                 'answers': [{'id': 'NCO-8-1', 'answer': 'Yes'}, {'id': 'NCO-8-2', 'answer': 'No'}]},
            ],
        },
        'refs': {'keywords': ['qa_template', 'customer', 'onboarding'], 'standards': []},
    },

    {
        'ida': 'qa-vendor-qualification',
        'name': 'Vendor Qualification',
        'description': 'Evaluate and qualify a new vendor before first purchase',
        'body': 'Assess vendor capability, quality systems, financial stability, and references '
                'before adding to approved vendor list. Required by QM-06.',
        'config': {
            'pass_threshold': 80,
            'questions': [
                {'id': 'VQ-1', 'question': 'Vendor has quality management system (ISO 9001 or equivalent)?', 'sequence': 1, 'type': 'select',
                 'answers': [{'id': 'VQ-1-1', 'answer': 'Yes — certified'}, {'id': 'VQ-1-2', 'answer': 'Yes — not certified'}, {'id': 'VQ-1-3', 'answer': 'No'}]},
                {'id': 'VQ-2', 'question': 'Financial references checked?', 'sequence': 2, 'type': 'select',
                 'answers': [{'id': 'VQ-2-1', 'answer': 'Yes — satisfactory'}, {'id': 'VQ-2-2', 'answer': 'Yes — concerns'}, {'id': 'VQ-2-3', 'answer': 'Not checked'}]},
                {'id': 'VQ-3', 'question': 'Customer references checked?', 'sequence': 3, 'type': 'select',
                 'answers': [{'id': 'VQ-3-1', 'answer': 'Yes — positive'}, {'id': 'VQ-3-2', 'answer': 'Yes — mixed'}, {'id': 'VQ-3-3', 'answer': 'Not checked'}]},
                {'id': 'VQ-4', 'question': 'Sample/trial order satisfactory?', 'sequence': 4, 'type': 'select',
                 'answers': [{'id': 'VQ-4-1', 'answer': 'Yes'}, {'id': 'VQ-4-2', 'answer': 'No'}, {'id': 'VQ-4-3', 'answer': 'Not required'}]},
                {'id': 'VQ-5', 'question': 'Lead time acceptable?', 'sequence': 5, 'type': 'select',
                 'answers': [{'id': 'VQ-5-1', 'answer': 'Yes'}, {'id': 'VQ-5-2', 'answer': 'Marginal'}, {'id': 'VQ-5-3', 'answer': 'No'}]},
                {'id': 'VQ-6', 'question': 'Recommendation', 'sequence': 6, 'type': 'select',
                 'answers': [{'id': 'VQ-6-1', 'answer': 'Approve'}, {'id': 'VQ-6-2', 'answer': 'Conditional'}, {'id': 'VQ-6-3', 'answer': 'Reject'}]},
                {'id': 'VQ-7', 'question': 'Notes', 'sequence': 7, 'type': 'text', 'answers': []},
            ],
        },
        'refs': {'keywords': ['qa_template', 'vendor', 'qualification'], 'standards': ['QM-06']},
    },

    {
        'ida': 'qa-inventory-count',
        'name': 'Cycle Count Verification',
        'description': 'Physical inventory count vs system — record variances',
        'body': 'Count physical inventory at bin location and compare to system quantity. '
                'Variances create inventory adjustments. Count at least quarterly per location.',
        'config': {
            'pass_threshold': 100,
            'questions': [
                {'id': 'CYC-1', 'question': 'Item number', 'sequence': 1, 'type': 'text', 'answers': []},
                {'id': 'CYC-2', 'question': 'Bin location', 'sequence': 2, 'type': 'text', 'answers': []},
                {'id': 'CYC-3', 'question': 'System quantity', 'sequence': 3, 'type': 'text', 'answers': []},
                {'id': 'CYC-4', 'question': 'Physical count', 'sequence': 4, 'type': 'text', 'answers': []},
                {'id': 'CYC-5', 'question': 'Variance?', 'sequence': 5, 'type': 'select',
                 'answers': [{'id': 'CYC-5-1', 'answer': 'No — counts match'}, {'id': 'CYC-5-2', 'answer': 'Yes — over'}, {'id': 'CYC-5-3', 'answer': 'Yes — short'}]},
                {'id': 'CYC-6', 'question': 'Condition of stock', 'sequence': 6, 'type': 'select',
                 'answers': [{'id': 'CYC-6-1', 'answer': 'Good'}, {'id': 'CYC-6-2', 'answer': 'Damaged'}, {'id': 'CYC-6-3', 'answer': 'Obsolete'}]},
                {'id': 'CYC-7', 'question': 'Notes', 'sequence': 7, 'type': 'text', 'answers': []},
            ],
        },
        'refs': {'keywords': ['qa_template', 'inventory', 'cycle_count'], 'standards': ['QM-12']},
    },

    {
        'ida': 'qa-ncr',
        'name': 'Nonconformance Report',
        'description': 'Document and disposition a nonconforming product or process',
        'body': 'Record the nonconformance, determine root cause, and decide disposition: '
                'use-as-is, rework, scrap, or return to vendor. Every NCR requires disposition '
                'before the item can move forward. Per QM-13.',
        'config': {
            'pass_threshold': 100,
            'questions': [
                {'id': 'NCR-1', 'question': 'Source of nonconformance', 'sequence': 1, 'type': 'select',
                 'answers': [{'id': 'NCR-1-1', 'answer': 'Incoming material'}, {'id': 'NCR-1-2', 'answer': 'In-process'}, {'id': 'NCR-1-3', 'answer': 'Customer return'}, {'id': 'NCR-1-4', 'answer': 'Internal audit'}]},
                {'id': 'NCR-2', 'question': 'Description of nonconformance', 'sequence': 2, 'type': 'text', 'answers': []},
                {'id': 'NCR-3', 'question': 'Item segregated?', 'sequence': 3, 'type': 'select',
                 'answers': [{'id': 'NCR-3-1', 'answer': 'Yes'}, {'id': 'NCR-3-2', 'answer': 'No — in use'}, {'id': 'NCR-3-3', 'answer': 'N/A — process issue'}]},
                {'id': 'NCR-4', 'question': 'Root cause identified?', 'sequence': 4, 'type': 'select',
                 'answers': [{'id': 'NCR-4-1', 'answer': 'Yes'}, {'id': 'NCR-4-2', 'answer': 'Under investigation'}, {'id': 'NCR-4-3', 'answer': 'Unknown'}]},
                {'id': 'NCR-5', 'question': 'Root cause description', 'sequence': 5, 'type': 'text', 'answers': []},
                {'id': 'NCR-6', 'question': 'Disposition', 'sequence': 6, 'type': 'select',
                 'answers': [{'id': 'NCR-6-1', 'answer': 'Use as-is'}, {'id': 'NCR-6-2', 'answer': 'Rework'}, {'id': 'NCR-6-3', 'answer': 'Scrap'}, {'id': 'NCR-6-4', 'answer': 'Return to vendor'}]},
                {'id': 'NCR-7', 'question': 'Corrective action required?', 'sequence': 7, 'type': 'select',
                 'answers': [{'id': 'NCR-7-1', 'answer': 'Yes — CAR opened'}, {'id': 'NCR-7-2', 'answer': 'No — isolated incident'}]},
                {'id': 'NCR-8', 'question': 'Notes', 'sequence': 8, 'type': 'text', 'answers': []},
            ],
        },
        'refs': {'keywords': ['qa_template', 'ncr', 'nonconformance'], 'standards': ['QM-13']},
    },

    {
        'ida': 'qa-employee-onboarding',
        'name': 'Employee Onboarding',
        'description': 'New employee setup checklist — system access, training, policies',
        'body': 'Ensure new employees have system access, required training, and policy acknowledgments '
                'before starting work. Training records link to Contact qualifications.',
        'config': {
            'pass_threshold': 100,
            'questions': [
                {'id': 'EMP-1', 'question': 'System login created?', 'sequence': 1, 'type': 'select',
                 'answers': [{'id': 'EMP-1-1', 'answer': 'Yes'}, {'id': 'EMP-1-2', 'answer': 'Pending'}]},
                {'id': 'EMP-2', 'question': 'Role/permissions assigned?', 'sequence': 2, 'type': 'select',
                 'answers': [{'id': 'EMP-2-1', 'answer': 'Yes'}, {'id': 'EMP-2-2', 'answer': 'Pending'}]},
                {'id': 'EMP-3', 'question': 'Safety training completed?', 'sequence': 3, 'type': 'select',
                 'answers': [{'id': 'EMP-3-1', 'answer': 'Yes'}, {'id': 'EMP-3-2', 'answer': 'Scheduled'}, {'id': 'EMP-3-3', 'answer': 'Not required'}]},
                {'id': 'EMP-4', 'question': 'Quality policy reviewed and acknowledged?', 'sequence': 4, 'type': 'select',
                 'answers': [{'id': 'EMP-4-1', 'answer': 'Yes'}, {'id': 'EMP-4-2', 'answer': 'Pending'}]},
                {'id': 'EMP-5', 'question': 'Equipment/tools issued?', 'sequence': 5, 'type': 'select',
                 'answers': [{'id': 'EMP-5-1', 'answer': 'Yes'}, {'id': 'EMP-5-2', 'answer': 'N/A'}]},
                {'id': 'EMP-6', 'question': 'Mentor/buddy assigned?', 'sequence': 6, 'type': 'select',
                 'answers': [{'id': 'EMP-6-1', 'answer': 'Yes'}, {'id': 'EMP-6-2', 'answer': 'No'}]},
            ],
        },
        'refs': {'keywords': ['qa_template', 'employee', 'onboarding', 'training'], 'standards': ['QM-18']},
    },
]


class Command(BaseCommand):
    help = 'Seed universal QA template Documents (7 templates)'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Delete existing and re-seed')

    def handle(self, *args, **options):
        if options.get('force'):
            idas = [t['ida'] for t in TEMPLATES]
            deleted, _ = Document.objects.filter(ida__in=idas).delete()
            self.stdout.write(f'Deleted {deleted} existing QA templates')

        created = skipped = 0
        for t in TEMPLATES:
            if Document.objects.filter(ida=t['ida']).exists():
                skipped += 1
                continue

            Document.objects.create(
                ida=t['ida'],
                name=t['name'],
                description=t.get('description', ''),
                body=t.get('body', ''),
                config=t['config'],
                refs=t.get('refs', {}),
                status='active',
                is_active=True,
            )
            created += 1
            q_count = len(t['config']['questions'])
            self.stdout.write(f'  {t["ida"]}: {q_count} questions')

        self.stdout.write(self.style.SUCCESS(
            f'\nQA templates: {created} created, {skipped} already exist'))
