# Forecasting — Demand, Supply, Cash Flow
**Status:** Design complete | **Source:** WC2 FC_* methods (11 files) + Bill 2026-07-04

---

## Principle

Forecast is a computed view across existing transaction lines — no new model. Looks at lines, not headers. Proposals carry probability. JSON viewer displays the results.

---

## Three Forecasts

### 1. Demand Forecast

```
Proposal lines × probability     = weighted pipeline demand
  + Order lines (confirmed)       = committed demand
  = Total expected demand by item by period
```

Key: a $100K proposal at 60% probability = $60K expected demand. This is the pipeline view that drives purchasing decisions.

### 2. Supply Forecast

```
Purchase lines (open POs)         = inbound supply
  + Work order lines (in progress) = production supply
  - BOM component consumption      = supply used by production
  = Net supply by item by period
```

### 3. Cash Flow (swag)

```
For each receivable:
  due_date + net_days_delay        = expected cash-in date
  amount × probability (if proposal) = expected amount

For each payable:
  due_date                         = expected cash-out date
  amount                          = certain (PO committed)

For inventory:
  on_hand × cost × carrying_days / 365 = carrying cost
  
Net cash flow = cash-in - cash-out - carrying cost by period
```

---

## Data Sources (all existing)

| Source | Model | Fields Used |
|---|---|---|
| Proposal demand | ProposalLine | item, qty, price, probability (new field or in metadata) |
| Order demand | OrderLine | item, qty, price, ship_date |
| PO supply | PurchaseLine | item, qty, cost, expected_date |
| WO supply | WorkOrderLine | item, qty, completion_date |
| Inventory | InventoryLayer | item, qty_remaining, cost |
| Receivables | Ledger | dt_due, value_available |
| Payables | Ledger (vendor) | dt_due, value_available |

No new tables. Forecast service queries these and computes.

---

## Display

The JSON viewer is the natural display tool:

```json
{
  "item_ida": "BB005",
  "item_name": "Baseball - Wilson",
  "periods": [
    {
      "period": "2026-07",
      "demand": {"proposals": 150, "orders": 80, "total": 230},
      "supply": {"po_inbound": 200, "wo_production": 0, "total": 200},
      "net": -30,
      "on_hand_start": 100,
      "on_hand_end": 70,
      "cash_in": 5750.00,
      "cash_out": 960.00,
      "carrying_cost": 12.50
    }
  ]
}
```

Could also be a 6th tab on the Commerce Dashboard or a standalone report.

---

## Probability on Proposals

Proposals need a probability field for weighted demand:

```
proposal_line.probability = 0.60    → 60% likely to convert
demand = qty × probability          → 100 units × 0.60 = 60 expected
```

This can live in the line's metadata or as a field on Proposal header (inherited by lines). Setting record provides default probabilities by stage (e.g., new=20%, quoted=50%, negotiating=75%, verbal_commit=90%).

---

## What WC2 Had (11 methods)

| Method | What It Did |
|---|---|
| FC_ByOrder | Order-based demand projection |
| FC_CalcUsage | Historical usage → future projection |
| FC_CashFlow | Cash timing from due dates + payment delay |
| FC_OH | On-hand projection (start + supply - demand) |
| FC_SumYear | Annual rollup |
| FC_FillArrays/FillRay | Display arrays (4D-specific, skip) |
| FC_SaveLocal/RetrvLocal | Cache forecast locally (4D-specific) |
| FC_LaunchWin | UI launcher (4D-specific) |

Core logic (ByOrder, CalcUsage, CashFlow, OH, SumYear) maps to 5 Python functions. The rest is 4D UI machinery.

---

## What Needs Building

1. `forecast_demand(item_ids, periods)` — proposals × probability + orders
2. `forecast_supply(item_ids, periods)` — POs + WOs - BOM consumption
3. `forecast_cashflow(periods)` — receivables + payables + carrying cost
4. `forecast_item(item_id)` — complete picture for one item
5. Probability field or convention on Proposal/ProposalLine
6. Dashboard tab or report view

---

## Files

| File | Status | Purpose |
|------|--------|---------|
| Forecast service | Needs building | forecast_demand, forecast_supply, forecast_cashflow |
| ProposalLine | May need probability field | Weighted demand |
| Commerce Dashboard | Could add 6th tab | Or standalone report |
