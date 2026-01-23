import { FormEvent, useCallback, useMemo, useState } from "react";
import { useDispatch } from "react-redux";

import { showToast } from "../../../../../store/slices/toastSlice";
import { searchItems } from "../services/salesOrderApi";
import type { ItemSearchResult } from "../types/itemSearchType";
import {
  resolveDefaultQuantity,
  resolveItemCode,
  resolveItemDescription,
  resolveItemKey,
  resolveQtyOnHand,
  resolveUnitCost,
  resolveUnitPrice,
} from "../utils/itemSearchHelpers";

interface SalesOrderItemSearchProps {
  onAddItem: (item: ItemSearchResult, quantity: number) => void;
}

const quantityInputMin = 0.0001;

export function SalesOrderItemSearch({ onAddItem }: SalesOrderItemSearchProps) {
  const dispatch = useDispatch();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<ItemSearchResult[]>([]);
  const [quantities, setQuantities] = useState<Record<string, number>>({});

  const hasResults = useMemo(() => results.length > 0, [results]);

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
        const res = await searchItems(trimmed, { limit: 25 });
        const nextResults = res.data.results ?? [];
        setResults(nextResults);
        setQuantities((prev) => {
          const next: Record<string, number> = {};
          nextResults.forEach((result) => {
            const key = resolveItemKey(result);
            if (key) {
              // Use previous value if exists, otherwise resolve default quantity (defaults to 1)
              next[key] = prev[key] ?? resolveDefaultQuantity(result);
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
    [dispatch, query],
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
            type: "warning",
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
      setQuantities((prev) => ({ ...prev, [key]: 0 }));
    },
    [dispatch, onAddItem, quantities],
  );

  return (
    <div className="space-y-4">
      <form
        onSubmit={handleSearch}
        className="flex flex-col gap-3 md:flex-row md:items-end"
      >
        <label className="flex-1 text-sm font-medium text-gray-700 dark:text-gray-200">
          <input
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by key tags, item #, or description"
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-hidden focus:ring-2 focus:ring-blue-200 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === "Tab") {
                event.preventDefault();
                handleSearch();
              }
            }}
          />
        </label>
        {/* <button
          type="submit"
          className="h-10 rounded-md bg-blue-500 px-4 text-sm font-medium text-white hover:bg-blue-600 focus:outline-hidden focus:ring-2 focus:ring-blue-400"
          disabled={loading}
        >
          {loading ? "Searching…" : "Search"}
        </button> */}
      </form>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-500/60 dark:bg-red-900/20 dark:text-red-200">
          {error}
        </div>
      )}

      <div className="overflow-x-auto cus-bg-purple-light overflow-y-scroll max-h-[180px]">
        {loading ? (
          <h3 className="text-center font-semibold">Searching…</h3>
        ) : (
          <table className="min-w-full text-left text-sm ">
            <thead className="bg-success-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200 sticky top-0 z-10">
              <tr>
                <th className="px-3 py-2">Item</th>
                <th className="px-3 py-2">Description</th>
                <th className="px-3 py-2 text-right">On Hand</th>
                <th className="px-3 py-2 text-right">Unit Price</th>
                <th className="px-3 py-2 text-right">Unit Cost</th>
                <th className="px-3 py-2 text-right">Quantity</th>
                <th className="px-3 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {!hasResults && !loading ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-3 py-4 text-center text-xs text-gray-500 dark:text-gray-400"
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
                  const quantity = quantities[itemKey] ?? 0;
                  // Stripe: even rows get bg-gray-50 (light) or bg-gray-800 (dark)
                  const stripeClass =
                    index % 2 === 1 ? "bg-gray-50 dark:bg-gray-800" : "";
                  return (
                    <tr
                      key={rowKey}
                      className={`border-b border-gray-100 last:border-none dark:border-gray-700 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors ${stripeClass}`}
                    >
                      <td className="px-3 py-1 text-xs text-gray-800 dark:text-gray-100">
                        {resolveItemCode(item) || "--"}
                      </td>
                      <td className="px-3 py-1 text-xs text-gray-600 dark:text-gray-300">
                        {resolveItemDescription(item) || "--"}
                      </td>
                      <td className="px-3 py-1 text-xs text-right text-gray-600 dark:text-gray-300">
                        {resolveQtyOnHand(item).toLocaleString()}
                      </td>
                      <td className="px-3 py-1 text-xs text-right text-gray-600 dark:text-gray-300">
                        $
                        {resolveUnitPrice(item).toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </td>
                      <td className="px-3 py-1 text-xs text-right text-gray-600 dark:text-gray-300">
                        $
                        {resolveUnitCost(item).toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </td>
                      <td className="px-3 py-1 text-xs text-right text-gray-600 dark:text-gray-300">
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={quantity || ""}
                          onChange={(event) =>
                            handleQuantityChange(itemKey, event.target.value)
                          }
                          className="h-9 w-24 rounded border border-gray-300 px-2 text-right text-xs focus:border-blue-400 focus:outline-hidden focus:ring-2 focus:ring-blue-200 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                        />
                      </td>
                      <td className="px-3 py-1 text-xs text-right">
                        <button
                          type="button"
                          onClick={() => handleAddItem(item)}
                          disabled={!itemKey}
                          className={`rounded-md px-3 py-1 text-xs font-medium text-white focus:outline-hidden focus:ring-2 focus:ring-green-400 ${
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
        )}
      </div>
    </div>
  );
}

export default SalesOrderItemSearch;
