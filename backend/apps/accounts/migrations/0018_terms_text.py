# Terms as text (Bill, 2026-10-22): "Users will not think in terms of FK for terms.
# Terms change rarely. There should be no FK delete risks of deleting a term."
# A ledger names its term by ida, the same key a document carries. The ida is copied
# from the FK before the FK is dropped.

from django.db import migrations, models
from django.db.models import OuterRef, Subquery


def copy_term_ida(apps, schema_editor):
    Ledger = apps.get_model('accounts', 'Ledger')
    Term = apps.get_model('accounts', 'Term')
    Ledger.objects.filter(term__isnull=False).update(
        terms=Subquery(Term.objects.filter(pk=OuterRef('term_id')).values('ida')[:1]))


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0017_gl_event_and_reversal_of'),
    ]

    operations = [
        migrations.AddField(
            model_name='ledger',
            name='terms',
            field=models.CharField(blank=True, default='', help_text='Term ida the schedule was computed from (N30, 2pct10N30, ...)', max_length=40),
        ),
        migrations.RunPython(copy_term_ida, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='ledger',
            name='term',
        ),
    ]
