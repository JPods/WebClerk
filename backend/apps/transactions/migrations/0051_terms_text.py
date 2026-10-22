# Terms as text (Bill, 2026-10-22). A document and a cash entry name their term by ida;
# the FKs go. Every ida is copied into the text field before its FK is dropped (a
# document's `terms` already set wins over its FK, as resolve_term read them).

from django.db import migrations, models
from django.db.models import OuterRef, Q, Subquery

DOCUMENTS = ('Invoice', 'Order', 'Purchase', 'Quote', 'Receipt', 'WorkOrder')


def copy_term_ida(apps, schema_editor):
    Term = apps.get_model('accounts', 'Term')
    ida_of = lambda field: Subquery(Term.objects.filter(pk=OuterRef(field)).values('ida')[:1])
    for name in DOCUMENTS:
        Model = apps.get_model('transactions', name)
        Model.objects.filter(terms_fk__isnull=False).filter(Q(terms__isnull=True) | Q(terms='')).update(
            terms=ida_of('terms_fk_id'))
    apps.get_model('transactions', 'Cash').objects.filter(term__isnull=False).update(terms=ida_of('term_id'))


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0050_line_assigned_to_id'),
        ('accounts', '0017_gl_event_and_reversal_of'),
    ]

    operations = [
        migrations.AddField(
            model_name='cash',
            name='terms',
            field=models.CharField(blank=True, default='', help_text='Term ida applied (N30, COD, ...)', max_length=40),
        ),
        migrations.RunPython(copy_term_ida, migrations.RunPython.noop),
        migrations.RemoveField(model_name='cash', name='term'),
        migrations.RemoveField(model_name='invoice', name='terms_fk'),
        migrations.RemoveField(model_name='order', name='terms_fk'),
        migrations.RemoveField(model_name='purchase', name='terms_fk'),
        migrations.RemoveField(model_name='quote', name='terms_fk'),
        migrations.RemoveField(model_name='receipt', name='terms_fk'),
        migrations.RemoveField(model_name='workorder', name='terms_fk'),
    ]
