from django.core.management.base import BaseCommand

from apps.transactions.models.project import Project
from apps.core.models.action import Action


class Command(BaseCommand):
    help = "Backfill empty project names and link actions to project ids."

    def handle(self, *args, **options):
        updated_project_names = self._repair_project_names()
        updated_actions = self._link_actions_to_projects()

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {updated_project_names} project names; "
                f"relabeled {updated_actions} actions."
            )
        )

    def _repair_project_names(self) -> int:
        updated = 0
        queryset = Project.objects.all().order_by("id").iterator(chunk_size=500)

        for project in queryset:
            if project.name == "" and project.slug:
                project.name = project.slug;
            else:
                project.name = str(project.id)
            project.save(update_fields=["name"])
            updated += 1

        return updated

    def _link_actions_to_projects(self) -> int:
        slug_to_project = {
            slug: (project_id, name or "")
            for project_id, slug, name in Project.objects.filter(slug__isnull=False)
            .exclude(slug="")
            .values_list("id", "slug", "name")
        }

        if not slug_to_project:
            return 0

        updated = 0
        queryset = Action.objects.order_by("id").iterator(chunk_size=500)

        for action in queryset:
            slug = (action.project_name or "").strip()
            project_data = slug_to_project.get(slug)
            if not project_data:
                continue

            project_id, project_name = project_data
            needs_update = False

            if action.project_id != project_id:
                action.project_id = project_id
                needs_update = True

            if action.project_name != project_name:
                action.project_name = project_name
                needs_update = True

            if needs_update:
                action.save(update_fields=["project_id", "project_name"])
                updated += 1

        return updated
