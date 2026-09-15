# Contact Field Map — wc2 → wc3

## Communications (separate models, linked via refs.links)
| wc2 Field | wc3 Home | Notes |
|-----------|----------|-------|
| FAX | phone model (type='fax') | Just another phone record |
| Cell | phone model (type='cell') | Just another phone record |
| eMail | email model | Primary email on contact.email |
| eVerified | email model.is_verified | Per-email, not per-contact |
| OptOut | email model.opt_out | Per-email opt-out status |
| wPage/Pub | domain model (type='website') | URL/handle |

## Contact record fields (already on model or config)
| wc2 Field | wc3 Home | Notes |
|-----------|----------|-------|
| AdSource | config.ad_source | How they found us |
| SalesID | config.sales_id | Sales rep assignment |
| RepID/Terr | config.rep_id, config.territory | Rep + territory |
| TypeSale | prefs.price_level | Inherited by orders |
| Terms | prefs.terms | Inherited by orders |
| ShipVia | prefs.ship_via | Inherited by orders |
| TaxJuris | prefs.tax_jurisdiction | Tax authority |

## Contact metadata (system-managed, not user-edited)
| wc2 Field | wc3 Home | Notes |
|-----------|----------|-------|
| Verified Date | metadata.verified.dt | When contact was verified |
| Retire Date | metadata.retired.dt | When contact was retired |
| Retired | metadata.retired.is_retired | Boolean flag |
| Response | metadata.first_response | Date of first response |

## Contact prefs (user defaults — inherited by transactions)
| wc2 Field | wc3 Home | Notes |
|-----------|----------|-------|
| TypeSale | prefs.price_level | A/B/C/D → Retail/Wholesale/Distributor/Sample |
| Terms | prefs.terms | Payment terms default |
| ShipVia | prefs.ship_via | Shipping method default |
| Budget | prefs.budget | Annual budget (for qualification) |
| Need | prefs.need | What they need (call back, quote, etc.) |
| Size | prefs.size | Company size (employees or revenue) |

## Contact config (application data)
| wc2 Field | wc3 Home | Notes |
|-----------|----------|-------|
| Prospect | config.prospect_status | Purchased, Lead, Qualified, Lost |
| Rank | config.rank | Priority ranking |
| Sector | config.sector | Industry sector |
| Type Business | config.business_type | Business classification code |
| Location | config.location | Physical location identifier |
| Specialties | config.specialties | What they specialize in |
| Profile5 | config.profile5 | Custom profile field |
| SIC Code | config.sic_code | Standard Industry Classification |
| AdSource | config.ad_source | Marketing source |

## refs.keytags (user-defined, not auto-generated)
| wc2 Field | wc3 Home | Notes |
|-----------|----------|-------|
| Keywords | refs.keytags | User-typed context words: "sally's_wedding_met", "golf_buddy", "referred_by_tom" |

## The Distinction

```
refs.keywords  — auto-generated from field values (company, name, phone digits)
                 System rebuilds these. User doesn't touch them.

refs.keytags   — human-added context that the system can't derive
                 "met at trade show 2025", "daughter plays softball"
                 User adds these. System never overwrites them.
                 Searchable alongside keywords.
```

Both are searched by the keyword fragment search (comma=AND, pipe=OR).
Keywords are rebuilt on save. Keytags are preserved across saves.
