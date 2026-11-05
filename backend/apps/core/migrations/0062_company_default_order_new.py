"""The company profile's one ``default`` section; a document's one priority list; layout
fields carry no option list of their own (Bill, 2026-11-05: a new order is born with
``default.order_new.days`` and ``.priority``; its terms are the customer's or ``default.terms``).

Three blocks named an order's defaults and none was read: ``config.transactions.default_*``,
``config.order_defaults`` and ``prefs.order_defaults`` (served to the browser, which never
read it). They become ``config.default = {terms, order_new: {days, priority}}``.

The six document models' priority lists held WC2's six numbers beside the word every record
carries (medium): one list, low / medium / high / urgent. And every layout field whose model
definition holds the field's list drops its inline ``options`` (0055 did status; the inline
copy was the fourth source and showed words the list does not hold — contractor, low).
"""
from django.db import migrations

DOCUMENTS = ('quote', 'order', 'invoice', 'purchase', 'workorder', 'receipt')
PRIORITY = [{'value': 'low', 'label': 'Low'}, {'value': 'medium', 'label': 'Medium'},
            {'value': 'high', 'label': 'High'}, {'value': 'urgent', 'label': 'Urgent'}]


def _term_ida(Term, value):
    """The active Term's own spelling of ``value`` (net30 / n30 → N30); '' when none matches."""
    text = (value or '').strip().lower().replace('net', 'n')
    if not text:
        return ''
    for ida in Term.objects.filter(is_active=True).values_list('ida', flat=True):
        if ida.lower() == text:
            return ida
    return ''


def _strip_options(node, lists):
    if isinstance(node, dict):
        if 'options' in node and node.get('field') in lists:
            return {k: _strip_options(v, lists) for k, v in node.items() if k != 'options'}
        return {k: _strip_options(v, lists) for k, v in node.items()}
    if isinstance(node, list):
        return [_strip_options(x, lists) for x in node]
    return node


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    Term = apps.get_model('accounts', 'Term')

    for company in Setting.objects.filter(purpose='wc:company_profile'):
        config = dict(company.config or {})
        prefs = dict(company.prefs or {})
        old = config.get('transactions') if isinstance(config.get('transactions'), dict) else {}
        days = old.get('dt_needed_days')
        config['default'] = {
            'terms': _term_ida(Term, old.get('default_terms')),
            'order_new': {'days': int(days) if days not in (None, '') else 14,
                          'priority': 'medium'},
        }
        config.pop('transactions', None)
        config.pop('order_defaults', None)
        prefs.pop('order_defaults', None)
        Setting.objects.filter(pk=company.pk).update(config=config, prefs=prefs)

    for setting in Setting.objects.filter(purpose='wc:model').iterator():
        config = dict(setting.config or {})
        lists = dict(config.get('selectlists') or {})
        if setting.parent_model in DOCUMENTS:
            lists['priority'] = [dict(o) for o in PRIORITY]
            config['selectlists'] = lists
        layout = config.get('layout')
        if layout is not None:
            config['layout'] = _strip_options(layout, set(lists))
        if config != setting.config:
            Setting.objects.filter(pk=setting.pk).update(config=config)


class Migration(migrations.Migration):
    dependencies = [('core', '0061_contact_id_is_a_lookup'), ('accounts', '__latest__')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
