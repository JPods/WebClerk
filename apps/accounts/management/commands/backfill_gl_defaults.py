from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Assign default GL accounts to entities that are missing them (items, services, tax jurisdictions, contacts commissions)."

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument('--limit', type=int, default=0, help='Max records per model (0 = all).')

    def handle(self, *args, **opts):  # pragma: no cover
        from django.apps import apps as dj_apps
        from apps.accounts.services.gl_defaults import assign_gl_defaults

        limit = int(opts['limit'] or 0)
        total_changed = 0

        # Items & Services
        for app_label, model_name, purposes in (
            ('products', 'Item', ['sales','inventory','cost','purchase']),
            ('products', 'Service', ['sales','cost']),
        ):
            Model = dj_apps.get_model(app_label, model_name)
            cnt = 0
            for obj in Model.objects.only('id').iterator(chunk_size=200):
                changed = assign_gl_defaults(obj, table_name=Model._meta.db_table, purposes=purposes)
                if changed:
                    obj.save(update_fields=['gls'])
                    total_changed += changed
                cnt += 1
                if limit and cnt >= limit:
                    break

        # Tax Jurisdictions
        TJ = dj_apps.get_model('accounts', 'TaxJurisdiction')
        cnt = 0
        for tj in TJ.objects.only('id','gl_account_payable').iterator(chunk_size=200):
            changed = assign_gl_defaults(tj, table_name=TJ._meta.db_table, purposes=['tax_payable'])
            if changed:
                tj.save(update_fields=['gl_account_payable'])
                total_changed += changed
            cnt += 1
            if limit and cnt >= limit:
                break

        # Contacts (commission recipients)
        Contact = dj_apps.get_model('core', 'Contact')
        cnt = 0
        for c in Contact.objects.only('id','prefs').iterator(chunk_size=200):
            changed = assign_gl_defaults(c, table_name='contacts', purposes=['commission'])
            if changed:
                c.save(update_fields=['prefs'])
                total_changed += changed
            cnt += 1
            if limit and cnt >= limit:
                break

        self.stdout.write(self.style.SUCCESS(f"GL defaults backfill complete. Changes applied: {total_changed}"))
