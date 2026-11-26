from django.db import migrations


# A receipt's charges no line carries post to one expense account when the receipt is journalized
# (Bill, 2026-11-26: "it should be an expense type gl but one specifically for
# unallocated-receipt"). A fresh install gets the account and the role from the chart file. An
# installed chart gets them here, so journalizing such a receipt does not refuse for a role nobody
# mapped. Only what is missing is added: an account that exists and a role the company already
# mapped are never touched. Any landed_freight / landed_duty / landed_handling / landed_vat role
# left from the branch that preceded this ruling is removed; it is no longer a posting role.
ACCOUNT = ('6560-unallocated_receipt', 'Unallocated Receipt Charges', 'expense', 'operating_expenses', 'expense')
ROLE = 'unallocated_receipt'
GONE = ('landed_freight', 'landed_duty', 'landed_handling', 'landed_vat')


def add_account_and_role(apps, schema_editor):
    GlAccount = apps.get_model('accounts', 'GlAccount')
    Setting = apps.get_model('core', 'Setting')
    if not GlAccount.objects.exists():
        return                      # no chart yet: the chart file brings both
    ida, name, acct_type, category, used_for = ACCOUNT
    if not GlAccount.objects.filter(ida=ida).exists():
        GlAccount.objects.create(ida=ida, name=name, type=acct_type, category=category,
                                 used_for=used_for, is_active=True)
    for company in Setting.objects.filter(purpose='wc:company_profile'):
        config = company.config if isinstance(company.config, dict) else {}
        defaults = config.get('gl_defaults')
        if not isinstance(defaults, dict) or not defaults:
            continue                # no role map: WC_HQ's recommended set fills it
        kept = {role: code for role, code in defaults.items() if role not in GONE}
        if not kept.get(ROLE):
            kept[ROLE] = ida
        if kept != defaults:
            config['gl_defaults'] = kept
            Setting.objects.filter(pk=company.pk).update(config=config)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0020_journal_batch_type_per_posting_model'),
        ('core', '0075_company_formatting_models_override'),
    ]

    operations = [
        migrations.RunPython(add_account_and_role, migrations.RunPython.noop),
    ]
