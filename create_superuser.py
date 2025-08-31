import os
import argparse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
import django  # noqa: E402
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="Create or upsert a superuser (idempotent).")
    parser.add_argument('--email', default=os.getenv('SUPERUSER_EMAIL', 'admin@webclerk.com'))
    parser.add_argument('--password', default=os.getenv('SUPERUSER_PASSWORD', '123456'))
    # Accept both legacy and new naming conventions
    parser.add_argument('--first-name', dest='first_name', default=os.getenv('FIRST_NAME'))
    parser.add_argument('--name-first', dest='name_first', default=os.getenv('NAME_FIRST'))
    parser.add_argument('--last-name', dest='last_name', default=os.getenv('LAST_NAME'))
    parser.add_argument('--name-last', dest='name_last', default=os.getenv('NAME_LAST'))
    parser.add_argument('--role', default=os.getenv('SUPERUSER_ROLE', 'admin'))
    parser.add_argument('--no-update', action='store_true', help="Fail if user exists instead of ensuring superuser flags.")
    return parser.parse_args()


def main():
    args = parse_args()
    User = get_user_model()

    # Resolve name fields (prefer explicit new names, then legacy, then defaults)
    resolved_first = args.name_first or args.first_name or 'Super'
    resolved_last = args.name_last or args.last_name or 'Admin'

    exists = User.objects.filter(email=args.email).first()
    if exists:
        if args.no_update:
            print(f"User {args.email} already exists (no-update).")
            return 0
        changed = False
        if not exists.is_superuser:
            exists.is_superuser = True; changed = True
        if not exists.is_staff:
            exists.is_staff = True; changed = True
        if hasattr(exists, 'role') and getattr(exists, 'role') != args.role:
            setattr(exists, 'role', args.role); changed = True
        # Update name fields only if blank to avoid clobbering intentional values
        if hasattr(exists, 'name_first') and not getattr(exists, 'name_first') and resolved_first:
            setattr(exists, 'name_first', resolved_first); changed = True
        if hasattr(exists, 'name_last') and not getattr(exists, 'name_last') and resolved_last:
            setattr(exists, 'name_last', resolved_last); changed = True
        if changed:
            update_fields = ['is_superuser','is_staff']
            if hasattr(exists, 'role'): update_fields.append('role')
            if hasattr(exists, 'name_first'): update_fields.append('name_first')
            if hasattr(exists, 'name_last'): update_fields.append('name_last')
            # include modified_dt/version if model tracks them
            if hasattr(exists, 'modified_dt'): update_fields.append('modified_dt')
            if hasattr(exists, 'version'): update_fields.append('version')
            exists.save(update_fields=update_fields)
            print(f"Updated existing superuser {args.email}.")
        else:
            print(f"Superuser {args.email} already up-to-date.")
        return 0

    # Create new superuser (manager supports legacy first_name/last_name mapping already)
    create_kwargs = dict(email=args.email, password=args.password, username=args.email)
    # Provide legacy names for manager mapping
    create_kwargs['first_name'] = resolved_first
    create_kwargs['last_name'] = resolved_last
    if 'role' in [f.name for f in User._meta.get_fields() if hasattr(f, 'name')]:
        create_kwargs['role'] = args.role
    user = User.objects.create_superuser(**create_kwargs)
    print(f"Superuser {user.email} created.")
    return 0


if __name__ == '__main__':  # pragma: no cover
    try:
        raise SystemExit(main())
    except Exception as e:  # defensive
        print(f"Error creating superuser: {e}")
        raise SystemExit(1)
    exit(1)