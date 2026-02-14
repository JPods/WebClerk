# Rename Action model project_id field to id_project

from django.db import migrations


def _column_names(schema_editor, table_name: str) -> set[str]:
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table_name)
    return {col.name for col in description}


def _forward_rename_project_id(apps, schema_editor):
    table_name = 'actions'
    columns = _column_names(schema_editor, table_name)
    if 'project_id' in columns and 'id_project' not in columns:
        q_table = schema_editor.quote_name(table_name)
        q_old = schema_editor.quote_name('project_id')
        q_new = schema_editor.quote_name('id_project')
        schema_editor.execute(f'ALTER TABLE {q_table} RENAME COLUMN {q_old} TO {q_new}')


def _reverse_rename_project_id(apps, schema_editor):
    table_name = 'actions'
    columns = _column_names(schema_editor, table_name)
    if 'id_project' in columns and 'project_id' not in columns:
        q_table = schema_editor.quote_name(table_name)
        q_old = schema_editor.quote_name('id_project')
        q_new = schema_editor.quote_name('project_id')
        schema_editor.execute(f'ALTER TABLE {q_table} RENAME COLUMN {q_old} TO {q_new}')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_rename_model_name_to_model_target'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(_forward_rename_project_id, _reverse_rename_project_id),
            ],
            state_operations=[
                migrations.RenameField(
                    model_name='action',
                    old_name='project_id',
                    new_name='id_project',
                ),
            ],
        ),
    ]