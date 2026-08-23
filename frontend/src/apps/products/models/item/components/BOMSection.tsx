/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * BOMSection - Bill of Materials display component
 * 
 * Shows the component children of an assembled/bundled item in a collapsible table.
 * Displays SKU, description, quantity, unit cost, and extended cost for each component.
 */
import { useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "../../../../../components/ui/table";
import Badge from "../../../../../components/ui/badge/Badge";
import { fetchBOMLines, type BOMLine } from "../services/bomApi";

// ============================================================================
// Types
// ============================================================================

interface BOMSectionProps {
  itemId: number;
  defaultOpen?: boolean;
}

// ============================================================================
// BOM Table Component
// ============================================================================

function BOMTable({ lines }: { lines: BOMLine[] }) {
  const formatCurrency = (val: number | string | null | undefined): string => {
    if (val === null || val === undefined || val === "") return "—";
    const num = typeof val === "string" ? parseFloat(val) : val;
    if (isNaN(num)) return "—";
    return `$${num.toFixed(2)}`;
  };

  const formatQty = (val: number | string): string => {
    const num = typeof val === "string" ? parseFloat(val) : val;
    if (isNaN(num)) return "—";
    return num % 1 === 0 ? num.toString() : num.toFixed(2);
  };

  // Calculate totals
  const totalExtended = lines.reduce((sum, line) => {
    const cost = typeof line.extended_cost === "string" 
      ? parseFloat(line.extended_cost) 
      : (line.extended_cost || 0);
    return sum + (isNaN(cost) ? 0 : cost);
  }, 0);

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader className="bg-gray-50 dark:bg-gray-800">
          <TableRow>
            <TableCell isHeader className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
              SKU
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
              Description
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
              Qty
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
              Unit Cost
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
              Extended
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
              Flags
            </TableCell>
          </TableRow>
        </TableHeader>
        <TableBody>
          {lines.map((line) => (
            <TableRow
              key={line.id}
              className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50"
            >
              <TableCell className="px-4 py-3 font-mono text-sm text-blue-600 dark:text-blue-400">
                {line.component?.sku || "—"}
              </TableCell>
              <TableCell className="px-4 py-3 text-gray-800 dark:text-gray-200">
                {line.description || line.component?.description || line.component?.name || "—"}
              </TableCell>
              <TableCell className="px-4 py-3 text-center font-medium text-gray-800 dark:text-white">
                {formatQty(line.quantity)}
              </TableCell>
              <TableCell className="px-4 py-3 text-right text-gray-600 dark:text-gray-400">
                {formatCurrency(line.cost_snapshot)}
              </TableCell>
              <TableCell className="px-4 py-3 text-right font-medium text-gray-800 dark:text-white">
                {formatCurrency(line.extended_cost)}
              </TableCell>
              <TableCell className="px-4 py-3 text-center">
                <div className="flex justify-center gap-1 flex-wrap">
                  {(line.component_child_count ?? 0) > 0 && (
                    <Badge color="info" size="sm">
                      {line.component_child_count} child{line.component_child_count !== 1 ? 'ren' : ''}
                    </Badge>
                  )}
                  {line.is_optional && (
                    <Badge color="warning" size="sm">Optional</Badge>
                  )}
                  {line.is_alternate && (
                    <Badge color="primary" size="sm">Alt</Badge>
                  )}
                  {(() => {
                    const scrap = typeof line.scrap_factor === "string" 
                      ? parseFloat(line.scrap_factor) 
                      : line.scrap_factor;
                    return scrap > 0 ? (
                      <Badge color="error" size="sm">
                        +{(scrap * 100).toFixed(0)}% scrap
                      </Badge>
                    ) : null;
                  })()}
                </div>
              </TableCell>
            </TableRow>
          ))}
          {/* Total Row */}
          <TableRow className="bg-gray-50 dark:bg-gray-800 font-semibold">
            <TableCell className="px-4 py-3" colSpan={4}>
              <span className="text-gray-600 dark:text-gray-400">
                Total ({lines.length} component{lines.length !== 1 ? "s" : ""})
              </span>
            </TableCell>
            <TableCell className="px-4 py-3 text-right text-blue-600 dark:text-blue-400">
              {formatCurrency(totalExtended)}
            </TableCell>
            <TableCell className="px-4 py-3">{""}</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>
  );
}

// ============================================================================
// Empty State
// ============================================================================

function BOMEmptyState() {
  return (
    <div className="py-8 text-center text-gray-500 dark:text-gray-400">
      <svg
        className="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600 mb-3"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
        />
      </svg>
      <p>No BOM components found for this item</p>
      <p className="text-sm mt-1">This item is not an assembly or bundle</p>
    </div>
  );
}

// ============================================================================
// Main BOM Section Component
// ============================================================================

export default function BOMSection({ itemId, defaultOpen = false }: BOMSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bomLines, setBomLines] = useState<BOMLine[]>([]);
  const [lastFetchedId, setLastFetchedId] = useState<number | null>(null);

  // Reset when itemId changes
  useEffect(() => {
    if (itemId !== lastFetchedId) {
      setBomLines([]);
      setError(null);
      setLastFetchedId(null);
    }
  }, [itemId, lastFetchedId]);

  // Fetch BOM data when section opens (lazy load) or itemId changes
  useEffect(() => {
    if (isOpen && itemId && itemId !== lastFetchedId) {
      setLoading(true);
      setError(null);
      fetchBOMLines(itemId)
        .then((data) => {
          setBomLines(data.results || []);
          setLastFetchedId(itemId);
        })
        .catch((err) => {
          console.error("Failed to fetch BOM:", err);
          setError("Failed to load BOM data");
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [isOpen, lastFetchedId, itemId]);

  return (
    <div className="mb-6">
      {/* Section Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800 rounded-t-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-gray-700 dark:text-gray-200">
            Bill of Materials
          </h3>
          {lastFetchedId && bomLines.length > 0 && (
            <Badge color="primary" size="sm">
              {bomLines.length}
            </Badge>
          )}
        </div>
        <svg
          className={`w-5 h-5 text-gray-500 transition-transform ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {/* Section Content */}
      {isOpen && (
        <div className="border border-t-0 border-gray-200 dark:border-gray-700 rounded-b-lg overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
              <span className="ml-2 text-gray-500 dark:text-gray-400">Loading BOM...</span>
            </div>
          ) : error ? (
            <div className="py-8 text-center text-red-500 dark:text-red-400">
              <p>{error}</p>
              <button
                onClick={() => {
                  setLastFetchedId(null);
                  setError(null);
                }}
                className="mt-2 text-sm text-blue-500 hover:text-blue-600"
              >
                Retry
              </button>
            </div>
          ) : bomLines.length === 0 ? (
            <BOMEmptyState />
          ) : (
            <BOMTable lines={bomLines} />
          )}
        </div>
      )}
    </div>
  );
}
