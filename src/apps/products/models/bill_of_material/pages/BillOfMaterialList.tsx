/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import DataGrid from "@/components/common/DataGrid";
import ComponentCard from "../../../../../components/common/ComponentCard";
import { useEffect, useState, useCallback, useMemo, useRef} from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchBillOfMaterials } from "../services/billOfMaterialApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../../../../context/ThemeContext";
import BillOfMaterialDetail from "./BillOfMaterialDetail";
import ButtonToolbar from "@/components/common/ButtonToolbar";

// Normalizes differing API payload shapes into a flat array of items.
const extractItems = (payload: any): any[] => {
  if (!payload) {
    return [];
  }

  const directCandidates = [
    payload?.data?.items,
    payload?.data?.results,
    payload?.data?.data?.items,
    payload?.data?.data?.results,
    payload?.items,
    payload?.results,
  ];

  for (const candidate of directCandidates) {
    if (Array.isArray(candidate)) {
      return candidate;
    }
  }

  const objectCandidates = [payload?.data?.data, payload?.data, payload];
  for (const obj of objectCandidates) {
    if (obj && typeof obj === "object" && !Array.isArray(obj)) {
      const values = Object.values(obj);
      for (const value of values) {
        if (Array.isArray(value)) {
          return value;
        }
      }
    }
  }

  return [];
};

export default function BillOfMaterialList() {
  const { theme } = useTheme();
  const [data, setData] = useState<any[]>([]);
  const [selectedBillOfMaterial, setSelectedBillOfMaterial] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<any>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const dispatch = useDispatch();

  const getBillOfMaterialData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchBillOfMaterials();
      if (res.status === 200) {
         const items = extractItems(res).map((it:any)=>({
            ...it,
            quantity:{
              on_hand:100,
              on_p:0,
              on_so:0,
              on_po:0,
              on_wo:0,
              on_in:0,
              ...(it.quantity||{})
            }
         }));
         setData(items);
        if (!items.length) {
          dispatch(
            showToast({
              message: "Bill of material response contained no rows",
              type: "info",
            })
          );
        }
      } else {
        dispatch(
          showToast({ message: "Failed to fetch bill of materials", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch bill of materials", error);
      dispatch(showToast({ message: "Failed to fetch bill of materials", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getBillOfMaterialData();
  }, [getBillOfMaterialData]);

  const handleView = (row: any) => {
    setSelectedBillOfMaterial(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedBillOfMaterial(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedBillOfMaterial(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getBillOfMaterialData();
    setFormMode(null);
    setSelectedBillOfMaterial(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedBillOfMaterial(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete bill of material ${row.name}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Bill of material deleted successfully", type: "success" }));
        getBillOfMaterialData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete bill of material", type: "error" }));
      }
    }
  };

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchBillOfMaterials({ search: searchQuery });
      if (res.status === 200) {
        const items = extractItems(res);
        setData(items);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const userColumns: any[] = [
    // {
    //   name: "Alternate Group",
    //   selector: (row) => row.alternate_group || "--",
    //   sortable: true,
    //   width: "10%",
    // },

    { name: "ID", selector: (row: any) => row.id, sortable: true, width: "5%" },
    {
      name: "CHILD ID",
      selector: (row: { child_id: string }) => row.child_id,
      sortable: true,
      width: "8%",
    },
    {
      name: "Cost Snapshot",
      selector: (row: any) => row.cost_snapshot ?? "--",
      sortable: true,
      width: "8%",
    },
    {
      name: "Description",
      selector: (row: any) => row.description || "--",
      sortable: true,
      width: "20%",
    },
    {
      name: "Is Active",
      selector: (row: any) => (row.is_active ? "Yes" : "No"),
      sortable: true,
      width: "6%",
    },
    {
      name: "Is Alternate",
      selector: (row: any) => (row.is_alternate ? "Yes" : "No"),
      sortable: true,
      width: "6%",
    },
    {
      name: "Is Optional",
      selector: (row: any) => (row.is_optional ? "Yes" : "No"),
      sortable: true,
      width: "6%",
    },
    {
      name: "PARENT ID",
      selector: (row: { parent_id: string }) => row.parent_id,
      sortable: true,
      width: "6%",
    },
    {
      name: "Quantity",
      selector: (row: any) => row.quantity?.on_hand ?? "--",
      sortable: true,
      width: "6%",
    },
    {
      name: "Revision",
      selector: (row: any) => row.revision || "--",
      sortable: true,
      width: "6%",
    },
    {
      name: "Scrap Factor",
      selector: (row: any) => row.scrap_factor ?? "--",
      sortable: true,
      width: "7%",
    },
    {
      name: "Sequence",
      selector: (row: any) => row.sequence ?? "--",
      sortable: true,
      width: "6%",
    },
    {
      name: "Action",
      cell: (row: any) => (
        <div className="flex gap-2">
          <button onClick={() => handleView(row)} title="View">
            <FaEye className="text-blue-600 hover:scale-110 transition" />
          </button>
          <button onClick={() => handleEdit(row)} title="Edit">
            <FaEdit className="text-green-600 hover:scale-110 transition" />
          </button>
          <button onClick={() => handleDelete(row)} title="Delete">
            <FaTrash className="text-red-600 hover:scale-110 transition" />
          </button>
        </div>
      ),
      ignoreRowClick: true,
      allowOverflow: true,
      button: true,
    },
  ];

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
    if (columnVisibility.length === 0) return userColumns;
    return userColumns.filter((_: any, index: number) => columnVisibility[index] !== false);
  }, [userColumns, columnVisibility]);
  return (
    <>
      <ButtonToolbar
        pageTitle="Bill of Material List"
        title="Bill of Material"
        modelKey="bill_of_material"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getBillOfMaterialData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={userColumns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="bill_of_material-list"
        filterValues={filterValues}
        onFilterValuesChange={setFilterValues}
        filtersOpen={filtersOpen}
        onFiltersOpenChange={setFiltersOpen}
      />
<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Bill of Material
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <DataGrid
              ref={tableRef}
                columns={userColumns.map((col) => ({
                  ...col,
                  name: typeof col.name === "string" ? col.name.toUpperCase() : col.name,
                }))}
                data={filteredData}
                storageKey="bill_of_material_list"
                onRowActivate={handleEdit}
                loading={loading}
                enableDatabaseSearch={true}
                searchDatabase={searchDatabase}
                onSearchModeChange={setSearchDatabase}
                onDatabaseSearch={handleDatabaseSearch}
              
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              hideHeader={true}/>
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <BillOfMaterialDetail
              inline
              modeProp={formMode}
              dataProp={selectedBillOfMaterial}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
