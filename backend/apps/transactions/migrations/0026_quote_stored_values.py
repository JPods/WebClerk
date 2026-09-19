"""Proposal → Quote in stored values (Bill, 2026-09-18).

Every text and JSON column in the public schema is rewritten case-preservingly
(PROPOSAL→QUOTE, Proposal→Quote, proposal→quote): model names in refs/links and
access lists, sequence keys, parent_model columns, event types, labels and prose.

Not touched: Django's own tables (django_migrations holds history; content types are
renamed by RenameModel), the WC2 export names, and the other meanings of "proposal"
listed in PROTECT. Permissions named for the old models are removed when nobody holds
them; Django creates the quote ones. The report "Proposal / Quote" becomes "Quote".
"""
from django.db import migrations

PROTECT = ['idNumProposal', 'mapping proposal', 'column proposals', 'Agent proposals', 'agent-proposal']
SKIP_TABLE_PREFIXES = ('django_', 'auth_permission')


def _expr(col: str) -> str:
    text = f'"{col}"::text'
    for i, g in enumerate(PROTECT):
        text = f"replace({text}, '{g}', '\u0001{i}\u0001')"
    for a, b in (('PROPOSAL', 'QUOTE'), ('Proposal', 'Quote'), ('proposal', 'quote')):
        text = f"replace({text}, '{a}', '{b}')"
    for i, g in enumerate(PROTECT):
        text = f"replace({text}, '\u0001{i}\u0001', '{g}')"
    return text


def forwards(apps, schema_editor):
    with schema_editor.connection.cursor() as cur:
        cur.execute("""
            select c.table_name, c.column_name, c.data_type
            from information_schema.columns c
            join information_schema.tables t on t.table_name = c.table_name and t.table_schema = c.table_schema
            where c.table_schema = 'public' and t.table_type = 'BASE TABLE'
              and c.data_type in ('text', 'character varying', 'json', 'jsonb')
        """)
        for table, col, dtype in cur.fetchall():
            if table.startswith(SKIP_TABLE_PREFIXES):
                continue
            cast = '::jsonb' if dtype == 'jsonb' else ('::json' if dtype == 'json' else '')
            cur.execute(f'update "{table}" set "{col}" = ({_expr(col)}){cast} '
                        f'where "{col}"::text ~ \'[Pp]roposal|PROPOSAL\'')
        # Permissions for the old names: Django creates add_/change_/delete_/view_quote(line)
        # after migrating. Old rows go only when nobody holds them.
        cur.execute("""
            delete from auth_permission p
            where p.codename ~ '_proposal(line)?$'
              and not exists (select 1 from auth_group_permissions g where g.permission_id = p.id)
              and not exists (select 1 from contacts_user_permissions u where u.permission_id = p.id)
        """)
        cur.execute("update reports set name = 'Quote' where name = 'Quote / Quote'")


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0025_alter_invoice_parent_model_alter_order_parent_model_and_more'),
        ('accounts', '0011_alter_erosion_parent_model_and_more'),
        ('ai_assistant', '0006_alter_inventoryevent_event_type'),
        ('communications', '0008_alter_touch_linkage_id'),
        ('core', '0010_alter_auditlog_model_name'),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
