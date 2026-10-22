# Terms as text (Bill, 2026-10-22). An org names its term by ida in `terms`; the FK
# goes. Any org that carried only the FK gets its ida copied into `terms` first.
# financial.common.settings.terms_id — a second, JSON copy of the same id — goes too
# (its ida copied the same way when `terms` is still empty).

from django.db import migrations
from django.db.models import OuterRef, Q, Subquery


def copy_term_ida(apps, schema_editor):
    OrgBase = apps.get_model('orgs', 'OrgBase')
    Term = apps.get_model('accounts', 'Term')
    OrgBase.objects.filter(terms_fk__isnull=False).filter(Q(terms__isnull=True) | Q(terms='')).update(
        terms=Subquery(Term.objects.filter(pk=OuterRef('terms_fk_id')).values('ida')[:1]))
    idas = dict(Term.objects.values_list('pk', 'ida'))
    for org in OrgBase.objects.filter(financial__common__settings__has_key='terms_id').only('pk', 'terms', 'financial'):
        settings = org.financial['common']['settings']
        term_id = settings.pop('terms_id')
        if not org.terms and term_id in idas:
            org.terms = idas[term_id]
        OrgBase.objects.filter(pk=org.pk).update(terms=org.terms, financial=org.financial)


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0010_is_locked_deleted'),
        ('accounts', '0017_gl_event_and_reversal_of'),
    ]

    operations = [
        migrations.RunPython(copy_term_ida, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='orgbase',
            name='terms_fk',
        ),
    ]
