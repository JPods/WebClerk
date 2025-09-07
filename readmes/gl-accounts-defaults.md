# Default GL Account Assignment

<!-- TOC START -->

## Table of Contents

- [Default GL Account Assignment](#default-gl-account-assignment)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Defaults Per Entity](#defaults-per-entity)
  - [Overriding Defaults](#overriding-defaults)
  - [Operational Notes](#operational-notes)

<!-- TOC END -->

## Overview

Newly created entities automatically receive sensible default GL accounts for typical flows. These defaults are intended for fast setup and can be overridden per record.

Scopes covered:

- Sales
- Inventory
- Cost
- Purchase

## Defaults Per Entity

The following entity types receive defaults at creation time:

- Customers
- Items
- Services
- Vendors
- Manufacturers
- Reps

Defaults are assigned via a small service hook in accounts and may consult org-level configuration. If unset, a safe fallback category is applied.

## Overriding Defaults

You can override GL accounts per record at any time. The system will prefer the most specific setting in this order:

1. Record-specific override (e.g., item-level)
2. Entity-type defaults (e.g., all services)
3. Global/org defaults

## Operational Notes

- Defaults are idempotent and only applied when a record lacks explicit assignments.
- Bulk imports can disable auto-defaulting and later run a reconcile to fill missing GL assignments.
- Future: Admin UI to view and edit default mappings.

Backfill command:

```bash
python manage.py backfill_gl_defaults --limit 0
```

Related:

- Tax jurisdictions: `gl_account_payable` gets defaulted when missing.
- Contacts receiving commissions: `prefs.gl_accounts.commission` is set when absent.
