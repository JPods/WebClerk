"""
db_init — Initialize a WC3 database from scratch.

Three-step process:
  1. Fetch the latest init-bundle from WCHQ API (or fall back to git copy)
  2. Run seed_freshstart (all seed commands in dependency order)
  3. Unpack the init-bundle (Settings + Reports baseline merge)

The WCHQ API provides the latest approved init-bundle, which may include
select list updates, layout improvements, new reports, and coaching content
contributed by the community. The git init-bundle is the fallback when
WCHQ is unreachable.

Usage:
    python manage.py db_init                    # full init (WCHQ → seed → unpack)
    python manage.py db_init --offline          # skip WCHQ, use git bundle only
    python manage.py db_init --fetch-only       # download bundle, don't seed
    python manage.py db_init --dry-run          # show what would happen
    python manage.py db_init --force            # pass --force to seed commands
    python manage.py db_init --wchq-url URL     # custom WCHQ endpoint

Prerequisites: migrations must be applied first (manage.py migrate).
"""
import hashlib
import json
import logging
import secrets
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.management import call_command

logger = logging.getLogger(__name__)

# Default WCHQ API endpoint for init-bundle
WCHQ_INIT_BUNDLE_URL = 'https://webclerk.com/wcapi/init-bundle/'

# Local git copy — always kept current by pack_init_bundle
GIT_BUNDLE_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent / 'init-bundle.json'


def _wchq_url_from_connection():
    """Read WCHQ init-bundle URL from the wchq-conn-downstream Connection record.

    Returns the configured URL if the Connection exists, else None.
    The Connection record is the installation's persistent link to WCHQ.
    """
    try:
        from apps.sync.models.connection import Connection
        conn = Connection.objects.filter(
            ida='wchq-conn-downstream', is_active=True,
        ).first()
        if conn and conn.config:
            base = conn.config.get('wchq_base_url', '')
            endpoint = (conn.config.get('endpoints') or {}).get('init_bundle', '')
            if base and endpoint:
                return base.rstrip('/') + endpoint
    except Exception:
        pass
    return None


class Command(BaseCommand):
    help = 'Initialize a WC3 database: fetch latest bundle from WCHQ, seed, and unpack'

    def add_arguments(self, parser):
        parser.add_argument('--offline', action='store_true',
                            help='Skip WCHQ fetch — use git init-bundle.json only')
        parser.add_argument('--fetch-only', action='store_true',
                            help='Download bundle from WCHQ without seeding or unpacking')
        parser.add_argument('--dry-run', action='store_true',
                            help='Show plan without executing')
        parser.add_argument('--force', action='store_true',
                            help='Pass --force to seed commands')
        parser.add_argument('--wchq-url', type=str, default=WCHQ_INIT_BUNDLE_URL,
                            help=f'WCHQ init-bundle endpoint (default: {WCHQ_INIT_BUNDLE_URL})')
        parser.add_argument('--bundle-path', type=str, default=str(GIT_BUNDLE_PATH),
                            help='Path to local init-bundle.json (default: project root)')

    def _fetch_from_wchq(self, url, timeout=30):
        """Fetch init-bundle JSON from WCHQ API. Returns (bundle_dict, error_msg)."""
        self.stdout.write(f'  Fetching init-bundle from WCHQ: {url}')
        try:
            req = urllib.request.Request(
                url,
                headers={
                    'Accept': 'application/json',
                    'User-Agent': 'WebClerk3-db_init/1.0',
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status != 200:
                    return None, f'WCHQ returned HTTP {resp.status}'
                data = json.loads(resp.read().decode('utf-8'))
                if 'settings' not in data:
                    return None, 'WCHQ response missing settings array'
                return data, None
        except urllib.error.URLError as e:
            return None, f'WCHQ unreachable: {e.reason}'
        except json.JSONDecodeError as e:
            return None, f'WCHQ returned invalid JSON: {e}'
        except Exception as e:
            return None, f'WCHQ fetch failed: {e}'

    def _load_git_bundle(self, path):
        """Load init-bundle from local git copy. Returns (bundle_dict, error_msg)."""
        bundle_path = Path(path)
        if not bundle_path.exists():
            return None, f'Git bundle not found: {bundle_path}'
        try:
            with open(bundle_path) as f:
                data = json.load(f)
            return data, None
        except Exception as e:
            return None, f'Failed to read git bundle: {e}'

    def _save_bundle(self, bundle, path):
        """Save bundle to git path (keeps git init-bundle current)."""
        bundle_path = Path(path)
        with open(bundle_path, 'w') as f:
            json.dump(bundle, f, indent=2, ensure_ascii=False)
        size_kb = bundle_path.stat().st_size / 1024
        self.stdout.write(self.style.SUCCESS(
            f'  Saved to {bundle_path} ({size_kb:.0f} KB)'
        ))

    def _register_with_wchq(self, base_url, timeout=30):
        """Register this installation with WCHQ and get an Athena token.

        Flow:
        1. Generate a local installation_id (UUID from the system Setting)
        2. POST to /wcapi/register-installation/ with the installation_id
        3. WCHQ returns a unique token for this installation
        4. Store the token in wchq-conn-downstream.encryption.athena_token
        5. Add the token to the Athena integrity manifest

        If WCHQ is unreachable, generates a local provisional token
        that can be upgraded later when WCHQ becomes available.

        Returns: (token, source) or (None, error_msg)
        """
        from apps.sync.models.connection import Connection

        # Get or create the downstream Connection
        conn = Connection.objects.filter(
            ida='wchq-conn-downstream', is_active=True,
        ).first()
        if not conn:
            return None, 'wchq-conn-downstream Connection not found'

        # Check if already registered
        encryption = conn.encryption or {}
        existing_token = encryption.get('athena_token')
        if existing_token:
            self.stdout.write(f'  Already registered (token starts {existing_token[:12]}...)')
            return existing_token, 'existing'

        # Get installation UUID from system Setting
        from apps.core.models.setting import Setting
        sys_setting = Setting.objects.filter(purpose='wc:system').first()
        installation_id = str(sys_setting.uuid) if sys_setting and sys_setting.uuid else ''

        # Get onboarding profile from company_profile Setting
        profile_setting = Setting.objects.filter(purpose='wc:company_profile').first()
        onboarding = {}
        company_info = {}
        if profile_setting and profile_setting.config:
            onboarding = profile_setting.config.get('onboarding', {})
            company = profile_setting.config.get('company', {})
            # Send non-sensitive company info (name, industry, locale — not tax_id)
            company_info = {
                'name': company.get('name', ''),
                'city': company.get('address', {}).get('city', ''),
                'state': company.get('address', {}).get('state', ''),
                'country': company.get('address', {}).get('country', ''),
            }

        # Try WCHQ registration
        register_url = f"{base_url.rstrip('/')}/wcapi/register-installation/"
        token = None
        source = None

        try:
            payload = json.dumps({
                'installation_id': installation_id,
                'dt_registered': datetime.now(timezone.utc).isoformat(),
                'company': company_info,
                'onboarding': onboarding,
            }).encode('utf-8')
            req = urllib.request.Request(
                register_url,
                data=payload,
                method='POST',
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'WebClerk3-db_init/1.0',
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status in (200, 201):
                    data = json.loads(resp.read().decode('utf-8'))
                    token = data.get('token')
                    source = 'wchq'
        except Exception as e:
            self.stdout.write(self.style.WARNING(
                f'  WCHQ registration unavailable: {e}'
            ))

        # Fallback: generate provisional local token
        if not token:
            raw = f"{installation_id}:{secrets.token_hex(32)}:{datetime.now(timezone.utc).isoformat()}"
            token = hashlib.sha256(raw.encode()).hexdigest()
            source = 'provisional'
            self.stdout.write('  Generated provisional token (upgrade when WCHQ available)')

        # Store in Connection.encryption
        encryption['athena_token'] = token
        encryption['token_source'] = source
        encryption['dt_registered'] = datetime.now(timezone.utc).isoformat()
        encryption['installation_id'] = installation_id
        conn.encryption = encryption
        conn.save(update_fields=['encryption'])

        # Add to Athena manifest for tamper detection
        try:
            call_command('athena_sign', stdout=self.stdout)
        except Exception:
            pass  # Athena is optional

        return token, source

    def handle(self, *args, **options):
        offline = options['offline']
        fetch_only = options['fetch_only']
        dry_run = options['dry_run']
        force = options['force']
        wchq_url = options['wchq_url']
        bundle_path = options['bundle_path']

        self.stdout.write(self.style.MIGRATE_HEADING('\ndb_init — WebClerk3 database initialization'))

        # ── Step 1: Get the bundle ──────────────────────────────────────

        self.stdout.write('\n── Step 1: Fetch init-bundle ──')
        bundle = None
        source = None

        if not offline:
            # Try Connection record URL first, fall back to default/CLI
            conn_url = _wchq_url_from_connection()
            if conn_url and wchq_url == WCHQ_INIT_BUNDLE_URL:
                wchq_url = conn_url
                self.stdout.write(f'  Using URL from wchq-conn-downstream: {wchq_url}')
            bundle, err = self._fetch_from_wchq(wchq_url)
            if bundle:
                source = 'wchq'
                s_count = len(bundle.get('settings', []))
                r_count = len(bundle.get('reports', []))
                dt = bundle.get('dt_exported', '?')
                self.stdout.write(self.style.SUCCESS(
                    f'  WCHQ bundle: {s_count} settings, {r_count} reports (exported {dt})'
                ))

                # Compare with git bundle to see if WCHQ is newer
                git_bundle, git_err = self._load_git_bundle(bundle_path)
                if git_bundle:
                    git_dt = git_bundle.get('dt_exported', '')
                    wchq_dt = bundle.get('dt_exported', '')
                    if wchq_dt > git_dt:
                        self.stdout.write(f'  WCHQ is newer than git ({wchq_dt} > {git_dt})')
                        if not dry_run:
                            self._save_bundle(bundle, bundle_path)
                    else:
                        self.stdout.write(f'  Git bundle is current ({git_dt})')
            else:
                self.stdout.write(self.style.WARNING(f'  {err}'))
                self.stdout.write('  Falling back to git bundle...')

        if not bundle:
            bundle, err = self._load_git_bundle(bundle_path)
            if bundle:
                source = 'git'
                s_count = len(bundle.get('settings', []))
                r_count = len(bundle.get('reports', []))
                dt = bundle.get('dt_exported', '?')
                self.stdout.write(self.style.SUCCESS(
                    f'  Git bundle: {s_count} settings, {r_count} reports (exported {dt})'
                ))
            else:
                self.stderr.write(self.style.ERROR(f'  {err}'))
                self.stderr.write(self.style.ERROR(
                    '  No init-bundle available. Run seed_freshstart manually, '
                    'then pack_init_bundle to create one.'
                ))
                return

        if fetch_only:
            self.stdout.write(self.style.SUCCESS(
                f'\n  Bundle fetched from {source}. --fetch-only: stopping here.'
            ))
            return

        if dry_run:
            self.stdout.write(f'\n  Would initialize from {source} bundle:')
            self.stdout.write(f'    Settings: {len(bundle.get("settings", []))}')
            self.stdout.write(f'    Reports: {len(bundle.get("reports", []))}')
            self.stdout.write(f'    Then run seed_freshstart')
            self.stdout.write(self.style.SUCCESS('\n  (dry run — nothing changed)'))
            return

        # ── Step 2: Run seed_freshstart ─────────────────────────────────

        self.stdout.write('\n── Step 2: Seed system data ──')
        try:
            cmd_kwargs = {}
            if force:
                cmd_kwargs['force'] = True
            call_command('seed_freshstart', **cmd_kwargs, stdout=self.stdout)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'  seed_freshstart failed: {e}'))
            self.stderr.write('  Continuing with unpack to apply bundle baseline...')

        # ── Step 3: Unpack init-bundle ──────────────────────────────────

        self.stdout.write('\n── Step 3: Unpack init-bundle ──')
        try:
            call_command('unpack_init_bundle', input=bundle_path, stdout=self.stdout)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'  unpack_init_bundle failed: {e}'))
            return

        # ── Step 4: Register with WCHQ ─────────────────────────────────

        self.stdout.write('\n── Step 4: Register installation ──')
        if offline:
            self.stdout.write('  Skipped (offline mode) — register later with:')
            self.stdout.write('    python manage.py db_init --register-only')
        else:
            base_url = wchq_url.rsplit('/wcapi/', 1)[0] if '/wcapi/' in wchq_url else 'https://webclerk.com'
            token, token_source = self._register_with_wchq(base_url)
            if token:
                self.stdout.write(self.style.SUCCESS(
                    f'  Registered ({token_source}). Token: {token[:12]}...'
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f'  Registration failed: {token_source}'
                ))

        # ── Done ────────────────────────────────────────────────────────

        self.stdout.write(self.style.SUCCESS(
            f'\ndb_init complete. Source: {source}. '
            f'Database is ready for company data entry.'
        ))
