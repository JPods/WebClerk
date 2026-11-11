/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * TransactionItemSearch - Shared item search component for all transaction types
 * Configurable to show price (for sales) or cost (for purchases) as the primary value
 */
import { FormEvent, useCallback, useState } from "react";
import { useDispatch } from "react-redux";

import { showToast } from "../../../store/slices/toastSlice";
import { searchItems as searchItemsApi } from "@/api/wcapi";
import { useItemCard } from "@/components/common/ItemCard";
import { DbColumns, type DbColumnDef } from "@/apps/common/components/panels/DbColumns";
import { formatCell } from "@/apps/common/components/panels/cellFormat";
import { priceLines, type LineFigures, type LinePricingContext } from "../services/linePricing";

// Generic item search result - supports various field naming conventions
export interface ItemSearchResult {
  id?: number;
  item_id?: number;
  itemId?: number;
  item_num?: string;
  itemNum?: string;
  ida_item?: string;
  sku?: string;
  description?: string;
  description_text?: string;
  name?: string;
  price?: number | string;
  priceA?: number | string;
  price_a?: number | string;
  unit_price?: number | string;
  unit_cost?: number | string;
  cost?: number | string | Record<string, unknown>;
  costA?: number | string;
  quantity?: { on_hand?: number | string; available?: number | string; [k: string]: unknown };
  unit_of_measure?: string;
  unitOfMeasure?: string;
  unit_measure?: string;
  [key: string]: unknown;
}

// Helper functions for resolving item fields
export function resolveItemCode(item: ItemSearchResult): string {
  return (
    item.ida_item ||
    item.item_num ||
    item.itemNum ||
    item.sku ||
    item.item_id?.toString() ||
    item.id?.toString() ||
    ""
  );
}

export function resolveItemDescription(item: ItemSearchResult): string {
  return (
    item.description ||
    item.description_text ||
    item.name ||
    resolveItemCode(item) ||
    "Item"
  );
}

export function resolveItemKey(item: ItemSearchResult): string {
  const code = resolveItemCode(item);
  if (code) return code;
  const id = item.id || item.item_id || item.itemId;
  return id ? `item-${id}` : "";
}

/** The item's own counts (Item.quantity: on_hand, available, on_so, ...). The flat
 *  qty_on_hand this read until 2026-10-25 no longer exists, so every item showed 0. */
export function resolveQtyOnHand(item: ItemSearchResult): number {
  return Number(item.quantity?.on_hand) || 0;
}

/** What can still be promised: the item's available count, the server's arithmetic. */
export function resolveQtyAvailable(item: ItemSearchResult): number {
  return Number(item.quantity?.available) || 0;
}

interface TransactionItemSearchProps {
  /** Callback when an item is added */
  onAddItem: (item: ItemSearchResult, quantity: number) => void;
  /** Whether to show cost instead of price (for purchase orders, work orders) */
  useCost?: boolean;
  /** Label for the value column (defaults to "Unit Price" or "Unit Cost" based on useCost) */
  valueLabel?: string;
  /** Default quantity for new items (defaults to 1) */
  defaultQuantity?: number;
  /** The document's customer and price level — the server prices the results for them */
  pricing?: LinePricingContext;
  /** Custom search function if not using default */
  searchFn?: (
    query: string,
    options?: { limit?: number },
  ) => Promise<{ data: { results: ItemSearchResult[] } }>;
}

const quantityInputMin = 0.0001;

export function TransactionItemSearch({
  onAddItem,
  useCost = false,
  valueLabel,
  pricing,
  defaultQuantity = 1,
  searchFn,
}: TransactionItemSearchProps) {
  const dispatch = useDispatch();
  const [itemCardEl, showItemCard] = useItemCard();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<ItemSearchResult[]>([]);
  const [quantities, setQuantities] = useState<Record<string, number>>({});

  // Determine column header
  const priceHeader = valueLabel ?? (useCost ? "Unit Cost" : "Unit Price");
  // Both figures per result, from the server (resolve_price / resolve_cost).
  const [figures, setFigures] = useState<Record<number, LineFigures>>({});

  const handleSearch = useCallback(
    async (event?: FormEvent) => {
      event?.preventDefault();
      const trimmed = query.trim();
      if (!trimmed) {
        setResults([]);
        setError(null);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        let res;
        if (searchFn) {
          res = await searchFn(trimmed, { limit: 25 });
        } else {
          // Use default wcapi search
          const apiRes = await searchItemsApi(trimmed, { limit: 25 });
          res = { data: { results: apiRes.results ?? [] } };
        }
        const nextResults = res.data.results ?? [];
        setResults(nextResults);
        const ids = nextResults
          .map((r) => Number(r.id || r.item_id || r.itemId || 0))
          .filter((id) => id > 0);
        setFigures({});
        if (ids.length) {
          const priced = await priceLines(
            ids.map((item_id) => ({ item_id, qty: defaultQuantity })), pricing);
          setFigures(Object.fromEntries(priced.lines.map((l) => [l.item_id, l])));
        }
        setQuantities((prev) => {
          const next: Record<string, number> = {};
          nextResults.forEach((result) => {
            const key = resolveItemKey(result);
            if (key) {
              // Use previous value if exists, otherwise use default quantity
              next[key] = prev[key] ?? defaultQuantity;
            }
          });
          return next;
        });
      } catch (err: any) {
        const message = err?.message || "Item search failed";
        setError(message);
        dispatch(showToast({ message, type: "error" }));
      } finally {
        setLoading(false);
      }
    },
    [dispatch, query, searchFn, defaultQuantity, pricing],
  );

  const handleQuantityChange = useCallback((key: string, value: string) => {
    const numeric = Number.parseFloat(value);
    setQuantities((prev) => ({
      ...prev,
      [key]: Number.isFinite(numeric) && numeric > 0 ? numeric : 0,
    }));
  }, []);

  const handleAddItem = useCallback(
    (item: ItemSearchResult) => {
      const key = resolveItemKey(item);
      if (!key) {
        dispatch(
          showToast({
            message: "Cannot add item without a stable identifier",
            type: "error",
          }),
        );
        return;
      }
      const quantity = quantities[key] ?? 0;
      if (!quantity || quantity < quantityInputMin) {
        dispatch(
          showToast({
            message: "Enter a quantity greater than zero",
            type: "info",
          }),
        );
        return;
      }
      onAddItem(item, quantity);
      dispatch(
        showToast({
          message: `Added ${quantity.toLocaleString()} × ${
            resolveItemCode(item) || "item"
          }`,
          type: "success",
        }),
      );
      // Reset quantity to default after adding
      setQuantities((prev) => ({ ...prev, [key]: defaultQuantity }));
    },
    [dispatch, onAddItem, quantities, defaultQuantity],
  );

  // Each side shows the other's figure — the control (Bill, 2026-10-22).
  const otherFigure = (item: ItemSearchResult): string => {
    const f = figures[Number(item.id || item.item_id || item.itemId || 0)];
    if (!f) return "";
    const margin = (m: number | null) => (m === null ? "no margin (no cost)" : `${m.toFixed(1)}% margin`);
    return useCost
      ? `List $${f.cost.list_price.toFixed(2)} · ${margin(f.cost.margin_pct)} at list`
      : `${f.price.resolved_by.replace("_", " ")}${f.price.price_level ? ` (${f.price.price_level})` : ""}` +
        ` · cost $${f.price.unit_cost.toFixed(2)} (${f.price.cost_basis}) · ${margin(f.price.margin_pct)}` +
        (f.price.below_margin_floor ? ` — below the ${f.price.margin_floor}% floor` : "");
  };

  // The server's figure for this result: price on the sell side, cost on the buy side.
  // The line itself is repriced at its quantity when added.
  const getUnitValue = (item: ItemSearchResult): number | null => {
    const f = figures[Number(item.id || item.item_id || item.itemId || 0)];
    if (!f) return null;
    return useCost ? f.cost.unit : f.price.price;
  };

  const resultColumns: DbColumnDef<ItemSearchResult & { _key: string }>[] = [
    { key: 'add', label: '', width: 64, render: (item) => {
        const itemKey = resolveItemKey(item);
        return (
          <button type="button" onClick={(e) => { e.stopPropagation(); handleAddItem(item); }} disabled={!itemKey}
            className={`rounded-md px-3 py-1 font-medium text-white ${itemKey ? "bg-green-500 hover:bg-green-600" : "cursor-not-allowed bg-gray-400"}`}
            style={{ fontSize: 'inherit' }}>Add</button>
        );
      } },
    // Quantity sits beside Add: type the number, click Add, with almost no mouse travel (Bill, 2026-11-11).
    { key: 'quantity', label: 'Qty', align: 'right', width: 80, render: (item) => {
        const itemKey = resolveItemKey(item);
        return (
          <input type="text" inputMode="decimal" value={(quantities[itemKey] ?? defaultQuantity) || ""}
            onClick={(e) => e.stopPropagation()}
            onChange={(event) => handleQuantityChange(itemKey, event.target.value)}
            className="db-input" style={{ width: 64, textAlign: 'right', fontSize: 'inherit' }} />
        );
      } },
    { key: 'image', label: '', width: 44, render: (item) => resolveItemCode(item) ? (
        <img src={`/wcapi/_image/item/${encodeURIComponent(resolveItemCode(item))}/tn.jpg`} alt=""
          className="w-8 h-8 rounded object-cover" loading="lazy"
          onError={(e) => { const img = e.target as HTMLImageElement; img.onerror = null; img.src = '/images/no-image.svg'; }} />
      ) : null },
    { key: 'item', label: 'Item', width: 120, render: (item) => (
        <span className="cursor-pointer hover:underline" style={{ color: 'var(--db-accent, #0d6efd)' }}
          onClick={(e) => { e.stopPropagation(); const code = resolveItemCode(item); if (code) showItemCard(code, (e.currentTarget as HTMLElement).getBoundingClientRect()); }}>
          {resolveItemCode(item) || "--"}</span>
      ) },
    { key: 'description', label: 'Description', render: (item) => resolveItemDescription(item) || "--" },
    { key: 'on_hand', label: 'On Hand', align: 'right', width: 80, render: (item) => resolveQtyOnHand(item).toLocaleString() },
    { key: 'price', label: priceHeader, align: 'right', width: 100, render: (item) => (
        <span title={otherFigure(item)}>{getUnitValue(item) === null ? "…"
          : formatCell(getUnitValue(item), 'price', { type: 'currency' })}</span>
      ) },
  ];

  return (
    <div className="space-y-4">
      <form
        onSubmit={handleSearch}
        className="flex flex-col gap-3 md:flex-row md:items-end"
      >
        <button
          type="submit"
          className="rounded-md bg-green-600 px-3 py-1.5 font-medium text-white hover:bg-green-700 focus:outline-hidden focus:ring-2 focus:ring-green-400 shrink-0"
          style={{ fontSize: 'inherit' }}
          disabled={loading}
        >
          {loading ? "Searching…" : "Search"}
        </button>
        <label className="flex-1 font-medium text-gray-700 dark:text-gray-200" style={{ fontSize: 'inherit' }}>
          Item search
          <input
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(e) => { if (e.key === 'Tab' && query.trim()) { e.preventDefault(); handleSearch(); } }}
            placeholder="Search by key tags, item #, or description"
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-hidden focus:ring-2 focus:ring-blue-200 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
            style={{ fontSize: 'inherit' }}
            autoFocus
          />
        </label>
      </form>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-500/60 dark:bg-red-900/20 dark:text-red-200">
          {error}
        </div>
      )}

      {/* The results: the shared list (DbColumns), Add and quantity in their cells. */}
      <DbColumns<ItemSearchResult & { _key: string }>
        storageKey="txn:item-search"
        columns={resultColumns}
        data={results.map((item, index) => ({ ...item, _key: resolveItemKey(item) || `${resolveItemCode(item) || "result"}-${index}` }))}
        rowKey={(r) => r._key}
        compact
        emptyMessage={loading ? "Searching…" : query.trim() ? "No matching items" : "Enter a search term to find catalog items."}
      />
      {itemCardEl}
    </div>
  );
}

export default TransactionItemSearch;
