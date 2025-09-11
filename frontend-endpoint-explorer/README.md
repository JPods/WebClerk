# Endpoint Explorer (React Prototype)

Minimal React + Vite tool to:

1. List all API endpoints (expects backend helper endpoint at `/wcapi/endpoints/`).
2. List all allowed `model_name` values (`/wcapi/model-names/`).
3. Show fields for a specific model (`/wcapi/model-fields/?model_name=...`).

## Backend Alignment
Provide lightweight JSON endpoints (example Django view stubs):

```python
# urls.py
path('wcapi/model-names/', list_model_names),
path('wcapi/endpoints/', list_endpoints),
path('wcapi/model-fields/', model_fields),
```

```python
from django.http import JsonResponse
from common.api_responses import api_response
from apps.core.services.wcapi_registry import MODEL_MAP

ENDPOINTS = [
  '/wcapi/manage/', '/wcapi/query/', '/wcapi/save/',
  '/tx/proposals/', '/tx/proposal-lines/', '/tx/lines/aggregate/'
]

def list_model_names(request):
    return api_response(data=sorted(MODEL_MAP.keys()))

def list_endpoints(request):
    return api_response(data=ENDPOINTS)

def model_fields(request):
    name = request.GET.get('model_name')
    if name not in MODEL_MAP:
        return api_response(status='error', message='Unknown model', error={'code':'invalid_model'})
    model = MODEL_MAP[name]
    fields = [f.name for f in model._meta.get_fields() if getattr(f, 'attname', None)]
    return api_response(data=fields)
```

## Run

```bash
cd frontend-endpoint-explorer
npm install
npm run dev
```

Environment override:

```bash
VITE_API_BASE=http://localhost:8000 npm run dev
```

## Next Enhancements
- Search filter on endpoints & models
- Field metadata (type, nullability)
- Copy-as-cURL button
- Error code legend panel
- Caching + stale-while-revalidate
- Dark mode toggle
- Export JSON snapshot
