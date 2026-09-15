"""
audit_connections — Verify Connection records are real, not hallucinated.

Checks:
  LIVE     — endpoint responds with 2xx
  DEAD     — endpoint returns 4xx/5xx or times out
  PHANTOM  — endpoint configured but connection never used (times_used == 0)
  NO_URL   — connection has no endpoint configured

Usage:
    python manage.py audit_connections                # summary
    python manage.py audit_connections --verify       # ping all endpoints
    python manage.py audit_connections --detail       # show full config
    python manage.py audit_connections --json         # JSON for Alice
"""
import json as json_mod
import logging
import urllib.request
import urllib.error

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Audit Connection records — verify endpoints exist and are reachable'

    def add_arguments(self, parser):
        parser.add_argument('--verify', action='store_true',
                            help='Actually ping configured endpoints (HTTP HEAD)')
        parser.add_argument('--detail', action='store_true', help='Show full connection config')
        parser.add_argument('--json', action='store_true', help='JSON output for Alice')
        parser.add_argument('--timeout', type=int, default=10,
                            help='HTTP timeout in seconds (default: 10)')

    def _extract_endpoints(self, conn):
        """Extract all URL endpoints from a Connection's config."""
        config = conn.config or {}
        urls = []

        # Direct endpoint field
        endpoint = config.get('endpoint', '')
        if endpoint and endpoint.startswith('http'):
            urls.append(('endpoint', endpoint))

        # Named endpoints dict
        base_url = config.get('wchq_base_url', '').rstrip('/')
        endpoints = config.get('endpoints', {})
        for name, path in endpoints.items():
            if path:
                url = f"{base_url}{path}" if base_url and not path.startswith('http') else path
                if url.startswith('http'):
                    urls.append((name, url))

        return urls

    def _check_endpoint(self, url, timeout=10):
        """HTTP HEAD to check if endpoint is reachable. Returns (status_code, error_msg)."""
        try:
            req = urllib.request.Request(
                url, method='HEAD',
                headers={'User-Agent': 'WebClerk3-audit/1.0'},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, None
        except urllib.error.HTTPError as e:
            return e.code, str(e.reason)
        except urllib.error.URLError as e:
            return 0, str(e.reason)
        except Exception as e:
            return 0, str(e)

    def handle(self, *args, **options):
        from apps.sync.models.connection import Connection

        verify = options.get('verify', False)
        detail = options.get('detail', False)
        as_json = options.get('json', False)
        timeout = options.get('timeout', 10)

        connections = Connection.objects.filter(is_active=True).order_by('type', 'name')

        results = []
        flags = []

        for conn in connections:
            endpoints = self._extract_endpoints(conn)
            entry = {
                'ida': conn.ida,
                'name': conn.name,
                'type': conn.type,
                'status': conn.status,
                'purpose': conn.purpose or '',
                'times_used': conn.times_used,
                'dt_last_used': conn.dt_last_used,
                'endpoints': [],
                'flags': [],
            }

            if not endpoints:
                entry['flags'].append('NO_URL')
                flags.append({
                    'connection': conn.ida,
                    'flag': 'NO_URL',
                    'detail': f'{conn.name} — no endpoints configured',
                })

            if conn.times_used == 0:
                entry['flags'].append('PHANTOM')
                flags.append({
                    'connection': conn.ida,
                    'flag': 'PHANTOM',
                    'detail': f'{conn.name} — never used (times_used=0)',
                })

            if verify:
                for ep_name, ep_url in endpoints:
                    status_code, error = self._check_endpoint(ep_url, timeout)
                    live = 200 <= status_code < 400
                    ep_result = {
                        'name': ep_name,
                        'url': ep_url,
                        'status_code': status_code,
                        'live': live,
                        'error': error,
                    }
                    entry['endpoints'].append(ep_result)
                    if not live:
                        entry['flags'].append(f'DEAD:{ep_name}')
                        flags.append({
                            'connection': conn.ida,
                            'flag': 'DEAD',
                            'detail': f'{conn.name}.{ep_name} — {ep_url} → {status_code} {error or ""}',
                        })

            results.append(entry)

        # ── Output ──
        if as_json:
            output = {
                'connections': len(results),
                'flags': flags,
                'results': results,
            }
            self.stdout.write(json_mod.dumps(output, indent=2, default=str))
            return

        # Summary
        live_count = sum(1 for r in results if not r['flags'])
        phantom_count = sum(1 for f in flags if f['flag'] == 'PHANTOM')
        dead_count = sum(1 for f in flags if f['flag'] == 'DEAD')
        no_url_count = sum(1 for f in flags if f['flag'] == 'NO_URL')

        self.stdout.write(self.style.SUCCESS(
            f"\nConnection audit: {len(results)} connections"
        ))
        self.stdout.write(f"  Clean: {live_count}")
        if phantom_count:
            self.stdout.write(f"  PHANTOM (never used): {phantom_count}")
        if dead_count:
            self.stdout.write(f"  DEAD (endpoint unreachable): {dead_count}")
        if no_url_count:
            self.stdout.write(f"  NO_URL (no endpoints): {no_url_count}")

        # Detail
        self.stdout.write("\n  ── Connections ──\n")
        for r in results:
            flag_str = f"  [{', '.join(r['flags'])}]" if r['flags'] else ''
            self.stdout.write(
                f"  {r['ida']:<30} {r['type']:<10} "
                f"status={r['status']:<8} "
                f"used={r['times_used']}{flag_str}"
            )
            if detail:
                for ep in r.get('endpoints', []):
                    icon = '✓' if ep['live'] else '✗'
                    self.stdout.write(
                        f"    {icon} {ep['name']}: {ep['url']} → {ep['status_code']}"
                    )

        if flags and not verify:
            self.stdout.write(self.style.WARNING(
                "\n  Run with --verify to ping endpoints and check for DEAD connections."
            ))
