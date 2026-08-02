# WC_HQ — WebClerk Headquarters

**Your store is yours. WC_HQ is the library.**

---

## What WC_HQ Is

WC_HQ is a service provider to your WebClerk installation — not an owner, not a controller, not a platform. Your data stays on your machine. WC_HQ provides library services that make your data better.

Think of it like a public library:
- You own your books (your data)
- The library lends you books you don't have (product data, supplier connections, improved defaults)
- You choose which books to borrow (you control what syncs)
- The library never takes your books (your data never leaves without your permission)
- You can stop going to the library anytime (disconnect with one click)

---

## What WC_HQ Provides

| Service | What you get | What WC_HQ gets |
|---------|-------------|-----------------|
| **Product data library** | Normalized product data from suppliers — descriptions, images, pricing, specs | Nothing — this flows one way, down to you |
| **Distribution agreements** | Landed costs, terms, availability from your suppliers | Nothing — negotiated by your supplier |
| **Improved defaults** | Better field layouts, Alice coaching tips, refs policies that other users found useful | Your anonymized usage patterns (which layouts you use, which refs fields you query) |
| **Email validation** | ZeroBounce or other provider — validates your contact emails | Nothing — your contacts stay local |
| **Software updates** | New features, bug fixes, security patches | Nothing |
| **Alice coaching library** | Training documents, QA templates, onboarding checklists | Your anonymized coaching feedback (what worked, what didn't) |

---

## What WC_HQ Does NOT Do

- **Does NOT store your data.** Your contacts, orders, invoices, inventory — all on your machine.
- **Does NOT see your customers.** Customer names, emails, purchase history — never leaves your installation.
- **Does NOT control your store.** You can disconnect from WC_HQ and everything still works.
- **Does NOT charge for the software.** WebClerk is open source. WC_HQ charges for library services only.
- **Does NOT require an account.** You can run WebClerk without ever connecting to WC_HQ.
- **Does NOT sell your data.** Ever. To anyone. This is a constitutional commitment, not a terms-of-service promise.

---

## Your Choices — The Connection Setting

Every WC_HQ relationship is controlled by a Connection record in your sync app. You set the terms.

### Connection Levels

| Level | What syncs TO you | What syncs FROM you | Monthly cost |
|-------|------------------|--------------------|-----------:|
| **Disconnected** | Nothing | Nothing | Free |
| **Read-only** | Product data, software updates | Nothing | Free |
| **Standard** | Product data, improved defaults, Alice coaching | Anonymized usage patterns | $29 |
| **Full** | Everything above + distribution agreements, email validation, cross-company sync | Usage patterns + anonymized refs policies | $99 |
| **HQ Services** | Everything above + campaign collaboration, manufacturer sync | Usage patterns + order summaries (no customer PII) | $299 |

### How to Change Your Level

In WebClerk:
1. Go to DataBrowser → Connection model
2. Find your WC_HQ connection
3. Change `sync_level` to your preference
4. Changes take effect immediately

Or ask Alice: *"Alice, disconnect from WC_HQ"* or *"Alice, change WC_HQ to read-only."*

### What "Anonymized" Means

When we say "anonymized usage patterns," we mean:
- ✅ "A user with 500 contacts uses the 3-column layout for the contact model" 
- ❌ NOT "Bill James at JPods uses the 3-column layout"
- ✅ "An installation queries refs.keywords 40 times/day on the action model"
- ❌ NOT "This installation's action records contain these keywords"

Your identity is never attached to usage data. WC_HQ sees patterns, not people.

---

## The Sync App — How It Works

### Connection Model

```
Connection:
  ida: "wchq-standard"
  provider: "wchq"
  sync_level: "standard"
  sync_frequency: "daily"
  last_sync_dt: 1785100000000
  config: {
    publish_refs_policy: true,
    publish_usage_patterns: true,
    publish_coaching_feedback: true,
    publish_order_summaries: false,
    receive_product_data: true,
    receive_defaults: true,
    receive_coaching: true,
    auto_update_software: false
  }
```

Every field in `config` is a toggle you control. Set `publish_refs_policy: false` and your refs policies stay local. Set `receive_defaults: false` and WC_HQ defaults don't overwrite yours.

### Bundle Model

Each sync exchange is a Bundle — a timestamped package of data with an audit trail:

```
Bundle:
  connection_id: 42
  direction: "down"  (from WC_HQ to you)
  dt_sent: 1785100000000
  status: "applied"
  content_type: "product_data"
  record_count: 150
  config: {
    supplier: "Acme Corp",
    catalog_version: "2026-07"
  }
```

You can see every Bundle in DataBrowser. Every piece of data that came from or went to WC_HQ is logged. No invisible transfers.

---

## Refs Policy Publishing

When you set a refs policy Setting for a model (e.g., `refs_policy:contact`), Alice can publish it to WC_HQ:

**What gets published:**
```json
{
  "model": "contact",
  "keywords": {"source_fields": ["attention", "company"], "max": 20},
  "links": {"contact": {"cache_fields": ["attention", "email"]}},
  "installation_size": "medium"  (anonymized: small/medium/large)
}
```

**What does NOT get published:**
- Your actual keywords or data
- Your contact names, emails, or records
- Your installation ID or location

**Why publish?** WC_HQ aggregates refs policies across hundreds of installations. If 80% of medium-sized businesses cache `attention` and `email` on contact refs, that becomes the improved default for new installations. Your Alice helped the next Alice start smarter.

**How to opt out:** Set `publish_refs_policy: false` in your WC_HQ Connection config.

---

## The Improvement Loop

```
Your installation
    │
    ├── Alice follows your refs policy
    │   (cache keywords, maintain links, refresh on save)
    │
    ├── Alice observes what's useful
    │   (which refs fields are queried, which are ignored)
    │
    ├── If publish_refs_policy: true
    │   → anonymized policy sent to WC_HQ
    │
    ▼
WC_HQ aggregates across all installations
    │
    ├── "80% of retail businesses cache these 5 fields on item refs"
    ├── "This coaching document has 90% positive feedback"
    ├── "This DataBrowser layout is used by 60% of users"
    │
    ▼
Improved defaults flow back via sync Bundle
    │
    ├── Your Alice gets smarter defaults
    ├── New installations start with proven patterns
    └── You can accept, modify, or reject any default
```

**The principle:** Every installation that participates makes every other installation better. n² — the value is in the number of connections. But participation is voluntary. Disconnected installations work fine. They just don't benefit from the collective learning.

---

## Desktop Hosting — The Foundation

WC_HQ is built on the Desktop Hosting model (Bill James, Wiley 2002):

- **Your machine is the server.** A Mac Mini + Cloudflare = enterprise-grade hosting.
- **Your data is sovereign.** No platform owns your customer relationships.
- **WC_HQ is a library, not a landlord.** You borrow services, you don't rent permission to operate.
- **Disconnecting is free.** No export fees, no data hostage, no degraded service. Everything still works.

This is the opposite of Shopify, Amazon, and Yelp. Those platforms own the relationship between you and your customer. WebClerk puts that relationship back where it belongs — with you.

Apple understood this in 2002 when they invited Bill James on two national tours to present Desktop Hosting. The Internet was supposed to empower individuals. WC_HQ ensures it still can.

---

## FAQ

**Q: What happens if WC_HQ goes down?**
A: Nothing. Your store keeps running. WC_HQ is a service you use, not infrastructure you depend on. When WC_HQ comes back, sync resumes.

**Q: Can I run multiple WebClerk installations?**
A: Yes. Each has its own Connection to WC_HQ. A business with 3 locations has 3 installations, each sovereign.

**Q: Can I sync with another WebClerk installation directly?**
A: Yes. The Connection/Bundle model works peer-to-peer, not just hub-and-spoke. Two businesses can sync inventory, product data, or order summaries directly.

**Q: Who sees my sync data at WC_HQ?**
A: Automated systems only. No human at WC_HQ reads your data. Alice at WC_HQ processes aggregated patterns. Individual installation data is never displayed, shared, or sold.

**Q: What if I disagree with a default WC_HQ sends?**
A: Reject it. Every Bundle can be reviewed before applying. Set `auto_apply: false` in your Connection config and Alice will show you each Bundle for approval.

**Q: Is the source code really open?**
A: Yes. MIT license. Fork it. Modify it. Run it without WC_HQ. The software is free. The library services are the business.

---

## Settings That Control WC_HQ

| Setting name | What it controls | Default |
|-------------|-----------------|---------|
| `wchq_sync_level` | Connection level (disconnected/read-only/standard/full/hq) | read-only |
| `wchq_publish_refs` | Send anonymized refs policies to WC_HQ | true |
| `wchq_publish_usage` | Send anonymized usage patterns | true |
| `wchq_publish_coaching` | Send coaching feedback | true |
| `wchq_receive_defaults` | Accept improved defaults from WC_HQ | true |
| `wchq_auto_apply` | Apply incoming Bundles automatically (vs manual review) | false |
| `wchq_sync_frequency` | How often to sync (hourly/daily/weekly/manual) | daily |

All settings are in the DataBrowser under the Setting model. Alice can change them on your behalf if you ask.

---

*Your store is yours. WC_HQ makes it better. You decide how much better, and you can change your mind anytime.*
