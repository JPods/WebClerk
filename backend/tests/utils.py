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
    """A REST save, as the frontend makes it. An update is PUT /wcapi/<model>/<id>/. A create
    is the frontend's createRecord: POST /wcapi/<model>/ (`new`, no values) makes the empty
    record, then the values are its first save, PUT to its id (Bill, 2026-09-26). The test
    names the model (model_name) and, for an update, the id; both go in the path, the fields
    go flat in the body. A refused `new` is returned as it came."""
    import json
    as_text = isinstance(data, (str, bytes))
    body = json.loads(data) if as_text else dict(data or {})
    model, rid = body.pop('model_name'), body.pop('id', None)
    from apps.core.services.behaviours import behaviour_for
    # new takes the signals and the fields the model cannot exist without; the rest is the save.
    takes = set(behaviour_for(model).NEW_REQUIRES)
    signals = {k: body.pop(k) for k in [k for k in body if k.startswith('_') or k in takes]}
    if not rid:
        made = client.post(f'/wcapi/{model}/', signals, content_type='application/json')
        if made.status_code >= 400 or not body:
            return made
        rid = made.json()['data']['id']
    if as_text:
        body = json.dumps(body)
    return client.put(f'/wcapi/{model}/{rid}/', body, **kwargs)


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


def received_receipt_line(receipt, **fields):
    """A receipt line planned, then received by the receipt's receive command: nothing else sets a
    receipt line's received quantity (Bill, 2026-09-30). ``quantity.active`` is what is received."""
    from apps.transactions.models import ReceiptLine
    from apps.transactions.services.receive_commands import receive_receipt
    quantity = dict(fields.pop('quantity', None) or {})
    active = float(quantity.pop('active', 0) or 0)
    quantity['staged'] = max(float(quantity.get('staged') or 0), active)
    quantity['active'] = 0
    line = ReceiptLine.objects.create(receipt=receipt, quantity=quantity, **fields)
    if active:
        receive_receipt(receipt, lines=[{'line_id': line.pk, 'qty': active}])
    line.refresh_from_db()
    return line
