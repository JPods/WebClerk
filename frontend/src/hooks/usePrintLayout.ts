/**
 * usePrintLayout — fetch and cache the print_layout Setting for a model.
 * Returns the layout JSON that drives UniversalPrint rendering.
 *
 * Falls back to a sensible default layout if no print_layout Setting exists,
 * so Cmd+P works immediately for any transaction model.
 */
import { useState, useEffect } from 'react';
import { getRecords } from '@/api/wcapi';
import type { PrintLayout } from '@/components/print/printLayoutTypes';

// Cache layouts by model name to avoid re-fetching
const layoutCache = new Map<string, PrintLayout>();

/** Generate a sensible default print layout for a transaction model */
function defaultPrintLayout(model: string): PrintLayout {
  const isSell = ['order', 'invoice', 'proposal'].includes(model);
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
          { field: isSell ? 'price.extended' : 'cost.extended', label: 'Extended', align: 'right', format: 'currency' },
        ],
        show_footer_totals: true,
      },
      {
        type: 'totals',
        rows: [
          { field: 'totals.subtotal', label: 'Subtotal', format: 'currency' },
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

export function usePrintLayout(modelName: string) {
  const [layout, setLayout] = useState<PrintLayout | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!modelName) return;

    // Check cache first
    const cached = layoutCache.get(modelName);
    if (cached) { setLayout(cached); return; }

    setLoading(true);
    getRecords('setting', { parent_model: modelName, purpose: 'wc:print_layout' })
      .then((res: any) => {
        const rec = (res?.results || [])[0];
        const config = rec?.config as PrintLayout | undefined;
        const pl = config?.sections ? config : defaultPrintLayout(modelName);
        layoutCache.set(modelName, pl);
        setLayout(pl);
      })
      .catch(() => {
        const pl = defaultPrintLayout(modelName);
        layoutCache.set(modelName, pl);
        setLayout(pl);
      })
      .finally(() => setLoading(false));
  }, [modelName]);

  return { layout, loading };
}

/** Imperatively fetch a print layout (for non-hook contexts like ReportsDialog) */
export async function fetchPrintLayout(modelName: string): Promise<PrintLayout> {
  const cached = layoutCache.get(modelName);
  if (cached) return cached;

  try {
    const res = await getRecords('setting', { parent_model: modelName, purpose: 'wc:print_layout' }) as any;
    const rec = (res?.results || [])[0];
    const config = rec?.config as PrintLayout | undefined;
    const pl = config?.sections ? config : defaultPrintLayout(modelName);
    layoutCache.set(modelName, pl);
    return pl;
  } catch {
    const pl = defaultPrintLayout(modelName);
    layoutCache.set(modelName, pl);
    return pl;
  }
}
