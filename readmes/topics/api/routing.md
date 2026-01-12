# Routing Guide (wcapi)

This project exposes a settings‑driven, model‑routed API under `/wcapi/<model>/...`.

Current URL patterns
- apps/core/wcapi/urls.py (loaded by apps/core/urls.py)

```python
# apps/core/wcapi/urls.py (excerpt)
from django.urls import path
from apps.core.wcapi.views_query import RESTOpenQueryView, RESTSavedSetView
from apps.core.wcapi.views import RESTModelRouterView

urlpatterns = [
    # Open-query run and save
    path("wcapi/<str:model>/_query", RESTOpenQueryView.as_view(), name="wcapi-open-query"),
    path("wcapi/<str:model>/_query/save", RESTOpenQueryView.as_view(), {"action": "save"}, name="wcapi-open-query-save"),

    # Saved sets
    path("wcapi/<str:model>/_sets", RESTSavedSetView.as_view(), name="wcapi-saved-sets"),
    path("wcapi/<str:model>/_sets/<str:ident>", RESTSavedSetView.as_view(), name="wcapi-saved-sets-item"),

    # Catch-all model router (covers push and other actions)
    path("wcapi/<str:model>", RESTModelRouterView.as_view(), name="wcapi-model-root"),
    path("wcapi/<str:model>/<path:extra>", RESTModelRouterView.as_view(), name="wcapi-model-extra"),
]
```

Notes on ordering
- Specific routes (`_query`, `_sets`) are listed before the catch‑alls to avoid collisions.
- The catch‑all routes ensure endpoints like `/wcapi/<model>/push` reach `RESTModelRouterView`.

Verify routes (preferred)
- Requires django-extensions:
  - source bin/activate
  - pip install django-extensions
  - Add "django_extensions" to INSTALLED_APPS
  - python manage.py show_urls | grep wcapi

Verify routes (no extra deps)
- source bin/activate
- python manage.py shell -c 'from django.urls import resolve; print(resolve("/wcapi/contact/_query/save"))'
- python manage.py shell -c 'from django.urls import resolve; print(resolve("/wcapi/contact/push"))'

Quick curl checks (while server is running)
- curl -I http://localhost:8000/wcapi/contact/_query
- curl -I http://localhost:8000/wcapi/contact/_query/save
- curl -I http://localhost:8000/wcapi/contact/push  # expect 200/405, not 404