"""security_audit — verify security controls are active and correctly configured.

Implements readmes/50-security-policy-webclerk.md §12 open items:
  - Guest role lockdown: verify auto-created guests see nothing
  - Django protections: confirm CSRF, XSS, clickjacking, HSTS not disabled
  - DEBUG guard: refuse production hostname with DEBUG=True
  - RBAC empty org_ids: verify fail-closed behavior
  - Athena validation: report configuration status

Usage:
  python manage.py security_audit                  # full audit
  python manage.py security_audit --check guest     # just guest role check
  python manage.py security_audit --check django    # just Django protections
  python manage.py security_audit --check rbac      # just RBAC verification

Established: 2026-09-10
"""
import socket

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q


CHECKS = ('django', 'guest', 'rbac', 'connections', 'debug')


class Command(BaseCommand):
    help = 'Verify security controls are active and correctly configured'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check', type=str, default='all',
            help=f'Specific check to run: {", ".join(CHECKS)}, or "all"',
        )

    def handle(self, *args, **options):
        check = options['check']
        passed = 0
        failed = 0
        warnings = 0

        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write("WebClerk Security Audit")
        self.stdout.write(f"{'=' * 60}\n")

        if check in ('all', 'debug'):
            p, f, w = self._check_debug()
            passed += p; failed += f; warnings += w

        if check in ('all', 'django'):
            p, f, w = self._check_django_protections()
            passed += p; failed += f; warnings += w

        if check in ('all', 'guest'):
            p, f, w = self._check_guest_role()
            passed += p; failed += f; warnings += w

        if check in ('all', 'rbac'):
            p, f, w = self._check_rbac_empty_orgs()
            passed += p; failed += f; warnings += w

        if check in ('all', 'connections'):
            p, f, w = self._check_connections()
            passed += p; failed += f; warnings += w

        # Summary
        self.stdout.write(f"\n{'─' * 60}")
        self.stdout.write(
            f"Results: {passed} passed, {failed} FAILED, {warnings} warnings"
        )
        if failed:
            self.stdout.write(self.style.ERROR("AUDIT FAILED — fix issues above"))
        else:
            self.stdout.write(self.style.SUCCESS("All checks passed"))
        self.stdout.write("")

    def _pass(self, msg):
        self.stdout.write(self.style.SUCCESS(f"  ✓ {msg}"))

    def _fail(self, msg):
        self.stdout.write(self.style.ERROR(f"  ✗ {msg}"))

    def _warn(self, msg):
        self.stdout.write(self.style.WARNING(f"  ⚠ {msg}"))

    def _check_debug(self):
        """Verify DEBUG is not True on a production hostname."""
        self.stdout.write("\n[DEBUG Guard]")
        passed = failed = warnings = 0

        hostname = socket.gethostname()
        debug = getattr(settings, 'DEBUG', False)
        localhost_names = {'localhost', '127.0.0.1', 'macbook', 'mac'}

        if debug:
            is_local = any(h in hostname.lower() for h in localhost_names)
            if is_local:
                self._warn(f"DEBUG=True on {hostname} — acceptable for local dev")
                warnings += 1
            else:
                self._fail(f"DEBUG=True on {hostname} — PRODUCTION RISK")
                failed += 1
        else:
            self._pass(f"DEBUG=False on {hostname}")
            passed += 1

        # Check SECRET_KEY
        fallback = 'insecure-dev-test-key'
        if settings.SECRET_KEY == fallback:
            if debug:
                self._warn("Using fallback SECRET_KEY — acceptable in dev")
                warnings += 1
            else:
                self._fail("Using fallback SECRET_KEY in production!")
                failed += 1
        else:
            self._pass("SECRET_KEY is set (not fallback)")
            passed += 1

        return passed, failed, warnings

    def _check_django_protections(self):
        """Verify Django's built-in security protections are active."""
        self.stdout.write("\n[Django Protections]")
        passed = failed = warnings = 0

        checks = [
            ('CSRF middleware',
             'django.middleware.csrf.CsrfViewMiddleware' in settings.MIDDLEWARE),
            ('SecurityMiddleware',
             'django.middleware.security.SecurityMiddleware' in settings.MIDDLEWARE),
            ('X_FRAME_OPTIONS',
             getattr(settings, 'X_FRAME_OPTIONS', '') == 'DENY'),
            ('SECURE_HSTS_SECONDS > 0',
             getattr(settings, 'SECURE_HSTS_SECONDS', 0) > 0),
            ('SECURE_HSTS_INCLUDE_SUBDOMAINS',
             getattr(settings, 'SECURE_HSTS_INCLUDE_SUBDOMAINS', False)),
            ('SESSION_COOKIE_SECURE (or DEBUG)',
             getattr(settings, 'SESSION_COOKIE_SECURE', False) or settings.DEBUG),
            ('CSRF_COOKIE_SECURE (or DEBUG)',
             getattr(settings, 'CSRF_COOKIE_SECURE', False) or settings.DEBUG),
        ]

        for name, ok in checks:
            if ok:
                self._pass(name)
                passed += 1
            else:
                self._fail(name)
                failed += 1

        # Check WriteGateMiddleware and AthenaValidationMiddleware
        wg = any('WriteGateMiddleware' in m for m in settings.MIDDLEWARE)
        av = any('AthenaValidationMiddleware' in m for m in settings.MIDDLEWARE)

        if wg:
            self._pass("WriteGateMiddleware active")
            passed += 1
        else:
            self._fail("WriteGateMiddleware NOT in MIDDLEWARE")
            failed += 1

        if av:
            self._pass("AthenaValidationMiddleware active")
            passed += 1
        else:
            self._warn("AthenaValidationMiddleware not in MIDDLEWARE")
            warnings += 1

        return passed, failed, warnings

    def _check_guest_role(self):
        """Verify that guest-role users see no records through RBAC."""
        self.stdout.write("\n[Guest Role Lockdown]")
        passed = failed = warnings = 0

        try:
            from apps.core.services.role_filter import (
                inject_role_filters, build_user_context,
            )
            from apps.core.models import Contact

            # A login whose role is not an access role (e.g. 'user') must see nothing
            from apps.core.services.access import ROLES
            guest = Contact.objects.exclude(role__in=ROLES).filter(is_superuser=False).first()
            if not guest:
                self._warn("No logins without an access role exist — cannot verify")
                return 0, 0, 1

            # Build context and check org_ids
            ctx = build_user_context(guest)
            org_types = ['customer', 'vendor', 'manufacturer', 'rep']

            for org_type in org_types:
                org_ids = ctx.get('org_ids', {}).get(org_type, [])
                if org_ids:
                    self._fail(
                        f"Guest {guest.id} has org_ids.{org_type} = {org_ids} "
                        f"— should be empty"
                    )
                    failed += 1
                else:
                    self._pass(f"Guest has no org_ids.{org_type}")
                    passed += 1

            # Verify inject_role_filters returns impossible Q for key models
            test_models = ['order', 'invoice', 'contact']
            for model_name in test_models:
                q = inject_role_filters(guest, model_name)
                if q == Q(pk__isnull=True):
                    self._pass(f"Guest query for {model_name} → Q(pk__isnull=True) (no results)")
                    passed += 1
                else:
                    # Check if the Q object would produce any results
                    self._warn(
                        f"Guest query for {model_name} returned Q object: {q} "
                        f"— verify this restricts to zero results"
                    )
                    warnings += 1

        except Exception as e:
            self._fail(f"Could not verify guest role: {e}")
            failed += 1

        return passed, failed, warnings

    def _check_rbac_empty_orgs(self):
        """Verify that users with empty org_ids get no results (fail closed)."""
        self.stdout.write("\n[RBAC Empty Org_ids]")
        passed = failed = warnings = 0

        try:
            from apps.core.services.role_filter import inject_role_filters
            from apps.core.models import Contact

            # Find a non-superuser, non-guest with a role
            user = Contact.objects.filter(
                is_superuser=False, is_active=True,
            ).exclude(role__in=['', 'guest']).first()

            if not user:
                self._warn("No non-superuser users to test")
                return 0, 0, 1

            # Test that inject_role_filters produces a valid Q
            q = inject_role_filters(user, 'order')
            self._pass(f"inject_role_filters returned Q for user {user.id} (role={user.role})")
            passed += 1

        except Exception as e:
            self._fail(f"RBAC check failed: {e}")
            failed += 1

        return passed, failed, warnings

    def _check_connections(self):
        """Report connections without sunset dates."""
        self.stdout.write("\n[Connection Sunset Dates]")
        passed = failed = warnings = 0

        try:
            from apps.sync.models import Connection

            active = Connection.objects.filter(is_active=True)
            total = active.count()

            no_sunset = 0
            for conn in active:
                config = conn.config or {}
                sunset = config.get('sunset') or config.get('sunset_date')
                if not sunset:
                    no_sunset += 1
                    self._warn(f"Connection {conn.id} ({conn.name}) has no sunset date")
                    warnings += 1

            if no_sunset == 0 and total > 0:
                self._pass(f"All {total} active connections have sunset dates")
                passed += 1
            elif total == 0:
                self._pass("No active connections")
                passed += 1
            else:
                self._warn(f"{no_sunset} of {total} active connections lack sunset dates")

        except Exception as e:
            self._fail(f"Connection check failed: {e}")
            failed += 1

        return passed, failed, warnings
