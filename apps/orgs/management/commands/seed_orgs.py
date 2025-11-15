from django.core.management.base import BaseCommand
from apps.orgs.models import OrgBase, OrgType

SAMPLE_NAMES = {
    OrgType.CUSTOMER: ["Acme Retail","North Supply","Blue Market"],
    OrgType.VENDOR: ["Vendor One","Prime Parts","Global Goods"],
    OrgType.REP: ["Rep Alpha","Rep Beta","Rep Gamma"],
    OrgType.EMPLOYEE: ["Employee Group A","Employee Group B","Employee Group C"],
    OrgType.MANUFACTURER: ["MFG Core","MFG Advanced","MFG Horizon"],
}

class Command(BaseCommand):
    help = "Seed 3 sample org records for each major org_type (customers, vendors, reps, employees, manufacturers). Idempotent."

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=3, help='How many per org_type (max 5).')
        parser.add_argument('--force', action='store_true', help='Create even if existing records already present for that org_type.')

    def handle(self, *args, **opts):
        count = max(1, min(opts['count'], 5))
        force = opts['force']
        created = []
        for org_type, names in SAMPLE_NAMES.items():
            existing_qs = OrgBase.objects.filter(org_type=org_type)
            if existing_qs.exists() and not force:
                self.stdout.write(f"Skip {org_type} (already has {existing_qs.count()} records). Use --force to add more.")
                continue
            for name in names[:count]:
                obj = OrgBase.objects.create(
                    org_type=org_type,
                    company=name,
                    status='active',
                    is_active=True,
                )
                created.append({
                    'id': obj.id,
                    'org_type': obj.org_type,
                    'company': obj.company,
                    'status': obj.status,
                })
        if not created:
            self.stdout.write('No new orgs created.')
            return
        self.stdout.write('Created orgs:')
        for row in created:
            self.stdout.write(f" - {row['id']}: {row['org_type']} :: {row['company']}")
