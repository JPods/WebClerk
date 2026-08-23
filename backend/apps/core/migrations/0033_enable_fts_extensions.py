"""Enable PostgreSQL extensions for Full-Text Search and trigram similarity."""

from django.db import migrations
from django.contrib.postgres.operations import (
    TrigramExtension,
    UnaccentExtension,
)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0032_add_times_used_dt_last_used"),
    ]

    operations = [
        TrigramExtension(),
        UnaccentExtension(),
    ]
