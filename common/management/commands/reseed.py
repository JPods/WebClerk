from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

from django.contrib.auth import get_user_model


def _ensure_demo_superusers():
    """
    Ensure three deterministic superusers exist:
      1@1.com / 1, 2@2.com / 2, 3@3.com / 3
    Works with custom user models that use email or username.
    """
    User = get_user_model()
    demo = [
        ("1@1.com", "1", "One", "Demo"),
        ("2@2.com", "2", "Two", "Demo"),
        ("3@3.com", "3", "Three", "Demo"),
    ]
    created = 0
    for email, pwd, first, last in demo:
        qs = User.objects
        # Prefer lookup by email if the field exists
        if hasattr(User, "email"):
            exists = qs.filter(email=email).exists()
        else:
            exists = qs.filter(username=email).exists()
        if exists:
            continue
        kwargs = {}
        if hasattr(User, "email"):
            kwargs["email"] = email
        if hasattr(User, "username") and "email" not in kwargs:
            kwargs["username"] = email
        # Optional naming fields (support custom or Django defaults)
        if hasattr(User, "name_first"):
            kwargs["name_first"] = first
        if hasattr(User, "name_last"):
            kwargs["name_last"] = last
        if hasattr(User, "first_name") and "name_first" not in kwargs:
            kwargs["first_name"] = first
        if hasattr(User, "last_name") and "name_last" not in kwargs:
            kwargs["last_name"] = last
        try:
            User.objects.create_superuser(password=pwd, **kwargs)
            created += 1
        except Exception:
            # Fallback: create then elevate if create_superuser signature differs
            user = User.objects.create(**kwargs)
            user.set_password(pwd)
            if hasattr(user, "is_staff"):
                user.is_staff = True
            if hasattr(user, "is_superuser"):
                user.is_superuser = True
            user.save()
            created += 1
    return created


class Command(BaseCommand):
    help = "Unified reseed: full reset+seed only. DEV ONLY."

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument('--full', action='store_true', help='Drop DB, migrate, seed defaults, superusers (like nuke_reseed_3).')
        parser.add_argument('--superusers', type=int, default=3, help='Number of superusers to create (full mode).')
        parser.add_argument('--nuke-migrations', action='store_true', help='Full mode: delete migrations before migrate (dev only).')
        parser.add_argument('--auto-makemigrations', action='store_true', help='Full mode: run makemigrations after nuking migrations.')
        parser.add_argument('--seed-cmd', action='append', default=None, help='Extra seed command(s) to run in full mode (repeatable).')

    def handle(self, *args, **opts):  # pragma: no cover
        if not opts['full']:
            raise CommandError("Only full mode is supported. Use: manage.py reseed --full")
        from common.rebuild.full_reset import full_reset_and_seed, DEFAULT_SEED_COMMANDS
        seed_cmds = opts['seed_cmd'] if opts['seed_cmd'] else DEFAULT_SEED_COMMANDS
        result = full_reset_and_seed(
            destructive=True,
            seed_commands=seed_cmds,
            seed_command_args=None,
            create_superusers=int(opts['superusers']),
            skip_seed=False,
            nuke_migrations=bool(opts['nuke_migrations']),
            auto_make_migrations=bool(opts['auto_makemigrations']),
        )
        try:
            call_command('seed_default_connections')
        except Exception:
            pass
        try:
            from django.apps import apps as dj_apps
            Location = dj_apps.get_model('communications', 'Location')
            cnt = 0
            for loc in Location.objects.only('id', 'address1', 'address2', 'city', 'state', 'zip', 'country', 'metadata').iterator(chunk_size=200):
                try:
                    loc.save()
                    cnt += 1
                except Exception:
                    pass
            self.stdout.write(self.style.SUCCESS(f"Backfill: Location display updated ({cnt})."))
        except Exception:
            pass
        # Ensure deterministic demo superusers exist regardless of seeders
        su_created = _ensure_demo_superusers()
        if su_created:
            self.stdout.write(self.style.SUCCESS(f"Created {su_created} demo superuser(s): 1@1.com, 2@2.com, 3@3.com"))
        self.stdout.write(self.style.SUCCESS(f"Unified reseed complete: db={result.db_name} superusers={result.superusers}"))
        return 0
