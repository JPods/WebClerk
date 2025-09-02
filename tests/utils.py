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
