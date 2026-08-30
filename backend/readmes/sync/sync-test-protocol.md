# Sync Test Protocol

**Purpose:** Validate that two WebClerk3 instances can exchange bundles reliably, including retry on failure.

**Alice uses this protocol to coach users through their first connection.**

---

## Step 1: Create the Connection (both machines)

On Machine A (sender):
```bash
python manage.py sync_setup connect \
  --name "A-to-B" \
  --endpoint http://<machine-b-ip>:8000/wcapi/sync/receive/
```

This generates a shared key. Copy it.

On Machine B (receiver), use the **same key**:
```bash
python manage.py sync_setup connect \
  --name "A-to-B" \
  --endpoint http://<machine-a-ip>:8000/wcapi/sync/receive/ \
  --key "<paste key from Machine A>"
```

One connection record, one key, bidirectional.

---

## Step 2: Send a test bundle

On the sending machine:
```bash
python manage.py sync_setup test --connection "A-to-B"
```

This creates a `Pending` record with:
- `purpose = "sync.bundle_out"`
- `config.test = true`
- `config.echo = "handshake"`

---

## Step 3: Process (or wait for Celery)

Process immediately:
```bash
python manage.py sync_setup process
```

Or wait for the next Celery Beat cycle (hourly).

---

## Step 4: Verify

Check status on the sender:
```bash
python manage.py sync_setup status
```

**If receiver was online:** Pending shows `dt_processed > 0`, changes log shows `"result": "success"`.

**If receiver was offline:** Pending stays `dt_processed = 0`, attempts increment, changes log shows each failed attempt with timestamp. Run `process` again after starting the receiver.

---

## Step 5: Confirm on the receiver

On the receiving machine, check for the incoming Bundle:
```bash
python manage.py shell -c "
from apps.sync.models.bundle import Bundle
for b in Bundle.objects.order_by('-dt_created')[:5]:
    print(f'{b.id} {b.direction} {b.status} test={b.payload.get(\"test\", False)}')
"
```

A Bundle with `direction=pull` and `test=True` confirms delivery.

---

## What the test proves

1. **Key authentication works** — invalid keys are rejected with 403
2. **Payload round-trip** — the `echo` value sent matches the `echo` in the ack
3. **Retry works** — if the receiver is offline, attempts accumulate; delivery completes on the first successful retry
4. **Audit trail** — every attempt is logged in `pending.changes` with timestamp, attempt number, and outcome
5. **Connection health** — patterns in the changes log reveal connectivity windows (e.g., always fails 2-8 AM = machine is asleep)

---

## Alice's coaching role

When a user creates a new Connection, Alice should:

1. **Suggest the test** — "I see you created a new connection. Want me to send a test handshake?"
2. **Create the Pending** — purpose=sync.bundle_out, test=true, echo="handshake"
3. **Monitor the result** — check dt_processed after the next Celery cycle
4. **Report back** — "Handshake with [connection name] succeeded in [N] attempts" or "Still pending after [N] attempts — is the other machine running?"
5. **Learn from patterns** — if a connection consistently fails at certain hours, note it and stop wasting attempts during those windows
