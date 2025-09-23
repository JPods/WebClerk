# wcapi Routing

Centralized under `apps/core/wcapi/urls.py`.

Patterns

- Open query: /wcapi/&lt;model&gt;/_query
- Save query: /wcapi/&lt;model&gt;/_query/save
- Saved sets: /wcapi/&lt;model&gt;/_sets, /wcapi/&lt;model&gt;/_sets/&lt;ident&gt;
- Catch‑all (push, etc.): /wcapi/&lt;model&gt;, /wcapi/&lt;model&gt;/&lt;extra&gt;

Verify (preferred; requires django-extensions)

- source bin/activate
- source bin/activate
- pip install django-extensions
- add "django_extensions" to INSTALLED_APPS

Verify (no extra deps)

- python manage.py shell -c 'from django.urls import resolve; print(resolve("/wcapi/contact/_query/save"))'

Verify (no extra deps)
Compliance scan

- python manage.py wcapi_lint

Compliance scan

- python manage.py wcapi_lint
- JSON: python manage.py wcapi_lint --json
- Exemptions must include owner and reason within 5 lines above the path:
  - `# WCAPI-NONCOMPLIANT owner=alice reason=temporary shim`
  - `# wcapi exempt responsible=bob@example.com reason=3rd-party callback`

# WCAPI Notes

## Search & Write Guards

Optional middleware/guards to centralize free‑text search control and write gating. Defaults prioritize developer velocity; enable in production as needed.

- Search Guard (?q= on list)
  - Default: disabled.
  - Enable: add `common.middleware.WCAPISearchGuardMiddleware` to MIDDLEWARE and set `WCAPI_Q_GUARD_ENABLED = True` in settings.
  - Effect: For blessed wcapi models, non‑staff requests with `?q=` return 403.
  - View hook: RESTModelRouterView only enforces staff‑only `?q=` when `WCAPI_Q_GUARD_ENABLED` is true; prefer the middleware for centralized policy.

- Write Gate (centralized write allowlist)
  - Default: disabled; bypassed during pytest.
  - Enable: set `WRITE_GATE_ENABLED = True` and add `common.middleware.WriteGateMiddleware` to MIDDLEWARE.
  - Configure allowlist with `WRITE_GATE_EXACT_PATHS`, `WRITE_GATE_PREFIXES`, `WRITE_GATE_ALLOWED_REGEX`.

Example (production):

```python
MIDDLEWARE = [
    # ...
    'common.middleware.WriteGateMiddleware',
    'common.middleware.WCAPISearchGuardMiddleware',  # optional
    # ...
]
WCAPI_Q_GUARD_ENABLED = True
WRITE_GATE_ENABLED = True
```
