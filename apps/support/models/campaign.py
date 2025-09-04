# Explanation: Records of specific marketing efforts. Tallies how many new customers, orders, invoices, margins, and revenue was generated from each.
# metadata: dt_begin,dt_calculated,dt_end,ida_source,id_pos,


# let is along until all else is done
CREATE_TABLE_CAMPAIGNS_SQL = """
CREATE TABLE IF NOT EXISTS campaigns (
  id BIGSERIAL PRIMARY KEY,
  publication JSONB,
  issue VARCHAR(255),
  market_effort VARCHAR(255),
  metrics JSONB,
  effort INTEGER,
  count_customers_actual INTEGER,
  count_customers_plan INTEGER,
  count_invoice_plan INTEGER,
  count_invoices INTEGER,
  count_responces_new INTEGER,
  count_so_first INTEGER,
  count_sos INTEGER,
  count_sos_plan INTEGER,
  value_invoices INTEGER,
  value_invoices_plan INTEGER,
  value_so_first DOUBLE PRECISION,
  value_sos INTEGER,
  value_sos_plan INTEGER,
  responses_actual INTEGER,
  responses_plan INTEGER,
  cost_actual INTEGER,
  cost_plan INTEGER,
  cost_sales DOUBLE PRECISION,
  pace VARCHAR(255),
  path TEXT,
  size VARCHAR(255)
);
"""
