"""
Migrate org financial field to new type-keyed structure.

Usage:
    python manage.py migrate_financial_structure
    python manage.py migrate_financial_structure --dry-run
    python manage.py migrate_financial_structure --org-id 123
"""
from django.core.management.base import BaseCommand
from apps.orgs.models import OrgBase
from apps.orgs.models.constants import default_financial, OrgType
import copy


def deep_merge(base: dict, updates: dict) -> dict:
    """Recursively merge updates into base, preserving base structure."""
    result = copy.deepcopy(base)
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        elif value is not None:  # Don't overwrite with None
            result[key] = value
    return result


def migrate_old_to_new(old_financial: dict, org_type: str | None) -> dict:
    """
    Migrate old flat financial structure to new type-keyed structure.
    Maps old keys to appropriate type sections based on org_type.
    """
    new_financial = default_financial()
    
    if not old_financial:
        return new_financial
    
    # Already migrated? Check for type keys
    if any(k in old_financial for k in ['common', 'customer', 'vendor', 'rep', 'employee', 'manufacturer']):
        # Merge with defaults to ensure all keys exist
        return deep_merge(new_financial, old_financial)
    
    # ----- Migrate flat structure to type-keyed -----
    
    # Common fields
    if 'currency' in old_financial:
        new_financial['common']['currency'] = old_financial.get('currency', {}).get('code', 'USD')
    if 'account' in old_financial:
        new_financial['common']['account'] = deep_merge(
            new_financial['common']['account'], 
            old_financial.get('account', {})
        )
    if 'rating' in old_financial:
        new_financial['common']['rating'] = deep_merge(
            new_financial['common']['rating'],
            old_financial.get('rating', {})
        )
    if 'settings' in old_financial:
        new_financial['common']['settings'] = deep_merge(
            new_financial['common']['settings'],
            old_financial.get('settings', {})
        )
    
    # FX
    if 'currency' in old_financial:
        curr = old_financial.get('currency', {})
        new_financial['fx']['gain_loss_mtd'] = curr.get('fx_gain_loss_mtd', 0)
        new_financial['fx']['gain_loss_ytd'] = curr.get('fx_gain_loss_ytd', 0)
        new_financial['fx']['gain_loss_alltime'] = curr.get('fx_gain_loss_alltime', 0)
    
    # Map old flat fields to customer section (default for legacy data)
    # These apply when org is a customer
    if org_type == OrgType.CUSTOMER or org_type is None:
        cust = new_financial['customer']
        
        if 'credit' in old_financial:
            cust['credit'] = deep_merge(cust['credit'], old_financial['credit'])
        if 'balances' in old_financial:
            cust['balances'] = deep_merge(cust['balances'], old_financial['balances'])
        if 'aging' in old_financial:
            cust['aging'] = deep_merge(cust['aging'], old_financial['aging'])
        if 'payment' in old_financial:
            cust['payment'] = deep_merge(cust['payment'], old_financial['payment'])
        if 'sales' in old_financial:
            sales_old = old_financial.get('sales', {})
            cust['sales']['mtd'] = sales_old.get('mtd', 0)
            cust['sales']['ytd'] = sales_old.get('ytd', 0)
            cust['sales']['dt_last_sale'] = sales_old.get('dt_last_sale')
            cust['sales']['last_sale_amount'] = sales_old.get('last_sale_amount', 0)
            # Lifetime from old lifetime section
            if 'lifetime' in old_financial:
                cust['sales']['lifetime'] = old_financial['lifetime'].get('sales', 0)
        if 'margin' in old_financial:
            cust['margin'] = deep_merge(cust['margin'], old_financial['margin'])
        if 'returns' in old_financial:
            cust['returns'] = deep_merge(cust['returns'], old_financial['returns'])
        if 'deposits' in old_financial:
            cust['deposits'] = deep_merge(cust['deposits'], old_financial['deposits'])
        if 'collection' in old_financial:
            cust['collection'] = deep_merge(cust['collection'], old_financial['collection'])
        if 'minimums' in old_financial:
            cust['minimums']['order'] = old_financial['minimums'].get('order', 0)
        if 'stats' in old_financial:
            for stat_key in ['proposals', 'orders', 'invoices', 'payments']:
                if stat_key in old_financial['stats']:
                    cust['stats'][stat_key] = deep_merge(
                        cust['stats'][stat_key],
                        old_financial['stats'][stat_key]
                    )
        if 'complaints' in old_financial.get('rating', {}):
            cust['complaints'] = old_financial['rating']['complaints']
        if 'small_stings' in old_financial:
            cust['small_stings'] = deep_merge(cust['small_stings'], old_financial['small_stings'])
    
    # Map to vendor section
    if org_type == OrgType.VENDOR:
        vend = new_financial['vendor']
        
        if 'credit' in old_financial:
            vend['credit']['limit'] = old_financial['credit'].get('limit', 0)
        if 'balances' in old_financial:
            vend['balances'] = deep_merge(vend['balances'], old_financial['balances'])
        if 'aging' in old_financial:
            vend['aging'] = deep_merge(vend['aging'], old_financial['aging'])
        if 'costs' in old_financial:
            vend['costs'] = deep_merge(vend['costs'], old_financial['costs'])
        if 'minimums' in old_financial:
            vend['minimums']['order'] = old_financial['minimums'].get('order', 0)
            vend['minimums']['purchase'] = old_financial['minimums'].get('purchase', 0)
        if 'stats' in old_financial and 'purchases' in old_financial['stats']:
            vend['stats']['purchases'] = deep_merge(
                vend['stats']['purchases'],
                old_financial['stats']['purchases']
            )
        if 'small_stings' in old_financial:
            vend['small_stings'] = deep_merge(vend['small_stings'], old_financial['small_stings'])
    
    # Map to rep section
    if org_type == OrgType.REP:
        rep = new_financial['rep']
        
        if 'commissions' in old_financial:
            comm = old_financial['commissions']
            if 'income' in comm:
                rep['commissions']['mtd'] = comm['income'].get('mtd', 0)
                rep['commissions']['ytd'] = comm['income'].get('ytd', 0)
            if 'lifetime' in old_financial:
                rep['commissions']['lifetime'] = old_financial['lifetime'].get('commissions', 0)
        if 'stats' in old_financial:
            for stat_key in ['proposals', 'orders']:
                if stat_key in old_financial['stats']:
                    rep['stats'][stat_key] = {
                        'issued': old_financial['stats'][stat_key].get('issued', {'count': 0, 'value': 0}),
                        'executed': old_financial['stats'][stat_key].get('executed', {'count': 0, 'value': 0}),
                    }
    
    # Map to manufacturer section
    if org_type == OrgType.MANUFACTURER:
        mfr = new_financial['manufacturer']
        
        if 'lifetime' in old_financial:
            mfr['purchases']['lifetime'] = old_financial['lifetime'].get('purchases', 0)
        if 'stats' in old_financial and 'purchases' in old_financial['stats']:
            mfr['stats']['purchases'] = deep_merge(
                mfr['stats']['purchases'],
                old_financial['stats']['purchases']
            )
    
    return new_financial


class Command(BaseCommand):
    help = 'Migrate org financial fields to new type-keyed structure'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without saving',
        )
        parser.add_argument(
            '--org-id',
            type=int,
            help='Migrate a specific org by ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        org_id = options.get('org_id')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - no changes will be saved'))
        
        # Get orgs to migrate
        if org_id:
            orgs = OrgBase.objects.filter(id=org_id)
        else:
            orgs = OrgBase.objects.all()
        
        total = orgs.count()
        migrated = 0
        skipped = 0
        errors = 0
        
        self.stdout.write(f'Processing {total} orgs...')
        
        for org in orgs.iterator():
            try:
                old_financial = org.financial or {}
                
                # Check if already migrated
                if 'common' in old_financial and 'customer' in old_financial:
                    skipped += 1
                    continue
                
                # Migrate to new structure
                new_financial = migrate_old_to_new(old_financial, org.org_type)
                
                if dry_run:
                    self.stdout.write(f'  Would migrate org {org.id} ({org.display_name})')
                    if options['verbosity'] >= 2:
                        self.stdout.write(f'    Old keys: {list(old_financial.keys())}')
                        self.stdout.write(f'    New keys: {list(new_financial.keys())}')
                else:
                    org.financial = new_financial
                    org.save(update_fields=['financial', 'dt_modified'])
                
                migrated += 1
                
            except Exception as e:
                errors += 1
                self.stderr.write(self.style.ERROR(f'Error migrating org {org.id}: {e}'))
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Migration complete:'))
        self.stdout.write(f'  Total orgs:  {total}')
        self.stdout.write(f'  Migrated:    {migrated}')
        self.stdout.write(f'  Skipped:     {skipped} (already migrated)')
        self.stdout.write(f'  Errors:      {errors}')
        
        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Run without --dry-run to apply changes'))
