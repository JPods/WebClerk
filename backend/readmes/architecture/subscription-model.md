# WebClerk Subscription Model

## Principle

WebClerk is free and open source (Apache-2.0). Always. The software is the gift.
The subscription funds Alice cloud AI and a direct support channel — priced by
how many people use it, not by features.

## Pricing

**$14/month per 5 staff users.** Alice counts `is_staff=True, is_active=True` in
the database and reports monthly to WCHQ. Price adjusts automatically.

| Staff Users | Monthly |
|-------------|---------|
| 1-5 | $14 |
| 6-10 | $28 |
| 11-15 | $42 |
| 20 | $56 |
| 50 | $140 |
| 100 | $280 |

No tiers. No feature matrix. No upsell. One product, one price rule.

## Two Modes

| Mode | Cost | What you get |
|------|------|-------------|
| **Community** | Free | Full WebClerk + Alice algorithms (Tier 1). Run your own Ollama for AI. |
| **Subscribed** | $14/5 users | Everything in Community + Alice cloud AI + direct support channel. No Ollama needed. |

## How It Works

### Registration

1. User installs WebClerk (free, `git clone` + `install.sh`)
2. First run → onboarding at `/setup`
3. Name, email, company → goals, pain points → subscribe or community
4. POST to `webclerk.com/wcapi/register-installation/`
5. WCHQ creates: Contact, Customer, Connection (with Athena token)
6. Local stores: Athena token in `wc:subscription` Setting

### Monthly Reporting

Alice runs a nightly task that counts staff users:

```python
User.objects.filter(is_staff=True, is_active=True).count()
```

Monthly, Alice reports the count to WCHQ via the Athena-authenticated
connection. WCHQ calculates the price and bills accordingly.

The user never enters a number. The system knows.

### Alice LLM Fallback

When a user calls Alice for AI help:

1. **Try local Ollama** — free, private, no network
2. **If Ollama unavailable and subscribed** → call WCHQ shared LLM
3. **If neither available** → Alice still works (Tier 1 algorithms)

The WCHQ LLM endpoint receives the *prompt*, not raw commerce data.
Alice formulates the question locally from local data, sends the question,
gets the response. WCHQ never sees the raw business data.

### Support Channel

Subscribers get a direct messaging channel powered by WebClerk's own
Touch + Action model. User creates a Touch → becomes an Action on WCHQ →
team responds → Touch back. Tracked, accountable, proves the product.

### Donations

Anyone can donate — one-time, any amount. Independent of subscription.
Supporters, not subscribers.

## Large Companies

A company with 500 employees doesn't buy one enterprise license. They run
10-20 independent WebClerk installations — one per department, division,
or location. Each installation:

- Registers independently
- Has its own Athena token
- Pays $14 per 5 staff users in that installation
- Links journals across installations via Connection/Bundle

A department of 25 pays $70/mo. The company total across all installations
might be $700/mo — but each department owns its own decision. Bottom-up,
not top-down. Each installation is sovereign.

No volume discount needed. No enterprise sales call. No contract.

## Revenue Streams

| Stream | Source | What it funds |
|--------|--------|---------------|
| Subscription | $14/5 users/mo | Alice cloud LLM compute + support |
| Support channel | Included in subscription | Team response time |
| Donations | Voluntary, any amount | The project |
| WebClerk software | $0 | Nothing — it's the gift |

## Files

- `apps/core/views/register_installation_view.py` — registration + subscription endpoints
- `apps/ai_assistant/services/ollama_client.py` — LLM fallback with subscription check
- `frontend/src/pages/Onboarding.tsx` — 3-step setup wizard at `/setup`
- `webclerk3_api/settings.py` — `CELERY_BEAT_SCHEDULE` for Alice reporting

## The Philosophy

WebClerk is free because access to commerce tools should not be gated by
ability to pay. The subscription exists because running LLM infrastructure
costs real money. Users who can run their own Ollama pay nothing. Users who
can't (or don't want to) pay for the convenience of shared infrastructure.

The price scales with value received — more people using it, more value,
proportionally more cost. Not more features, not artificial tiers, not
negotiated contracts. Math.
