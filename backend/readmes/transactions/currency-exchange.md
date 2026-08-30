# Currency & Exchange Rates

## Architecture — Three Model Boundaries

We explicitly separate three concerns:

### 1. Sync Exchanges (Operational Audit)

- **Models**: `sync.Connection` and `sync.Bundle`
- **Purpose**: Integration/sync. `Connection` defines an external provider or partner; `Bundle` logs each exchange (direction, payload, mappings, responses).
- **Tables**: `connections`, `exchanges` (sync app)
- **Usage**: Tracks exchanges for Items, Currencies, etc.; not FX rates.

### 2. Currency Catalog & FX Rates (Reference Data)

- **Models**: `accounts.Currency` and `accounts.ExchangeRate`
- **Purpose**: Currency catalog and time-windowed FX rates.
- `Currency.connection` optionally points to `sync.Connection` to source updates.
- `ExchangeRate` stores base→target, `rate`, `dt_start`/`dt_end`, and `connection` provenance.
- **Tables**: `acct_currencies`, `acct_exchange_rates` (accounts app)

### 3. Monetary Transactions (Planned)

- **Model**: `accounts.Bundle` (planned future shape)
- **Purpose**: Monetary exchange/settlement transaction (amounts_in/out, fees, references, currencies).
- **Note**: Rate history lives in `ExchangeRate` and should not be conflated with transactions.

---

## Update Flow

1. Select active currencies with a provider connection.
2. Call provider adapter (stubbed) to fetch latest rates.
3. Store time-windowed rates in `accounts.ExchangeRate` with `currency_base`, `currency_target`, and `rate`.

FX updates create/update `accounts.ExchangeRate` records using the provider behind `Currency.connection`.
Sync logging calls through `sync.Connection` create `sync.Bundle` rows for operational audit, independent of FX rates.

### Management Command

```bash
python manage.py update_currencies --provider stub --limit 50
```

Provider adapters are stubbed; production integrations can be added behind connection config. Bundle records are additive and constrained by a uniqueness window.

---

## Review Workflow

Foreign/provider data is not applied automatically. Each `sync.Bundle` created by an integration has a `response.review.status` field that starts as `pending`. An authorized reviewer must accept or reject the bundle before changes are committed to core records.

### Workflow (email verification example)

1. A Celery task performs verification and creates a `Bundle` with `response.review.status: pending` and `response.provider/status/deliverability` populated.
2. A reviewer accepts or rejects the bundle (admin actions provided). On acceptance, the decision service updates the target record and marks the `Bundle` as `accepted` (or `rejected`).

### Admin

Use the Bundles admin to bulk accept/reject. Actions call `apps.sync.services.decisions.accept_email_verification` or `reject_exchange`.

### Notes

- No migrations required; decision state is stored in JSON fields.
- Extend the decision services for other resource types by adding targeted `accept_*` functions.

---

## Future Work

- Consider renaming `accounts.Bundle` to `ExchangeTransaction` to avoid ambiguity.
- Add admin/serializers for `ExchangeRate` and later for `Bundle` transactions.
- Introduce periodic tasks to refresh FX rates for active currencies.
