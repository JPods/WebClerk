/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import DataTable, { TableColumn } from "react-data-table-component";
import { useTheme } from "../../../../context/ThemeContext";
import { useAdminWorkspace } from "../AdminWorkspaceProvider";
import type { AdminFieldDescriptor, AdminRecord } from "../types";
import { submitSearchFeedback } from "../../../support/services/aiApi";
import { FieldCustomizerModal } from "./FieldCustomizerModal";
import { FilterDrawer } from "./FilterDrawer";

type SortDirection = "asc" | "desc";

type BadgeProps = {
  intent?: "neutral" | "success" | "danger" | "warning" | "info";
  children: ReactNode;
};

const Badge = ({ intent = "neutral", children }: BadgeProps) => {
  const intentClasses: Record<string, string> = {
    neutral: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
    success: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
    danger: "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300",
    warning: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
    info: "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${intentClasses[intent]}`}>
      {children}
    </span>
  );
};

const resolveBadgeIntent = (value: unknown): BadgeProps["intent"] => {
  if (typeof value !== "string") {
    return "neutral";
  }
  const normalized = value.toLowerCase();
  if (["active", "success", "paid", "complete", "completed", "verified"].some((token) => normalized.includes(token))) {
    return "success";
  }
  if (["pending", "in progress", "hold", "waiting"].some((token) => normalized.includes(token))) {
    return "warning";
  }
  if (["error", "failed", "declined", "inactive", "blocked", "cancelled", "canceled"].some((token) => normalized.includes(token))) {
    return "danger";
  }
  if (["info", "draft", "open"].some((token) => normalized.includes(token))) {
    return "info";
  }
  return "neutral";
};

const formatDateTime = (value: unknown, includeTime = false): string => {
  if (!value) {
    return "--";
  }
  const dateValue = value instanceof Date ? value : new Date(String(value));
  if (Number.isNaN(dateValue.getTime())) {
    return String(value);
  }
  if (includeTime) {
    return `${dateValue.toLocaleDateString()} ${dateValue.toLocaleTimeString()}`;
  }
  return dateValue.toLocaleDateString();
};

const formatCellValue = (value: unknown, record: AdminRecord, field: AdminFieldDescriptor): React.ReactNode => {
  if (field.renderListCell) {
    return field.renderListCell(value, record);
  }
  if (field.format) {
    return field.format(value, record);
  }
  switch (field.kind) {
    case "boolean":
      return <Badge intent={value ? "success" : "danger"}>{value ? "Yes" : "No"}</Badge>;
    case "date":
      return formatDateTime(value, false);
    case "datetime":
      return formatDateTime(value, true);
    case "currency":
      if (typeof value === "number") {
        return value.toLocaleString(undefined, { style: "currency", currency: "USD" });
      }
      if (typeof value === "string") {
        const numeric = Number(value);
        if (!Number.isNaN(numeric)) {
          return numeric.toLocaleString(undefined, { style: "currency", currency: "USD" });
        }
      }
      return "--";
    case "number":
    case "integer":
      if (typeof value === "number") {
        return value.toLocaleString();
      }
      return "--";
    case "badge":
    case "status":
      return <Badge intent={resolveBadgeIntent(value)}>{String(value ?? "--")}</Badge>;
    case "tag":
      if (Array.isArray(value)) {
        return (
          <div className="flex flex-wrap gap-1">
            {value.map((tag) => (
              <Badge key={String(tag)} intent="info">
                {String(tag)}
              </Badge>
            ))}
          </div>
        );
      }
      return String(value ?? "--");
    default:
      if (value === undefined || value === null || value === "") {
        return "--";
      }
      return String(value);
  }
};

const formatFilterValue = (
  value: unknown,
  fieldId: string,
  fieldDefinitions: AdminFieldDescriptor[]
): string => {
  const definition = fieldDefinitions.find((field) => field.id === fieldId);
  if (!definition) {
    return Array.isArray(value) ? value.join(", ") : String(value);
  }
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (typeof value === "object" && value !== null) {
    const maybeRange = value as { from?: string | number; to?: string | number };
    return `${maybeRange.from ?? ""} -> ${maybeRange.to ?? ""}`;
  }
  return String(value);
};

export const RecordListColumn = () => {
  const {
    selectedTable,
    selectedRecordId,
    setSelectedRecordId,
    list,
    listFields,
    hiddenListFields,
    setListSearch,
    setListFilters,
    setListSort,
    setListPage,
    setListPageSize,
    resetListFilters,
    refreshList,
    updateListLayout,
    resetListLayout,
  } = useAdminWorkspace();

  const { theme } = useTheme();

  const [searchDraft, setSearchDraft] = useState(list.search ?? "");
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [isCustomizerOpen, setIsCustomizerOpen] = useState(false);

  // ── Search feedback state ──────────────────────────────────────
  const [feedbackSent, setFeedbackSent] = useState<1 | -1 | null>(null);
  const [showCoaching, setShowCoaching] = useState(false);
  const [coachingText, setCoachingText] = useState("");
  const lastFeedbackQuery = useRef("");

  // Reset feedback state when search changes
  useEffect(() => {
    if (list.search !== lastFeedbackQuery.current) {
      setFeedbackSent(null);
      setShowCoaching(false);
      setCoachingText("");
    }
  }, [list.search]);

  const handleSearchFeedback = useCallback(
    async (rating: 1 | -1, coaching = "") => {
      const query = list.search?.trim();
      const modelKey = selectedTable?.id;
      if (!query || !modelKey) return;

      lastFeedbackQuery.current = query;
      setFeedbackSent(rating);

      if (rating < 0) {
        setShowCoaching(true);
      } else {
        setShowCoaching(false);
      }

      try {
        await submitSearchFeedback({
          rating,
          query,
          parent_model: modelKey,
          result_count: list.total,
          coaching,
        });
      } catch {
        // Feedback is best-effort — don't disrupt the user
      }
    },
    [list.search, list.total, selectedTable?.id],
  );

  const handleCoachingSubmit = useCallback(() => {
    if (coachingText.trim()) {
      handleSearchFeedback(-1, coachingText.trim());
    }
    setShowCoaching(false);
  }, [coachingText, handleSearchFeedback]);

  useEffect(() => {
    setSearchDraft(list.search ?? "");
  }, [list.search]);

  useEffect(() => {
    const handler = window.setTimeout(() => {
      if ((list.search ?? "") !== searchDraft) {
        setListSearch(searchDraft);
      }
    }, 200);
    return () => window.clearTimeout(handler);
  }, [searchDraft, setListSearch, list.search]);

  const columns: TableColumn<AdminRecord>[] = useMemo(() => {
    return listFields.map((field) => {
      const column: TableColumn<AdminRecord> = {
        id: field.id,
        name: field.label,
        sortable: Boolean(field.sortable),
        minWidth: field.minWidth,
        width: field.width,
        sortField: field.id,
        selector: (row: AdminRecord) => String(row[field.id] ?? ''),
        cell: (row: AdminRecord) => formatCellValue(row[field.id], row, field),
        center: field.align === "center",
        right: field.align === "right",
        wrap: field.kind === "text" || field.kind === "json",
      };
      return column;
    });
  }, [listFields]);

  const conditionalRowStyles = useMemo(
    () => [
      {
        when: (row: AdminRecord) => row.id === selectedRecordId,
        style: {
          backgroundColor: "#dbeafe",
          color: "#0f172a",
        },
      },
    ],
    [selectedRecordId]
  );

  const handleSort = useCallback(
    (column: TableColumn<AdminRecord>, direction: SortDirection) => {
      if (!column.sortField) {
        setListSort(null);
        return;
      }
      setListSort({ fieldId: String(column.sortField), direction });
    },
    [setListSort]
  );

  const handleRowClick = useCallback(
    (record: AdminRecord) => {
      setSelectedRecordId(record.id);
    },
    [setSelectedRecordId]
  );

  const activeFilters = list.filters ?? {};
  const hasActiveFilters = Object.keys(activeFilters).length > 0;

  return (
    <section className="flex h-full flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              {selectedTable?.label ?? "Records"}
            </p>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {selectedTable?.description ?? "Browse records"}
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => refreshList()}
              className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Refresh
            </button>
            <button
              type="button"
              onClick={() => setIsFilterOpen(true)}
              className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Filters
              {hasActiveFilters && (
                <span className="ml-1 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-sky-600 px-2 text-xs font-semibold text-white">
                  {Object.keys(activeFilters).length}
                </span>
              )}
            </button>
            <button
              type="button"
              onClick={() => setIsCustomizerOpen(true)}
              className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Columns
            </button>
          </div>
        </div>
        <div className="mt-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="relative w-full max-w-md">
            <input
              type="search"
              placeholder="Fragments: acm, 102 · @west = contains"
              value={searchDraft}
              onChange={(event) => setSearchDraft(event.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 pr-8 py-2 text-sm text-slate-900 shadow-sm transition focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
            {searchDraft && (
              <button
                type="button"
                onClick={() => setSearchDraft("")}
                className="absolute inset-y-0 right-3 flex items-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                aria-label="Clear search"
              >
                X
              </button>
            )}
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <span>Total records:</span>
            <Badge intent="info">{list.total.toLocaleString()}</Badge>
          </div>
        </div>
        {/* Search feedback — appears when search is active and not loading */}
        {list.search && !list.loading && (
          <div className="mt-2 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            {feedbackSent === null ? (
              <>
                <span>Did you find what you needed?</span>
                <button
                  type="button"
                  onClick={() => handleSearchFeedback(1)}
                  className="rounded px-1.5 py-0.5 text-emerald-600 transition hover:bg-emerald-50 dark:text-emerald-400 dark:hover:bg-emerald-900/30"
                  title="Yes, found it"
                >
                  &#x1F44D;
                </button>
                <button
                  type="button"
                  onClick={() => handleSearchFeedback(-1)}
                  className="rounded px-1.5 py-0.5 text-rose-600 transition hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-900/30"
                  title="No, couldn't find it"
                >
                  &#x1F44E;
                </button>
              </>
            ) : feedbackSent > 0 ? (
              <span className="text-emerald-600 dark:text-emerald-400">Thanks!</span>
            ) : (
              <span className="text-amber-600 dark:text-amber-400">Noted — Alice will look into this.</span>
            )}
          </div>
        )}
        {/* Coaching input — appears on negative feedback */}
        {showCoaching && feedbackSent === -1 && (
          <div className="mt-2 flex items-center gap-2">
            <input
              type="text"
              placeholder="What were you looking for?"
              value={coachingText}
              onChange={(e) => setCoachingText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCoachingSubmit()}
              className="flex-1 rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
            <button
              type="button"
              onClick={handleCoachingSubmit}
              className="rounded-md bg-sky-600 px-2 py-1 text-xs font-medium text-white transition hover:bg-sky-700"
            >
              Send
            </button>
            <button
              type="button"
              onClick={() => setShowCoaching(false)}
              className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            >
              Skip
            </button>
          </div>
        )}
        {hasActiveFilters && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {Object.entries(activeFilters).map(([filterKey, value]) => (
              <Badge key={filterKey} intent="info">
                {filterKey}: {formatFilterValue(value, filterKey, selectedTable?.fields ?? [])}
              </Badge>
            ))}
            <button
              type="button"
              onClick={resetListFilters}
              className="text-xs font-medium text-slate-500 underline transition hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            >
              Clear all
            </button>
          </div>
        )}
        {list.error && (
          <div className="mt-3 rounded-md border border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-700 dark:border-rose-500/40 dark:bg-rose-950/40 dark:text-rose-200">
            {list.error}
          </div>
        )}
      </div>
      <div className="flex-1 overflow-hidden">
        <div className="h-full overflow-auto">
          <DataTable
            keyField="id"
            columns={columns}
            data={list.items}
            conditionalRowStyles={conditionalRowStyles}
            highlightOnHover
            pointerOnHover
            dense
            theme={theme === "dark" ? "tailwindDark" : "default"}
            responsive
            progressPending={list.loading}
            progressComponent={<div className="p-8 text-center text-sm text-slate-500 dark:text-slate-400">Loading records...</div>}
            noDataComponent={<div className="p-8 text-center text-sm text-slate-500 dark:text-slate-400">No records found</div>}
            onRowClicked={handleRowClick}
            sortServer
            onSort={handleSort}
            defaultSortAsc={list.sort?.direction !== "desc"}
            defaultSortFieldId={list.sort?.fieldId}
            pagination
            paginationServer
            paginationTotalRows={list.total}
            paginationPerPage={list.pageSize}
            paginationRowsPerPageOptions={list.pageSizeOptions}
            paginationDefaultPage={list.page}
            onChangeRowsPerPage={(newPageSize: number) => setListPageSize(newPageSize)}
            onChangePage={(newPage: number) => setListPage(newPage)}
          />
        </div>
      </div>
      <FieldCustomizerModal
        open={isCustomizerOpen}
        onClose={() => setIsCustomizerOpen(false)}
        onSave={updateListLayout}
        onReset={resetListLayout}
        availableFields={selectedTable?.fields ?? []}
        visibleFieldIds={listFields.map((field) => field.id)}
        hiddenFieldIds={hiddenListFields.map((field) => field.id)}
        title={`${selectedTable?.label ?? "Records"} list`}
        view="list"
      />
      <FilterDrawer
        open={isFilterOpen}
        onClose={() => setIsFilterOpen(false)}
        definitions={selectedTable?.filterDefinitions}
        values={activeFilters}
        onApply={setListFilters}
        onClear={resetListFilters}
      />
    </section>
  );
};
