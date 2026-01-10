import { useState, useEffect, useMemo, useCallback } from "react";
import { TableColumn } from "react-data-table-component";
import { FaPlus, FaEye, FaEdit, FaTrash, FaCheck, FaTimes } from "react-icons/fa";
import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "../../../../../components/common/AdvancedDataTable";
import { Actions, patchAction } from "../../../../../api/userProfile";
import { useNavigate } from "react-router";
import { useDispatch } from "react-redux";
import { showToast } from "../../../../../store/slices/toastSlice";
import Badge from "../../../../../components/ui/badge/Badge";
import ActionDetail from "./ActionDetail";
import { PageRoutes } from "../../../../../routes/Routes";

interface ActionData {
  id: string | number;
  action?: Record<string, string>;
  description?: Record<string, string>;
  kanban_column?: string;
  priority?: number;
  difficulty?: number;
  status?: string;
  progress?: number;
  dt_due?: number | string | null;
  dt_start?: number | string | null;
  dt_end?: number | string | null;
  project_name?: string;
  assigned_to?: Array<{ name?: string; id?: string | number }>;
  languages?: string[];
  [key: string]: any;
}

const ActionListPage = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const [data, setData] = useState<ActionData[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedActions, setSelectedActions] = useState<ActionData[]>([]);
  const [selectedAction, setSelectedAction] = useState<ActionData | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);

  // Helper to extract translated text
  const getTranslatedText = useCallback((
    translations: Record<string, string> | undefined,
    languages: string[] | undefined
  ): string => {
    if (!translations || typeof translations !== "object") return "";
    
    // Try to get text in order of preference
    const preferredLangs = ["en", "ar", "bn", "es"];
    const availableLangs = languages || Object.keys(translations);
    
    for (const lang of preferredLangs) {
      if (translations[lang]) return translations[lang];
    }
    
    // Return first available translation
    for (const lang of availableLangs) {
      if (translations[lang]) return translations[lang];
    }
    
    return Object.values(translations)[0] || "";
  }, []);

  // Get priority label
  const getPriorityLabel = useCallback((priority: number): string => {
    const labels: Record<number, string> = {
      1: "Low",
      2: "Medium",
      3: "High",
      4: "Critical",
    };
    return labels[priority] || `Priority ${priority}`;
  }, []);

  // Get priority badge color
  const getPriorityColor = useCallback((priority: number): string => {
    const colors: Record<number, string> = {
      1: "success",
      2: "warning",
      3: "error",
      4: "error",
    };
    return colors[priority] || "default";
  }, []);

  // Format date
  const formatDate = useCallback((timestamp: number | string | null | undefined): string => {
    if (!timestamp) return "-";
    
    try {
      const date = typeof timestamp === "number" 
        ? new Date(timestamp) 
        : new Date(timestamp);
      
      if (isNaN(date.getTime())) return "-";
      
      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {
      return "-";
    }
  }, []);

  // Extract unique values for filters
  const filterOptions = useMemo(() => {
    const statuses = new Set<string>();
    const projects = new Set<string>();
    const columns = new Set<string>();
    const priorities = new Set<number>();

    data.forEach((action) => {
      if (action.status) statuses.add(action.status);
      if (action.project_name) projects.add(action.project_name);
      if (action.kanban_column) columns.add(action.kanban_column);
      if (action.priority !== undefined && action.priority !== null) {
        priorities.add(action.priority);
      }
    });

    return {
      statuses: Array.from(statuses).map((s) => ({ value: s, label: s })),
      projects: Array.from(projects).map((p) => ({ value: p, label: p })),
      columns: Array.from(columns).map((c) => ({ value: c, label: c })),
      priorities: Array.from(priorities)
        .sort((a, b) => a - b)
        .map((p) => ({ value: String(p), label: getPriorityLabel(p) })),
    };
  }, [data, getPriorityLabel]);

  // Fetch actions
  const fetchActions = useCallback(async () => {
    setLoading(true);
    try {
      const response = await Actions();
      
      if (response && response.status === 200) {
        const apiData = response.data?.data;
        
        // Extract actions array from various possible structures
        let actions: ActionData[] = [];
        
        if (Array.isArray(apiData)) {
          actions = apiData;
        } else if (apiData && typeof apiData === "object") {
          if (Array.isArray(apiData.results)) {
            actions = apiData.results;
          } else if (Array.isArray(apiData.data)) {
            actions = apiData.data;
          } else if (Array.isArray(apiData.actions)) {
            actions = apiData.actions;
          }
        }

        // Normalize action data
        const normalizedActions = actions.map((action, index) => ({
          ...action,
          id: action.id || action.pk || action.uuid || `temp-${index}`,
          // Extract primary language text for display
          actionText: getTranslatedText(action.action, action.languages),
          descriptionText: getTranslatedText(action.description, action.languages),
        }));

        setData(normalizedActions);
      } else {
        throw new Error("Failed to fetch actions");
      }
    } catch (error) {
      console.error("Error fetching actions:", error);
      dispatch(
        showToast({
          message: "Failed to load actions. Please try again.",
          type: "error",
        })
      );
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [dispatch, getTranslatedText]);

  useEffect(() => {
    fetchActions();
  }, [fetchActions]);

  // Handle delete
  const handleDelete = useCallback(
    async (id: string | number) => {
      if (!window.confirm("Are you sure you want to delete this action?")) {
        return;
      }

      try {
        // Implement delete logic here using patchAction or appropriate API
        await patchAction({
          model_name: "action",
          id,
          method: "delete",
        });

        dispatch(
          showToast({
            message: "Action deleted successfully",
            type: "success",
          })
        );

        // Refresh data
        fetchActions();
      } catch (error) {
        console.error("Error deleting action:", error);
        dispatch(
          showToast({
            message: "Failed to delete action",
            type: "error",
          })
        );
      }
    },
    [dispatch, fetchActions]
  );

  // Define table columns
  const columns: TableColumn<ActionData>[] = useMemo(
    () => [
      // {
      //   name: "#",
      //   selector: (_row: ActionData, index?: number) => (index !== undefined ? index + 1 : 0),
      //   sortable: false,
      //   width: "80px",
      //   cell: (_row: ActionData, index: number) => (
      //     <div className="text-center font-medium text-gray-700 dark:text-gray-300">
      //       {index + 1}
      //     </div>
      //   ),
      // },
      {
        name: "ID",
        selector: (row: ActionData) => row.id || "-",
        sortable: true,
        width: "100px",
        cell: (row: ActionData) => (
          <div 
            onClick={(e) => {
              e.stopPropagation();
              handleEdit(row);
            }}
            className="text-xs font-mono text-blue-600 dark:text-blue-400 cursor-pointer hover:underline"
          >
            {row.id || "-"}
          </div>
        ),
      },
      {
        name: "Action",
        selector: (row: ActionData) => row.actionText || "-",
        sortable: true,
        wrap: true,
        width: "250px",
        cell: (row: ActionData) => (
          <div className="py-2">
            <div className="font-medium text-gray-900 dark:text-gray-100">
              {row.actionText || "Untitled"}
            </div>
            {row.descriptionText && (
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                {row.descriptionText}
              </div>
            )}
          </div>
        ),
      },
      {
        name: "Project",
        selector: (row: ActionData) => row.project_name || "-",
        sortable: true,
        width: "150px",
        cell: (row: ActionData) => (
          <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
            {row.project_name || "-"}
          </span>
        ),
      },
      {
        name: "Status",
        selector: (row: ActionData) => row.status || "-",
        sortable: true,
        width: "120px",
        cell: (row: ActionData) => (
          <Badge type={row.status === "active" ? "success" : "default"}>
            {row.status || "N/A"}
          </Badge>
        ),
      },
      {
        name: "Column",
        selector: (row: ActionData) => row.kanban_column || "-",
        sortable: true,
        width: "130px",
      },
      {
        name: "Priority",
        selector: (row: ActionData) => row.priority || 0,
        sortable: true,
        width: "110px",
        cell: (row: ActionData) => (
          <Badge type={getPriorityColor(row.priority || 0)}>
            {getPriorityLabel(row.priority || 0)}
          </Badge>
        ),
      },
      {
        name: "Progress",
        selector: (row: ActionData) => row.progress || 0,
        sortable: true,
        width: "110px",
        cell: (row: ActionData) => (
          <div className="w-full">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                {row.progress || 0}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2 dark:bg-gray-700">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${Math.min(100, row.progress || 0)}%` }}
              ></div>
            </div>
          </div>
        ),
      },
      {
        name: "Assigned To",
        selector: (row: ActionData) =>
          row.assigned_to?.map((a) => a.name).join(", ") || "-",
        sortable: false,
        width: "150px",
        cell: (row: ActionData) => {
          const assignees = row.assigned_to || [];
          if (assignees.length === 0) return <span className="text-gray-400">Unassigned</span>;
          
          return (
            <div className="flex flex-wrap gap-1">
              {assignees.slice(0, 2).map((assignee, idx) => (
                <span
                  key={idx}
                  className="px-2 py-1 text-xs rounded-full bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200"
                >
                  {assignee.name}
                </span>
              ))}
              {assignees.length > 2 && (
                <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                  +{assignees.length - 2}
                </span>
              )}
            </div>
          );
        },
      },
      {
        name: "Due Date",
        selector: (row: ActionData) => row.dt_due || "-",
        sortable: true,
        width: "120px",
        cell: (row: ActionData) => (
          <span className="text-sm">{formatDate(row.dt_due)}</span>
        ),
      },
      {
        name: "Actions",
        width: "140px",
        cell: (row: ActionData) => (
          <div className="flex items-center gap-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleView(row);
              }}
              className="p-2 text-blue-600 hover:bg-blue-50 rounded dark:hover:bg-blue-900/20 transition-colors"
              title="View"
            >
              <FaEye className="w-4 h-4" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleEdit(row);
              }}
              className="p-2 text-green-600 hover:bg-green-50 rounded dark:hover:bg-green-900/20 transition-colors"
              title="Edit"
            >
              <FaEdit className="w-4 h-4" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleDelete(row.id);
              }}
              className="p-2 text-red-600 hover:bg-red-50 rounded dark:hover:bg-red-900/20 transition-colors"
              title="Delete"
            >
              <FaTrash className="w-4 h-4" />
            </button>
          </div>
        ),
      },
    ],
    [navigate, handleDelete]
  );

  // Define filters
  const filters: ColumnFilter[] = useMemo(
    () => [
      {
        key: "status",
        label: "Status",
        type: "select",
        options: filterOptions.statuses,
      },
      {
        key: "project_name",
        label: "Project",
        type: "select",
        options: filterOptions.projects,
      },
      {
        key: "kanban_column",
        label: "Column",
        type: "select",
        options: filterOptions.columns,
      },
      {
        key: "priority",
        label: "Priority",
        type: "select",
        options: filterOptions.priorities,
      },
    ],
    [filterOptions]
  );

  // Handle bulk operations
  const handleBulkDelete = useCallback(async () => {
    if (selectedActions.length === 0) {
      dispatch(
        showToast({
          message: "Please select actions to delete",
          type: "warning",
        })
      );
      return;
    }

    if (
      !window.confirm(
        `Are you sure you want to delete ${selectedActions.length} action(s)?`
      )
    ) {
      return;
    }

    try {
      // Implement bulk delete logic
      await Promise.all(
        selectedActions.map((action) =>
          patchAction({
            model_name: "action",
            id: action.id,
            method: "delete",
          })
        )
      );

      dispatch(
        showToast({
          message: `${selectedActions.length} action(s) deleted successfully`,
          type: "success",
        })
      );

      fetchActions();
      setSelectedActions([]);
    } catch (error) {
      console.error("Error in bulk delete:", error);
      dispatch(
        showToast({
          message: "Failed to delete some actions",
          type: "error",
        })
      );
    }
  }, [selectedActions, dispatch, fetchActions]);

  // Handle view action
  const handleView = (row: ActionData) => {
    setSelectedAction(row);
    setFormMode("view");
  };

  // Handle edit action
  const handleEdit = (row: ActionData) => {
    setSelectedAction(row);
    setFormMode("edit");
  };

  // Handle add new action - navigate to separate page
  const handleAdd = () => {
    navigate(PageRoutes.actionDetail.replace("/:id?", ""));
  };

  // Handle form saved
  const handleFormSaved = () => {
    fetchActions();
    setFormMode(null);
    setSelectedAction(null);
  };

  // Handle form cancel
  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedAction(null);
  };

  return (
    <>
      <PageBreadcrumb pageTitle="Actions List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
          data={data}
          columns={columns}
          title="Actions"
          loading={loading}
          filters={filters}
          enableExport={true}
          enableSelection={true}
          onSelectionChange={setSelectedActions}
          exportFileName="actions_export"
          searchPlaceholder="Search actions, projects, assignees..."
          noDataMessage="No actions found"
          customActions={
            <div className="flex gap-2">
              {selectedActions.length > 0 && (
                <button
                  onClick={handleBulkDelete}
                  className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                >
                  <FaTrash className="w-4 h-4" />
                  Delete ({selectedActions.length})
                </button>
              )}
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
              >
                <FaPlus className="w-4 h-4" />
                New Action
              </button>
            </div>
          }
          onRowClicked={handleEdit}
        />
      </ComponentCard>
    </div>
    {formMode && (
      <div className="lg:col-span-2">
        <ActionDetail
          inline
          modeProp={formMode}
          dataProp={selectedAction}
          onSaved={handleFormSaved}
          onCancelInline={handleFormCancel}
        />
      </div>
    )}
  </div>
    </>
  );
};

export default ActionListPage;
