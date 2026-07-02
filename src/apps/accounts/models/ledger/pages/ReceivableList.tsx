/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import DataGrid from "@/components/common/DataGrid";
import type { ColumnFilter } from "@/components/common/ButtonToolbar";
import ComponentCard from "@/components/common/ComponentCard";
import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { manageAction } from "@/api/wcapi";
import { FaEye, FaSyncAlt } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import ButtonToolbar from "@/components/common/ButtonToolbar";

// ── Types ─────────────────────────────────────────────────────────────
export interface ReceivableRow {
  org_id: number;
  org_name: string;
  future: number;
  current: number;
  period_1: number;
  period_2: number;
  period_3: number;
  total: number;
  count: number;
}

interface AgingResponse {
  as_of_date: string;
  totals: Omit<ReceivableRow, "org_id" | "org_name">;
  rows: ReceivableRow[];
}

// ── Formatting helpers ────────────────────────────────────────────────
const fmt = (v: number) =>
  v === 0
    ? "–"
    : v.toLocaleString("en-US", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 2,
      });

/** Tailwind text colour mapped to aging severity. */
const agingColor = (bucket: string): string => {
  switch (bucket) {
    case "future":
      return "text-slate-500";
    case "current":
      return "text-green-700 dark:text-green-400";
    case "period_1":
      return "text-yellow-600 dark:text-yellow-400";
    case "period_2":
      return "text-orange-600 dark:text-orange-400";
    case "period_3":
      return "text-red-600 dark:text-red-400";
    default:
      return "";
  }
};

// ── Component ─────────────────────────────────────────────────────────
export default function ReceivableList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<ReceivableRow[]>([]);
  const [asOfDate, setAsOfDate] = useState<string>("");
  const [totals, setTotals] = useState<AgingResponse["totals"] | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const [selectedRows, setSelectedRows] = useState<ReceivableRow[]>([]);
  const tableRef = useRef<any>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  // ── Fetch aging data via manage action ──────────────────────────────
  const fetchAging = useCallback(
    async (overrideDate?: string) => {
      try {
        setLoading(true);
        const params: Record<string, any> = {};
        if (overrideDate) params.as_of_date = overrideDate;
        const res = (await manageAction(
          "get_receivable_aging",
          params,
        )) as AgingResponse;
        setData(res.rows ?? []);
        setAsOfDate(res.as_of_date ?? "");
        setTotals(res.totals ?? null);
      } catch (err) {
        console.error("Failed to fetch receivable aging", err);
        dispatch(
          showToast({
            message: "Failed to load receivable aging",
            type: "error",
          }),
        );
      } finally {
        setLoading(false);
      }
    },
    [dispatch],
  );

  useEffect(() => {
    fetchAging();
  }, [fetchAging]);

  // ── Column definitions ─────────────────────────────────────────────
  const columns: any[] = useMemo(
    () => [
      {
        id: "org_name",
        name: "Customer",
        selector: (r) => r.org_name,
        sortable: true,
        width: "22%",
        cell: (r) => (
          <span className="font-medium text-gray-900 dark:text-white truncate">
            {r.org_name}
          </span>
        ),
      },
      {
        id: "future",
        name: "Future",
        selector: (r) => r.future,
        sortable: true,
        right: true,
        width: "11%",
        cell: (r) => (
          <span className={agingColor("future")}>{fmt(r.future)}</span>
        ),
      },
      {
        id: "current",
        name: "Current",
        selector: (r) => r.current,
        sortable: true,
        right: true,
        width: "11%",
        cell: (r) => (
          <span className={agingColor("current")}>{fmt(r.current)}</span>
        ),
      },
      {
        id: "period_1",
        name: "1–30 Days",
        selector: (r) => r.period_1,
        sortable: true,
        right: true,
        width: "11%",
        cell: (r) => (
          <span className={agingColor("period_1")}>{fmt(r.period_1)}</span>
        ),
      },
      {
        id: "period_2",
        name: "31–60 Days",
        selector: (r) => r.period_2,
        sortable: true,
        right: true,
        width: "11%",
        cell: (r) => (
          <span className={agingColor("period_2")}>{fmt(r.period_2)}</span>
        ),
      },
      {
        id: "period_3",
        name: "60+ Days",
        selector: (r) => r.period_3,
        sortable: true,
        right: true,
        width: "11%",
        cell: (r) => (
          <span className={agingColor("period_3")}>{fmt(r.period_3)}</span>
        ),
      },
      {
        id: "total",
        name: "Total",
        selector: (r) => r.total,
        sortable: true,
        right: true,
        width: "12%",
        cell: (r) => (
          <span className="font-semibold text-gray-900 dark:text-white">
            {fmt(r.total)}
          </span>
        ),
      },
      {
        id: "count",
        name: "Items",
        selector: (r) => r.count,
        sortable: true,
        center: true,
        width: "6%",
      },
      {
        id: "actions",
        name: "",
        cell: (r) => (
          <button
            onClick={() =>
              window.open(`/org/organization/detail/${r.org_id}`, "_blank")
            }
            title="View customer"
          >
            <FaEye className="text-blue-600 hover:scale-110 transition" />
          </button>
        ),
        ignoreRowClick: true,
        button: true,
        width: "50px",
      },
    ],
    [],
  );

  // ── Filters ────────────────────────────────────────────────────────
  const filters: ColumnFilter[] = useMemo(
    () => [{ key: "org_name", label: "Customer", type: "text" }],
    [],
  );

  const filteredData = useMemo(() => {
    if (Object.keys(filterValues).length === 0) return data;
    return data.filter((row) =>
      Object.entries(filterValues).every(([key, value]) => {
        if (!value) return true;
        const rv = String((row as any)[key] || "").toLowerCase();
        return rv.includes(value.toLowerCase());
      }),
    );
  }, [data, filterValues]);

  const visibleColumns = useMemo(() => {
    if (columnVisibility.length === 0) return columns;
    return columns.filter(
      (_: any, i: number) => columnVisibility[i] !== false,
    );
  }, [columns, columnVisibility]);

  // ── Totals footer row ──────────────────────────────────────────────
  const totalsBar = totals ? (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-1 px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-b text-sm font-semibold border-t dark:border-gray-700">
      <span className="text-gray-500 uppercase text-xs tracking-wide">
        Totals
      </span>
      <span className={agingColor("future")}>
        Future: {fmt(totals.future)}
      </span>
      <span className={agingColor("current")}>
        Current: {fmt(totals.current)}
      </span>
      <span className={agingColor("period_1")}>
        1–30: {fmt(totals.period_1)}
      </span>
      <span className={agingColor("period_2")}>
        31–60: {fmt(totals.period_2)}
      </span>
      <span className={agingColor("period_3")}>
        60+: {fmt(totals.period_3)}
      </span>
      <span className="text-gray-900 dark:text-white ml-auto">
        Total: {fmt(totals.total)}
      </span>
      <span className="text-gray-500">{totals.count} items</span>
    </div>
  ) : null;

  // ── Render ─────────────────────────────────────────────────────────
  return (
    <>
      <ButtonToolbar
        pageTitle="Receivable Aging"
        title="Receivable"
        modelKey="ledger"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedRows}
        selectedCount={selectedRows.length}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={() => fetchAging()}
        loading={loading}
        columns={columns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="receivable-aging"
        filters={filters}
        filterValues={filterValues}
        onFilterValuesChange={setFilterValues}
        filtersOpen={filtersOpen}
        onFiltersOpenChange={setFiltersOpen}
      />

      {asOfDate && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
          As of {asOfDate}
        </p>
      )}

      <div className="grid grid-cols-1 gap-6">
        <ComponentCard>
          <DataGrid
            ref={tableRef}
            data={filteredData}
            columns={visibleColumns}
            title="Receivable Aging"
            loading={loading}
            filters={filters}
            storageKey="receivable-aging"
            enableExport={true}
            enableSelection={false}
            onSelectionChange={setSelectedRows}
            exportFileName="receivable_aging_export"
            searchPlaceholder="Search customers..."
            noDataMessage="No open receivables"
            externalSearchTerm={searchTerm}
            onExternalSearchTermChange={setSearchTerm}
            hideHeader={true}
          />
          {totalsBar}
        </ComponentCard>
      </div>
    </>
  );
}
