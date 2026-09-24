def assert_envelope(body, *, expect_status=None):
    """Assert body matches the standard API envelope.

    expect_status: optional expected status ('success','fail','error').
    Returns body['data'] for convenience.
    """
    assert isinstance(body, dict), f"Body not dict: {body!r}"
    for key in ('status','code','message','data'):
        assert key in body, f"Missing key {key} in envelope: {body.keys()}"
    assert body['status'] in ('success','fail','error'), body['status']
    if expect_status:
        assert body['status'] == expect_status, body
    if body['status'] == 'success':
        assert body.get('error') in (None, {}), body.get('error')
    else:
        assert isinstance(body.get('error'), dict), body
    data = body.get('data')
    if data is None:
        data = {}
    return data


def wcapi_save(client, data=None, **kwargs):
    """A REST save, as the frontend makes it: POST /wcapi/<model>/ creates, PUT
    /wcapi/<model>/<id>/ updates. The body (a dict, or JSON text) names both."""
    import json
    body = json.loads(data) if isinstance(data, (str, bytes)) else (data or {})
    model, rid = body['model_name'], body.get('id')
    if rid:
        return client.put(f'/wcapi/{model}/{rid}/', data, **kwargs)
    return client.post(f'/wcapi/{model}/', data, **kwargs)


def wcapi_get(client, params=None, **kwargs):
    """A REST read: GET /wcapi/<model>/ with criteria, or GET /wcapi/<model>/<id>/. The
    params name the model (model_name) and, for one record, its id."""
    params = dict(params or {})
    model, rid = params.pop('model_name'), params.pop('id', None)
    path = f'/wcapi/{model}/{rid}/' if rid else f'/wcapi/{model}/'
    return client.get(path, params, **kwargs)
