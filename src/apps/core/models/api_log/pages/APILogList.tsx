import ComponentCard from "@/components/common/ComponentCard";
import AdvancedDataTable, { type AdvancedDataTableHandle } from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo, useRef} from "react";
import { getRecords } from "@/api/wcapi";
import { FaEye, FaCheck, FaTimes, FaSync } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import APILogDetail from "./APILogDetail";
import Badge from "@/components/ui/badge/Badge";
import ButtonToolbar from "@/components/common/ButtonToolbar";

interface APILogRecord {
  id: number;
  source: string;
  destination: string;
  method: string;
  endpoint: string;
  status_code: number | null;
  duration_ms: number | null;
  error_message: string;
  correlation_id: string;
  dt_created: string;
  user_id?: number;
}

export default function APILogList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<APILogRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedLog, setSelectedLog] = useState<APILogRecord | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<AdvancedDataTableHandle<any>>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getRecords("api_log", { 
        order_by: "-dt_created",
        limit: 500 
      });
      setData(res.results || []);
    } catch (error) {
      dispatch(showToast({ message: "Failed to load API logs", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handle database search
  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    const query = terms.join(' ');
    setLoading(true);
    try {
      const res = await getRecords("api_log", { 
        order_by: "-dt_created",
        limit: 500,
        search: query
      });
      setData(res.results || []);
    } catch (error) {
      dispatch(showToast({ message: "Search failed", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  const handleView = (row: APILogRecord) => {
    setSelectedLog(row);
    setShowDetail(true);
  };

  const handleCloseDetail = () => {
    setShowDetail(false);
    setSelectedLog(null);
  };

  // Status badge color
  const getStatusBadge = (statusCode: number | null) => {
    if (!statusCode) return <Badge color="light">N/A</Badge>;
    if (statusCode >= 200 && statusCode < 300) {
      return <Badge color="success">{statusCode}</Badge>;
    } else if (statusCode >= 400 && statusCode < 500) {
      return <Badge color="warning">{statusCode}</Badge>;
    } else if (statusCode >= 500) {
      return <Badge color="error">{statusCode}</Badge>;
    }
    return <Badge color="info">{statusCode}</Badge>;
  };

  // Source badge color
  const getSourceBadge = (source: string) => {
    switch (source) {
      case "r25":
        return <Badge color="primary">R25</Badge>;
      case "wc3":
        return <Badge color="info">WC3</Badge>;
      case "ext":
        return <Badge color="light">External</Badge>;
      default:
        return <Badge color="light">{source}</Badge>;
    }
  };

  // Method badge color
  const getMethodBadge = (method: string) => {
    switch (method?.toUpperCase()) {
      case "GET":
        return <Badge color="success">{method}</Badge>;
      case "POST":
        return <Badge color="primary">{method}</Badge>;
      case "PUT":
      case "PATCH":
        return <Badge color="warning">{method}</Badge>;
      case "DELETE":
        return <Badge color="error">{method}</Badge>;
      default:
        return <Badge color="light">{method}</Badge>;
    }
  };

  const formatDuration = (ms: number | null) => {
    if (ms === null || ms === undefined) return "-";
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  const columns: TableColumn<APILogRecord>[] = useMemo(
    () => [
      {
        name: "Time",
        selector: (row: APILogRecord) => row.dt_created,
        cell: (row: APILogRecord) => (
          <span className="text-xs text-gray-600 dark:text-gray-400">
            {formatDate(row.dt_created)}
          </span>
        ),
        sortable: true,
        width: "160px",
      },
      {
        name: "Source",
        selector: (row: APILogRecord) => row.source,
        cell: (row: APILogRecord) => getSourceBadge(row.source),
        sortable: true,
        width: "80px",
      },
      {
        name: "Method",
        selector: (row: APILogRecord) => row.method,
        cell: (row: APILogRecord) => getMethodBadge(row.method),
        sortable: true,
        width: "80px",
      },
      {
        name: "Endpoint",
        selector: (row: APILogRecord) => row.endpoint,
        cell: (row: APILogRecord) => (
          <span className="font-mono text-xs truncate max-w-[300px]" title={row.endpoint}>
            {row.endpoint}
          </span>
        ),
        sortable: true,
        grow: 2,
      },
      {
        name: "Status",
        selector: (row: APILogRecord) => row.status_code || 0,
        cell: (row: APILogRecord) => getStatusBadge(row.status_code),
        sortable: true,
        width: "80px",
      },
      {
        name: "Duration",
        selector: (row: APILogRecord) => row.duration_ms || 0,
        cell: (row: APILogRecord) => (
          <span className={`text-xs ${(row.duration_ms || 0) > 1000 ? "text-red-500" : "text-gray-600 dark:text-gray-400"}`}>
            {formatDuration(row.duration_ms)}
          </span>
        ),
        sortable: true,
        width: "90px",
      },
      {
        name: "Error",
        selector: (row: APILogRecord) => row.error_message || "",
        cell: (row: APILogRecord) =>
          row.error_message ? (
            <FaTimes className="text-red-500" title={row.error_message} />
          ) : (
            <FaCheck className="text-green-500" />
          ),
        width: "60px",
        center: true,
      },
      {
        name: "Actions",
        cell: (row: APILogRecord) => (
          <div className="flex gap-2">
            <button
              onClick={() => handleView(row)}
              className="p-1.5 text-blue-600 hover:bg-blue-50 rounded dark:hover:bg-blue-900/20"
              title="View Details"
            >
              <FaEye size={14} />
            </button>
          </div>
        ),
        width: "70px",
        center: true,
      },
    ],
    []
  );

  // Filter data based on filterValues from ButtonToolbar
  const filteredData = useMemo(() => {
    if (Object.keys(filterValues).length === 0) return data;
    return data.filter((row: any) => {
      return Object.entries(filterValues).every(([key, value]) => {
        if (!value) return true;
        const rowValue = String(row[key] || "").toLowerCase();
        return rowValue.includes(value.toLowerCase());
      });
    });
  }, [data, filterValues]);

  // Filter columns based on visibility from ButtonToolbar
  const visibleColumns = useMemo(() => {
    if (columnVisibility.length === 0) return columns;
    return columns.filter((_: any, index: number) => columnVisibility[index] !== false);
  }, [columns, columnVisibility]);
  return (
    <>
      <ButtonToolbar
        pageTitle="API Logs"
        title="API Logs"
        modelKey="api_logs"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={fetchData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={columns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="api_logs-list"
        filterValues={filterValues}
        onFilterValuesChange={setFilterValues}
        filtersOpen={filtersOpen}
        onFiltersOpenChange={setFiltersOpen}
      />
<ComponentCard title="API Request Logs">
        <div className="mb-4 flex justify-end">
          <button
            onClick={fetchData}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            <FaSync size={12} />
            Refresh
          </button>
        </div>
        <AdvancedDataTable
              ref={tableRef}
          data={filteredData}
          columns={visibleColumns}
          loading={loading}
          enableExport={true}
          enableSelection={false}
          enableDatabaseSearch={true}
          searchDatabase={searchDatabase}
          onSearchModeChange={setSearchDatabase}
          onDatabaseSearch={handleDatabaseSearch}
        
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              hideHeader={true}/>
      </ComponentCard>

      {/* Detail Modal */}
      {showDetail && selectedLog && (
        <APILogDetail log={selectedLog} onClose={handleCloseDetail} />
      )}
    </>
  );
}
