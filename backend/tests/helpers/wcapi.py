# Canonical test helpers (model-key routing only)

from typing import Any, Dict, Optional
from rest_framework.test import APIClient

def api_list(client: APIClient, model: str):
    return client.get(f'/{model}/')

def api_detail(client: APIClient, model: str, pk: Any):
    return client.get(f'/{model}/{pk}/')

def api_create(client: APIClient, model: str, data: Dict[str, Any]):
    return client.post('/wcapi/save', {'model': model, 'data': data}, format='json')

def api_update(client: APIClient, model: str, pk: Any, data: Dict[str, Any]):
    return client.post(f'/{model}/{pk}/', {'data': data}, format='json')

def api_delete_one(client: APIClient, model: str, pk: Any):
    return client.delete(f'/{model}/{pk}/')

def api_delete_batch_ids(client: APIClient, model: str, ids: list[int]):
    return client.delete(f'/{model}/', data={'ids': ids}, format='json')

def api_query(client: APIClient, model: str, filters: Optional[Dict[str, Any]] = None):
    return client.post('/wcapi/query', {'model': model, 'filters': filters or {}}, format='json')