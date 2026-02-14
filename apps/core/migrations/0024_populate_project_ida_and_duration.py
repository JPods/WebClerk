# Generated data migration

from django.db import migrations


def populate_project_ida_and_duration(apps, schema_editor):
    """
    Copy project_id into project_ida (as string) where project_ida is empty.
    Set duration to 7 where it is null or 0.
    """
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))
        if 'actions' not in tables:
            return

        cols = {
            col.name
            for col in connection.introspection.get_table_description(cursor, 'actions')
        }

        if {'project_id', 'project_ida'}.issubset(cols):
            cursor.execute(
                """
                UPDATE actions
                SET project_ida = project_id::text
                WHERE project_id <> 0
                  AND (project_ida IS NULL OR project_ida = '')
                """
            )

        if 'duration' in cols:
            cursor.execute(
                """
                UPDATE actions
                SET duration = 7
                WHERE duration IS NULL OR duration = 0
                """
            )


def reverse_populate(apps, schema_editor):
    # No need to reverse - data is still valid
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_action_project_ida'),
    ]

    operations = [
        migrations.RunPython(populate_project_ida_and_duration, reverse_populate),
    ]
