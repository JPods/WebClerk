/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * TransactionItemSearch - Shared item search component for all transaction types
 * Configurable to show price (for sales) or cost (for purchases) as the primary value
 */
import { FormEvent, useCallback, useMemo, useState } from "react";
import { useDispatch } from "react-redux";

import { showToast } from "../../../store/slices/toastSlice";
import { searchItems as searchItemsApi } from "@/api/wcapi";

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
  cost?: number | string;
  costA?: number | string;
  qty_on_hand?: number | string;
  qtyOnHand?: number | string;
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

/**
 * Resolve unit price based on price level
 * If item.price is an object with price levels (base, wholesale, distributor, sample),
 * looks up item.price[priceLevel], falling back to item.price.base if level not found.
 * priceLevel defaults to "retail" if null/undefined.
 * Note: "retail" and "base" are treated as equivalent.
 */
export function resolveUnitPrice(
  item: ItemSearchResult,
  priceLevel?: string | null,
): number {
  // Default price level to "retail" if not provided ("retail" and "base" are equivalent)
  const level = priceLevel || "retail";

  // Check if item.price is an object with price levels
  if (item.price && typeof item.price === "object") {
    const priceObj = item.price as Record<string, unknown>;
    // Try the requested price level first
    // For "retail" also check "base", and vice versa (they are equivalent)
    let levelValue = priceObj[level];
    if (levelValue === undefined || levelValue === null) {
      if (level === "retail") {
        levelValue = priceObj.base;
      } else if (level === "base") {
        levelValue = priceObj.retail;
      } else {
        // Fall back to base/retail for other levels not found
        levelValue = priceObj.base ?? priceObj.retail;
      }
    }
    if (typeof levelValue === "number" && levelValue >= 0) return levelValue;
    if (typeof levelValue === "string") {
      const parsed = Number.parseFloat(levelValue);
      if (!Number.isNaN(parsed) && parsed >= 0) return parsed;
    }
  }

  // Legacy fallback for non-object price fields
  const candidates = [item.unit_price, item.price, item.priceA, item.price_a];
  for (const candidate of candidates) {
    if (typeof candidate === "number" && candidate >= 0) return candidate;
    if (typeof candidate === "string") {
      const parsed = Number.parseFloat(candidate);
      if (!Number.isNaN(parsed) && parsed >= 0) return parsed;
    }
  }
  return 0;
}

export function resolveUnitCost(item: ItemSearchResult): number {
  const candidates = [item.unit_cost, item.cost, item.costA];
  for (const candidate of candidates) {
    if (typeof candidate === "number" && candidate >= 0) return candidate;
    if (typeof candidate === "string") {
      const parsed = Number.parseFloat(candidate);
      if (!Number.isNaN(parsed) && parsed >= 0) return parsed;
    }
  }
  return 0;
}

export function resolveQtyOnHand(item: ItemSearchResult): number {
  const candidates = [item.qty_on_hand, item.qtyOnHand];
  for (const candidate of candidates) {
    if (typeof candidate === "number" && candidate >= 0) return candidate;
    if (typeof candidate === "string") {
      const parsed = Number.parseFloat(candidate);
      if (!Number.isNaN(parsed) && parsed >= 0) return parsed;
    }
  }
  return 0;
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
  defaultQuantity = 1,
  searchFn,
}: TransactionItemSearchProps) {
  const dispatch = useDispatch();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<ItemSearchResult[]>([]);
  const [quantities, setQuantities] = useState<Record<string, number>>({});

  const hasResults = useMemo(() => results.length > 0, [results]);

  // Determine column header
  const priceHeader = valueLabel ?? (useCost ? "Unit Cost" : "Unit Price");

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
    [dispatch, query, searchFn, defaultQuantity],
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

  // Get unit value based on useCost flag
  const getUnitValue = (item: ItemSearchResult): number => {
    return useCost ? resolveUnitCost(item) : resolveUnitPrice(item);
  };

  return (
    <div className="space-y-4">
      <form
        onSubmit={handleSearch}
        className="flex flex-col gap-3 md:flex-row md:items-end"
      >
        <label className="flex-1 text-sm font-medium text-gray-700 dark:text-gray-200">
          Item search
          <input
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by key tags, item #, or description"
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-hidden focus:ring-2 focus:ring-blue-200 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
          />
        </label>
        <button
          type="submit"
          className="h-10 rounded-md bg-blue-500 px-4 text-sm font-medium text-white hover:bg-blue-600 focus:outline-hidden focus:ring-2 focus:ring-blue-400"
          disabled={loading}
        >
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-500/60 dark:bg-red-900/20 dark:text-red-200">
          {error}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-gray-50 text-gray-700 dark:bg-gray-800 dark:text-gray-200">
            <tr>
              <th className="px-3 py-2">Item</th>
              <th className="px-3 py-2">Description</th>
              <th className="px-3 py-2 text-right">On Hand</th>
              <th className="px-3 py-2 text-right">{priceHeader}</th>
              <th className="px-3 py-2 text-right">Quantity</th>
              <th className="px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {!hasResults && !loading ? (
              <tr>
                <td
                  colSpan={6}
                  className="px-3 py-4 text-center text-sm text-gray-500 dark:text-gray-400"
                >
                  {query.trim()
                    ? "No matching items"
                    : "Enter a search term to find catalog items."}
                </td>
              </tr>
            ) : (
              results.map((item, index) => {
                const itemKey = resolveItemKey(item);
                const rowKey =
                  itemKey || `${resolveItemCode(item) || "result"}-${index}`;
                const quantity = quantities[itemKey] ?? defaultQuantity;
                return (
                  <tr
                    key={rowKey}
                    className="border-b border-gray-100 last:border-none dark:border-gray-700"
                  >
                    <td className="px-3 py-2 text-gray-800 dark:text-gray-100">
                      {resolveItemCode(item) || "--"}
                    </td>
                    <td className="px-3 py-2 text-gray-600 dark:text-gray-300">
                      {resolveItemDescription(item) || "--"}
                    </td>
                    <td className="px-3 py-2 text-right text-gray-600 dark:text-gray-300">
                      {resolveQtyOnHand(item).toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-right text-gray-600 dark:text-gray-300">
                      $
                      {getUnitValue(item).toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </td>
                    <td className="px-3 py-2 text-right text-gray-600 dark:text-gray-300">
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={quantity || ""}
                        onChange={(event) =>
                          handleQuantityChange(itemKey, event.target.value)
                        }
                        className="h-9 w-24 rounded border border-gray-300 px-2 text-right text-sm focus:border-blue-400 focus:outline-hidden focus:ring-2 focus:ring-blue-200 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                      />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button
                        type="button"
                        onClick={() => handleAddItem(item)}
                        disabled={!itemKey}
                        className={`rounded-md px-3 py-1 text-sm font-medium text-white focus:outline-hidden focus:ring-2 focus:ring-green-400 ${
                          itemKey
                            ? "bg-green-500 hover:bg-green-600"
                            : "cursor-not-allowed bg-gray-400 dark:bg-gray-700"
                        }`}
                      >
                        Add
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default TransactionItemSearch;
