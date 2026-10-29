/**
 * usePrintLayout — the layout JSON that drives UniversalPrint rendering: a sensible default
 * per model, so Cmd+P works for any transaction model.
 */
import { useMemo } from 'react';
import type { PrintLayout } from '@/components/print/printLayoutTypes';

// Cache layouts by model name to avoid re-fetching

/** Generate a sensible default print layout for a transaction model */
function defaultPrintLayout(model: string): PrintLayout {
  const isSell = ['order', 'invoice', 'quote'].includes(model);
  const title = model.charAt(0).toUpperCase() + model.slice(1).replace(/_/g, ' ');

  return {
    model,
    family: isSell ? 'sell' : 'exec',
    paper: 'letter',
    title,
    version: 0,
    sections: [
      { type: 'company_header', logo: true, show_address: true, show_contact: true },
      {
        type: 'address_blocks',
        columns: [
          {
            title: 'Bill To',
            fields: [
              { field: 'attention', label: 'Attn' },
              { field: 'company', label: 'Company' },
              { field: 'address_full', label: 'Address' },
            ],
          },
          {
            title: 'Ship To',
            fields: [
              { field: 'config.ship_to.company', label: 'Company' },
              { field: 'config.ship_to.attention', label: 'Attn' },
              { field: 'config.ship_to.address1', label: 'Address' },
            ],
          },
          {
            title: title + ' Info',
            fields: [
              { field: 'ida', label: `${title} #` },
              { field: 'status', label: 'Status' },
              { field: 'dt_created', label: 'Date', format: 'date' },
              { field: 'terms', label: 'Terms' },
              { field: 'price_level', label: 'Price Level' },
            ],
          },
        ],
      },
      { type: 'comments', source: 'comments.public', label: 'Comments' },
      {
        type: 'line_items',
        columns: [
          { field: 'item.ida_item', label: 'Item', align: 'left' },
          { field: 'item.description', label: 'Description', align: 'left', width: '40%' },
          { field: 'quantity.active', label: 'Qty', align: 'right' },
          { field: isSell ? 'price.unit' : 'cost.unit', label: isSell ? 'Unit Price' : 'Unit Cost', align: 'right', format: 'currency' },
          { field: 'totals.amount', label: 'amount', align: 'right', format: 'currency' },
        ],
        show_footer_totals: true,
      },
      {
        type: 'totals',
        rows: [
          { field: 'totals.amount', label: 'Subtotal', format: 'currency' },
          { field: 'totals.tax', label: 'Tax', format: 'currency' },
          { field: 'totals.shipping', label: 'Shipping', format: 'currency' },
          { field: 'totals.total', label: 'Total', format: 'currency', style: 'bold' },
        ],
        left_text: 'Thank you for your business.',
      },
      { type: 'conditions', source: 'conditions_description' },
      {
        type: 'footer',
        fields: [
          { field: 'ida', label: `${title} #` },
          { field: 'customer_id', label: 'Customer #' },
        ],
      },
    ],
  };
}

/** The print layout for a model: its default. No wc:print_layout record ever existed, so
 *  the Setting read is gone (Setting audit S-7, 2026-10-28). */
export function usePrintLayout(modelName: string) {
  const layout = useMemo(() => (modelName ? defaultPrintLayout(modelName) : null), [modelName]);
  return { layout, loading: false };
}

/** Imperatively fetch a print layout (for non-hook contexts like ReportsDialog) */
export async function fetchPrintLayout(modelName: string): Promise<PrintLayout> {
  return defaultPrintLayout(modelName);
}
