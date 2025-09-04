from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from common.rebuild import full_reset_and_seed


class Command(BaseCommand):
    help = (
        "One-shot dev helper: nuke migrations, regenerate single 0001_initial, drop & recreate DB, "
        "run default seed commands, create exactly 3 patterned superusers (1@1.com..3@3.com)."
    )

    def handle(self, *args, **options):  # pragma: no cover
        # Supply extended relationship seeding flags so order/customer links & orderline propagation happen in the FIRST run
        result = full_reset_and_seed(
            destructive=True,
            seed_commands=None,  # use defaults (includes seed_relationships)
            seed_command_args={
                'seed_relationships': [
                    '--customer-order-links',
                    '--orderline-links',
                    '--order-contact',
                    '--auto-create-contacts','5',
                    '--ensure-contact-order-link',
                    '--ensure-contact-org-link',
                ]
            },
            create_superusers=3,
            skip_seed=False,
            nuke_migrations=True,
            auto_make_migrations=True,
        )
        User = get_user_model()
        existing = list(User.objects.filter(email__in=['1@1.com','2@2.com','3@3.com']).values_list('email', flat=True))
        missing = sorted(set(['1@1.com','2@2.com','3@3.com']) - set(existing))
        status = 'OK' if not missing else f"MISSING:{','.join(missing)}"
        self.stdout.write(self.style.SUCCESS(
            f"nuke_reseed_3 complete: db={result.db_name} migrations=nuked seeds={','.join(result.seed_commands_run)} superusers={result.superusers} ({status})"
        ))
        if missing:
            return 1
        return 0
