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
