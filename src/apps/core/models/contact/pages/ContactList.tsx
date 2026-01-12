import { useState, useEffect, useMemo, useCallback } from "react";
import { TableColumn } from "react-data-table-component";
import {
  FaPlus,
  FaEye,
  FaEdit,
  FaTrash,
  FaCheck,
  FaTimes,
} from "react-icons/fa";
import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, {
  ColumnFilter,
} from "../../../../../components/common/AdvancedDataTable";
import { Actions, patchAction } from "../../../../../api/userProfile";
import { fetchContacts } from "../services/contactApi";
import { useNavigate } from "react-router";
import { useDispatch } from "react-redux";
import { showToast } from "../../../../../store/slices/toastSlice";
import ContactDetail from "./ContactDetail";
import { PageRoutes } from "../../../../../routes/Routes";

interface ActionData {
  id: string | number;
  email?: string;
  name_first?: string;
  name_last?: string;
  company?: string;
  role?: string;
  is_active?: boolean;
  is_staff?: boolean;
  [key: string]: any;
}

const ContactList = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const [data, setData] = useState<ActionData[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedActions, setSelectedActions] = useState<ActionData[]>([]);
  const [selectedAction, setSelectedAction] = useState<ActionData | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null
  );

  // Helper to extract translated text
  const getTranslatedText = useCallback(
    (
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
    },
    []
  );

  // Format date
  const formatDate = useCallback(
    (timestamp: number | string | null | undefined): string => {
      if (!timestamp) return "-";

      try {
        const date =
          typeof timestamp === "number"
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
    },
    []
  );

  // Extract unique values for filters
  const filterOptions = useMemo(() => {
    const id = new Set<string | number>();
    const email = new Set<string>();
    const name_first = new Set<string>();
    const name_last = new Set<string>();
    const company = new Set<string>();
    const role = new Set<string>();
    const is_active = new Set<string>();
    const is_staff = new Set<string>();

    data.forEach((item) => {
      if (item.id) id.add(item.id);
      if (item.email) email.add(item.email);
      if (item.name_first) name_first.add(item.name_first);
      if (item.name_last) name_last.add(item.name_last);
      if (item.company) company.add(item.company);
      if (item.role) role.add(item.role);

      // Yes/No version
      is_active.add(item.is_active ? "Yes" : "No");
      is_staff.add(item.is_staff ? "Yes" : "No");
    });

    const toOptions = (set: Set<any>) =>
      Array.from(set).map((value) => ({
        value,
        label: String(value),
      }));

    return {
      id: toOptions(id),
      email: toOptions(email),
      name_first: toOptions(name_first),
      name_last: toOptions(name_last),
      company: toOptions(company),
      role: toOptions(role),
      is_active: toOptions(is_active),
      is_staff: toOptions(is_staff),
    };
  }, [data]);

  // const filterOptions = useMemo(() => {
  //   const id = new Set<string | number>();
  //   const email = new Set<string>();
  //   const name_first = new Set<string>();
  //   const name_last = new Set<string>();
  //   const company = new Set<string>();
  //   const role = new Set<string>();
  //   const is_active = new Set<string>();
  //   const is_staff = new Set<string>();
  //   data.forEach((action) => {
  //     if (action.id) id.add(action.id);
  //     if (action.email) email.add(action.email);
  //     if (action.name_first) name_first.add(action.name_first);
  //     if (action.name_last) name_last.add(action.name_last);
  //     if (action.company) company.add(action.company);
  //     if (action.role) role.add(action.role);
  //     is_active.add(action.is_active ? "Yes" : "No");
  //     is_staff.add(action.is_staff ? "Yes" : "No");
  //   });

  //   return {
  //     id: Array.from(id).map((s) => ({ value: s, label: s })),
  //     email: Array.from(email).map((s) => ({ value: s, label: s })),
  //     name_first: Array.from(name_first).map((p) => ({ value: p, label: p })),
  //     name_last: Array.from(name_last).map((c) => ({ value: c, label: c })),
  //     company: Array.from(company).map((c) => ({ value: c, label: c })),
  //     role: Array.from(role).map((c) => ({ value: c, label: c })),
  //     is_active: toOptions(is_active),
  //     is_staff: toOptions(is_staff),
  //   };
  // }, [data]);

  // Fetch actions
  const fetchActions = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetchContacts();

      if (response) {
        const apiData = Array.isArray(response?.data?.results)
          ? response.data.results
          : [];

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
          descriptionText: getTranslatedText(
            action.description,
            action.languages
          ),
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
        width: "5%",
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
        name: "email",
        selector: (row: ActionData) => row.email || "-",
        sortable: true,
        wrap: true,
        width: "15%",
        cell: (row: ActionData) => row.email || "-",
      },
      {
        name: "name_first",
        selector: (row: ActionData) => row.name_first || "-",
        sortable: true,
        width: "13%",
        cell: (row: ActionData) => row.name_first || "-",
      },
      {
        name: "name_last",
        selector: (row: ActionData) => row.name_last || "-",
        sortable: true,
        width: "13%",
        cell: (row: ActionData) => row.name_last || "-",
      },
      {
        name: "company",
        selector: (row: ActionData) => row.company || "-",
        sortable: true,
        width: "15%",
        cell: (row: ActionData) => row.company || "-",
      },
      {
        name: "role",
        selector: (row: ActionData) => row.role || "-",
        sortable: true,
        width: "10%",
        cell: (row: ActionData) => row.role || "-",
      },
      {
        name: "is_active",
        selector: (row: ActionData) => (row.is_active ? "Yes" : "No"),
        sortable: true,
        width: "8%",
        cell: (row: ActionData) =>
          row.is_active ? (
            <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
              {"Yes"}
            </span>
          ) : (
            <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-red-500 dark:bg-red-500 dark:text-blue-200">
              {"No"}
            </span>
          ),
      },
      {
        name: "is_staff",
        selector: (row: ActionData) => (row.is_staff ? "Yes" : "No"),
        sortable: true,
        width: "8%",
        cell: (row: ActionData) =>
          row.is_staff ? (
            <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
              {"Yes"}
            </span>
          ) : (
            <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-red-500 dark:bg-red-500 dark:text-blue-200">
              {"No"}
            </span>
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
        key: "email",
        label: "email",
        type: "select",
        options: filterOptions.email,
      },
      {
        key: "name_first",
        label: "name_first",
        type: "select",
        options: filterOptions.name_first,
      },
      {
        key: "name_last",
        label: "name_last",
        type: "select",
        options: filterOptions.name_last,
      },
      {
        key: "company",
        label: "company",
        type: "select",
        options: filterOptions.company,
      },
      {
        key: "role",
        label: "role",
        type: "select",
        options: filterOptions.role,
      },
      {
        key: "is_active",
        label: "is_active",
        type: "select",
        options: filterOptions.is_active,
      },
      {
        key: "is_staff",
        label: "is_staff",
        type: "select",
        options: filterOptions.is_staff,
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
          type: "error",
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
    navigate(PageRoutes.coreContactList.replace("/:id?", ""));
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
      <PageBreadcrumb pageTitle="Contact List" />
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
            <ContactDetail
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

export default ContactList;
