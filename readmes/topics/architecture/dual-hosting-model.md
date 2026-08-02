# Dual Hosting Model

> **Reading order**: [← 01-architecture-overview](../../01-architecture-overview.md) | [data-library-ecosystem →](data-library-ecosystem.md)

---

## Overview

WebClerk supports two hosting modes simultaneously:

- **Desktop Hosting** — a local server running inside the business, on the business's own hardware
- **Cloud Hosting** — a cloud mirror providing persistence and customer access when the local server is unreachable

These are not alternatives. They are complements. Both run at the same time. Each serves a different constituency and a different failure mode.

---

## Why Both

**Desktop Hosting** serves the people inside the business. If the internet goes down, if the cloud is unavailable, if there is a power disruption at the data center — staff can still access inventory, process transactions, and serve customers standing in front of them. The business does not stop because a remote server is unreachable.

**Cloud Hosting** serves customers and remote access. If the local server goes down — power outage, hardware failure, maintenance — customers can still reach their order history, account data, and the retailer's published inventory. The business remains visible to the world even when its local infrastructure is temporarily unavailable.

Together they mean: **no single point of failure can take the business fully offline.**

---

## The Four Scenarios

| Scenario | Local | Cloud | Staff access | Customer access |
|----------|-------|-------|-------------|----------------|
| Normal operation | Up | Up | Local server | Cloud mirror |
| Local outage (power, hardware) | Down | Up | None — staff wait for restoration | Cloud mirror continues |
| Cloud unavailable | Up | Down | Local server — unaffected | Unavailable until cloud restores |
| Split — both up, disconnected | Up, writing independently | Up, writing independently | Local server | Cloud mirror |

The first three scenarios are straightforward. The fourth — the split — is where conflict resolution is required.

---

## Conflict Resolution — Alice's Domain

During a split, both the local server and the cloud mirror accept writes independently. When connectivity restores, WebClerk may have two versions of the same record that diverged. Reconciling them is a key function of **Alice**, the database agent.

### The tools Alice works with

**`uuid`** — the identity anchor. Every record carries a stable uuid generated at creation that travels with the record across systems. When local and cloud both have a record with the same uuid, Alice knows they are the same logical record regardless of whether their internal `id` values match. uuid is how Alice finds the conflict; `id` is local bookkeeping.

**`dt` event tracking** — the causal timeline. Timestamps on every state change give Alice the sequence of events on each side during the split. She can reconstruct what happened on local, what happened on cloud, and in what order — which is the foundation for any resolution decision.

**Pending records** — the uncertainty layer. Writes during uncertain conditions (split, offline, unverified sync) are staged as pending rather than immediately committed as authoritative. Pending records are Alice's work queue: they exist, they are visible, but they are not yet resolved. Nothing is silently discarded; nothing is silently promoted.

**Optimistic concurrency (version numbers)** — Alice detects that a record diverged by comparing versions. A record at version 7 on local and version 9 on cloud signals two writes on cloud during the split. The version gap tells Alice how much divergence to expect.

### Resolution in practice

With uuid establishing identity, dt establishing timeline, and pending records flagging uncertainty, most conflicts resolve to a small set of standard patterns. Alice handles these automatically:

- **One side changed, the other did not** — apply the change. No ambiguity.
- **Both sides changed different fields** — merge. No ambiguity.
- **Both sides changed the same field** — compare dt timestamps. Later write takes precedence for scalar fields; key-level merge for JSON fields.
- **Genuine ambiguity** — flag for human review. Both versions preserved. Staff resolve via reconciliation queue.

### Experience compounds

The patterns Alice encounters repeat. A customer updating their shipping address while a staff member updates the same contact's phone number is a merge, not a conflict — Alice learns this quickly. Over time the set of cases requiring human review shrinks. Resolution becomes increasingly standard and automatic.

This is the same principle as the data library feedback loop: each cycle of experience raises the baseline. Excellence is the process of relentlessly improving.

---

## Sovereignty Implications

**Desktop hosting is local sovereignty.** The business's data lives on hardware the business controls. A cloud outage, a vendor bankruptcy, a terms-of-service change — none of these can take the business's operational data away from it. The local server is the authoritative source during normal operation.

**Cloud hosting is availability without dependency.** The cloud mirror exists to serve customers and provide geographic redundancy — not to hold the business's data hostage. The business can switch cloud providers, move to a different host, or take the cloud fully offline without losing its operational data.

This mirrors the broader WebClerk design principle: **no single entity controls a dependency that can be used as leverage.**

---

## Connection to the Data Library Ecosystem

Data libraries push normalized inventory and cost data into WebClerk via wcapi. During a split, the local server may receive a library push while the cloud mirror does not — or vice versa. The same conflict resolution rules apply: version comparison, timestamp ordering, merge at the field level.

Libraries should be configured to push to the local server as the primary target during normal operation. The cloud mirror syncs from local. This ensures the local server remains the authoritative inventory source and the cloud reflects it — rather than both receiving independent library pushes that diverge.

---

## Connection to Allie

Allie's offline behavior follows the same pattern at the personal scale: writes queue as pending items in the carryon when WebClerk is unreachable, and sync when connectivity restores. The dual-hosting model means Allie is more likely to reach *some* version of WebClerk even during partial outages — she can fall back to the cloud mirror if the local server is down.

See [allie-webclerk-integration.md](allie-webclerk-integration.md) for Allie's offline queue behavior.

---

## WC_HQ — The Hub Instance

When many Andi boxes are deployed, one WC3 instance operates as WC_HQ — the hub. WC_HQ is not a separate application. It is a WC3 instance configured with Connections to every deployed Andi.

WC_HQ uses the same Connection/Bundle models for both commerce operations (catalog data, complication reports) and infrastructure operations (software deploys, knowledge sync, vector store rebuilds). One system, one audit trail, one DataBrowser interface.

The three-data-type rule governs what flows:
- **Common** data (catalogs, code, training) pushes from HQ to all instances
- **Transactional** data (distribution agreements, complications) flows between HQ and specific instances
- **Proprietary** data (customers, transactions, margins) never leaves the instance

Each Connection carries a scoped wcapi token that enforces these boundaries. The token allows writes to catalog models and reads of health metrics. It blocks access to contacts, invoices, orders, and all proprietary data. Alice on each instance validates incoming Bundles against these rules.

See `readmes/21-sync-integration.md` for the full WC_HQ sync pattern, including deploy and knowledge Bundle examples.
