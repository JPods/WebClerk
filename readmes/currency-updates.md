# Currency Updates via Connections

<!-- TOC START -->

## Table of Contents

- [Currency Updates via Connections](#currency-updates-via-connections)
  - [Table of Contents](#table-of-contents)
  - [Model Links](#model-links)
  - [Update Flow](#update-flow)
  - [Management Command](#management-command)
  - [Notes](#notes)

<!-- TOC END -->

## Model Links

- `accounts.Currency.connection` → points to `sync.Connection` (provider, e.g., stub/forex)
- `accounts.ExchangeRate.connection` → provenance for a given rate window
- See also: `readmes/exchanges-architecture.md` for model boundaries (sync logs vs FX rates vs transactions).

## Update Flow

1. Select active currencies with a provider connection.
2. Call provider adapter (stubbed) to fetch latest rates.
3. Store time-windowed rates in `accounts.ExchangeRate` with `currency_base`, `currency_target`, and `rate`.

## Management Command

```bash
python manage.py update_currencies --provider stub --limit 50
```

## Notes

- Provider adapters are stubbed; production integrations can be added behind connection config.
- Exchange records are additive and constrained by a uniqueness window.
