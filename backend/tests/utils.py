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
    /wcapi/<model>/<id>/ updates. The test names the model (model_name) and, for an update,
    the id; both go in the path and the fields go flat in the body, as the door requires."""
    import json
    body = json.loads(data) if isinstance(data, (str, bytes)) else dict(data or {})
    model, rid = body.pop('model_name'), body.pop('id', None)
    if isinstance(data, (str, bytes)):
        body = json.dumps(body)
    if rid:
        return client.put(f'/wcapi/{model}/{rid}/', body, **kwargs)
    return client.post(f'/wcapi/{model}/', body, **kwargs)


def wcapi_get(client, params=None, **kwargs):
    """A REST read: GET /wcapi/<model>/ with criteria, or GET /wcapi/<model>/<id>/. The
    params name the model (model_name) and, for one record, its id."""
    params = dict(params or {})
    model, rid = params.pop('model_name'), params.pop('id', None)
    path = f'/wcapi/{model}/{rid}/' if rid else f'/wcapi/{model}/'
    return client.get(path, params, **kwargs)


def save_document(model_key, header_data, lines_data, actor=None):
    """Save a document with its lines through the door, as every channel does.

    Returns what the old transaction endpoint answered — ``header.id``, the created lines'
    ids in order, and ``action`` — plus the door's ``SaveResult``.
    """
    from apps.core.services.door import Actor
    from apps.core.services.save import save_record
    from apps.core.services.save_line_processing import LINE_MODEL_MAP
    from apps.core.utils import registry

    line_name, fk = LINE_MODEL_MAP[model_key]
    LineModel = registry.resolve(line_name.lower())
    header_id = header_data.get('id')
    before = set(LineModel.objects.filter(**{f'{fk}_id': header_id})
                 .values_list('pk', flat=True)) if header_id else set()
    result = save_record(actor or Actor.system(source='test'),
                         {**header_data, 'lines': list(lines_data)}, model_key=model_key)
    created = (LineModel.objects.filter(**{f'{fk}_id': result.obj_id})
               .exclude(pk__in=before).order_by('pk').values_list('pk', flat=True))
    return {'header': {'id': result.obj_id}, 'lines': [{'id': pk} for pk in created],
            'action': 'created' if result.created else 'updated', 'result': result}
