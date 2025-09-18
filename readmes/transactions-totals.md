# Transactions: Line Split and Totals Rollup

Scope

- Sell-side headers: Proposal, SalesOrder, Invoice
  - Lines: ProposalLine, SalesOrderLine, InvoiceLine → inherit BaseSellLineModel (has price JSON)
- Exec-side headers: PurchaseOrder, WorkOrder
  - Lines: PurchaseOrderLine, WorkOrderLine → inherit BaseExecLineModel (no price JSON)

Line JSON

- Shared (all lines)
  - cost: unit, extended, shipping, handling, freight, commissions, tax_rate, tax, is_fixed, precision, tax_code, tax_code_id
  - quantity: defaults vary by family (proposal/order/invoice) via default_quantity
- Sell-side only
  - price: unit, discount_percent, discount_amount, extended, is_fixed, precision

Header rollups

- Proposal: compute_proposal_sell_cost_totals + Proposal.update_sell_cost_totals()
- SalesOrder: compute_sales_order_sell_cost_totals + SalesOrder.update_sell_cost_totals()
- Invoice: compute_invoice_sell_cost_totals + Invoice.update_sell_cost_totals()

Shapes returned

- sell: line_sum_goods, discount, tax, shipping, handling, other, total
- cost: line_sum_goods, line_sum_tax, line_sum_shipping, line_sum_handling, freight, commissions, tax_rate, tax, total
- totals: total, cost, margin, margin_pc, received, balance

Refs links (singular model keys)

- invoice.refs.links.invoice_line
- sales_order.refs.links.sales_order_line
- proposal.refs.links.proposal_line

WCAPI saves

- SaveWcapiView deep-merges JSON clusters (refs, prefs, metadata, item, price, cost, etc.).
- Unknown fields are captured into prefs.userdefined.

Tests

- tests/test_line_model_inheritance.py: sell vs exec price field presence
- tests/test_sales_order_totals.py: order rollup
- tests/test_proposal_totals.py: proposal rollup

Next

- Add header fields (sell, cost, totals) and functional index on totals.total for Proposal/SalesOrder/Invoice.
