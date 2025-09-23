# wcapi Routing

Centralized under `apps/core/wcapi/urls.py`.

Patterns
- Open query: /wcapi/<model>/_query
- Save query: /wcapi/<model>/_query/save
- Saved sets: /wcapi/<model>/_sets, /wcapi/<model>/_sets/<ident>
- Catch‑all (push, etc.): /wcapi/<model>, /wcapi/<model>/<extra>

Verify (preferred; requires django-extensions)
- source bin/activate
- pip install django-extensions
- add "django_extensions" to INSTALLED_APPS
- python manage.py show_urls | grep wcapi

Verify (no extra deps)
- python manage.py shell -c 'from django.urls import resolve; print(resolve("/wcapi/contact/_query/save"))'
- python manage.py shell -c 'from django.urls import resolve; print(resolve("/wcapi/contact/push"))'

Compliance scan
- python manage.py wcapi_lint
- JSON: python manage.py wcapi_lint --json
- Exemptions must include owner and reason within 5 lines above the path:
  - # WCAPI-NONCOMPLIANT owner=alice reason=temporary shim
  - # wcapi exempt responsible=bob@example.com reason=3rd-party callback