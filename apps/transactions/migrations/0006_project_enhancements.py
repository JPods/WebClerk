from django.db import migrations, models
from django.db.models import Q
from django.utils.text import slugify
from decimal import Decimal

PRIORITY_MIN = 1
PRIORITY_MAX = 5


def populate_slugs(apps, schema_editor):
    Project = apps.get_model('transactions', 'Project')
    seen = set()
    for proj in Project.objects.all().only('id', 'intent', 'slug'):
        base = slugify(proj.intent or '')[:170] or f'project-{proj.id}'
        candidate = base
        idx = 2
        while candidate in seen:
            candidate = f"{base}-{idx}"[:180]
            idx += 1
        seen.add(candidate)
        Project.objects.filter(id=proj.id).update(slug=candidate)


def noop_reverse(apps, schema_editor):  # irreversible
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('transactions', '0005_project'),
    ]

    operations = [
        # 1. Add slug + temp index (no uniqueness yet)
        migrations.AddField(
            model_name='project',
            name='slug',
            field=models.CharField(blank=True, default='', help_text='URL / human friendly identifier derived from intent (unique)', max_length=180, db_index=True),
        ),
        # 2. Alter profit to DecimalField
        migrations.AlterField(
            model_name='project',
            name='profit',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Projected or realized profit (base currency with cents)', max_digits=14),
        ),
        # 3. Populate slug values uniquely
        migrations.RunPython(populate_slugs, noop_reverse),
        # 4. Add constraints & unique constraint + additional indexes
        migrations.AddConstraint(
            model_name='project',
            constraint=models.CheckConstraint(check=Q(priority__gte=PRIORITY_MIN, priority__lte=PRIORITY_MAX), name='project_priority_range'),
        ),
        migrations.AddConstraint(
            model_name='project',
            constraint=models.CheckConstraint(check=Q(burndown__gte=0, burndown__lte=100), name='project_burndown_range'),
        ),
        migrations.AddConstraint(
            model_name='project',
            constraint=models.CheckConstraint(check=Q(security_level__gte=0, security_level__lte=5), name='project_security_range'),
        ),
        migrations.AddConstraint(
            model_name='project',
            constraint=models.UniqueConstraint(fields=['slug'], name='project_slug_unique'),
        ),
    ]
