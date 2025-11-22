// Canonical mapping of domain terms used in UI → backend model_name
export const Model = {
  product: 'item',
  order: 'sales_order',
  orderLine: 'sales_order_line',
  invoice: 'invoice',
  invoiceLine: 'invoice_line',
  proposal: 'proposal',
  proposalLine: 'proposal_line',
  qa: 'qa', // alias for doc_qa on backend
} as const;

export type ModelKey = keyof typeof Model;
