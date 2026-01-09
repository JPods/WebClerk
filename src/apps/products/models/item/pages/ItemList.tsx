import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
import { useCallback, useEffect, useMemo, useState } from "react";
import { FaEdit, FaEye, FaPlus, FaTrash } from "react-icons/fa";
import { useDispatch } from "react-redux";
import { deleteAction } from "../../../../../api/userProfile";
import { showToast } from "../../../../../store/slices/toastSlice";
import { fetchItems } from "../services/itemApi";
import { useTheme } from "../../../../../context/ThemeContext";
import ItemDetail from "./ItemDetail";

type ItemListMode = "add" | "edit" | "view" | null;

const valueFrom = (row: any, keys: string[], fallback: any = undefined) => {
  for (const key of keys) {
    const value = row?.[key];
    if (value !== undefined && value !== null && value !== "") {
      return value;
    }
  }
  return fallback;
};

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

export default function ItemList() {
  const { theme } = useTheme();
  const dispatch = useDispatch();

  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [formMode, setFormMode] = useState<ItemListMode>(null);
  const [selectedItem, setSelectedItem] = useState<any | null>(null);

  const getItemId = useCallback((row: any) => {
    return (
      valueFrom(row, ["id", "item_id", "uuid", "item_number", "sku"], null) ?? null
    );
  }, []);

  const getItemLabel = useCallback((row: any) => {
    return (
      valueFrom(row, ["name", "item_name", "title", "sku", "item_number"], "Item") ||
      "Item"
    );
  }, []);

  const getItems = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchItems();
      if (res.status === 200) {
        const normalized = extractItems(res);
        setItems(normalized);
        if (!normalized.length) {
          dispatch(
            showToast({
              message: "Item response contained no rows",
              type: "warning",
            })
          );
        }
      } else {
        dispatch(showToast({ message: "Failed to fetch items", type: "error" }));
      }
    } catch (error) {
      console.error("Failed to fetch items", error);
      dispatch(showToast({ message: "Failed to fetch items", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getItems();
  }, [getItems]);

  const handleView = useCallback((row: any) => {
    setSelectedItem(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedItem(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedItem(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getItems();
    setFormMode(null);
    setSelectedItem(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedItem(null);
  };

  const handleDelete = useCallback(
    async (row: any) => {
      const id = getItemId(row);
      if (!id) {
        dispatch(showToast({ message: "Item id missing", type: "error" }));
        return;
      }

      const label = getItemLabel(row);
      if (!window.confirm(`Delete item ${label}?`)) {
        return;
      }

      try {
        await deleteAction(id);
        dispatch(showToast({ message: "Item deleted successfully", type: "success" }));
        getItems();
      } catch (error) {
        console.error("Failed to delete item", error);
        dispatch(showToast({ message: "Failed to delete item", type: "error" }));
      }
    },
    [dispatch, getItemId, getItemLabel, getItems]
  );

  const columns: TableColumn<any>[] = useMemo(() => {
    const idSelector = (row: any) =>
      valueFrom(row, ["id", "item_id", "item_number", "sku", "uuid"], "--");
    const nameSelector = (row: any) =>
      valueFrom(row, ["name", "item_name", "title", "description"], "--");
    const skuSelector = (row: any) =>
      valueFrom(row, ["sku", "item_code", "item_number", "external_id"], "--");
    const categorySelector = (row: any) =>
      valueFrom(row, ["category", "category_name", "segment", "group"], "--");
    const priceSelector = (row: any) => {
      const raw = valueFrom(row, ["price", "unit_price", "list_price", "cost"], 0);
      const numeric = Number(raw);
      return Number.isFinite(numeric) ? numeric : 0;
    };
    const descriptionSelector = (row: any) =>
      valueFrom(
        row,
        ["description", "long_description", "short_description", "change_reason"],
        "--"
      );

    return [
      { name: "ID", selector: idSelector, sortable: true, width: "10%" },
      {
        name: "NAME",
        selector: nameSelector,
        sortable: true,
        wrap: true,
        width: "20%",
      },
      {
        name: "SKU",
        selector: skuSelector,
        sortable: true,
        wrap: true,
        width: "15%",
      },
      {
        name: "CATEGORY",
        selector: categorySelector,
        sortable: true,
        wrap: true,
        width: "15%",
      },
      {
        name: "PRICE",
        selector: priceSelector,
        sortable: true,
        width: "10%",
        cell: (row) => {
          const price = priceSelector(row);
          return (
            <span className="font-medium text-green-600 dark:text-green-400">
              ${price.toFixed(2)}
            </span>
          );
        },
      },
      {
        name: "DESCRIPTION",
        selector: descriptionSelector,
        sortable: false,
        wrap: true,
        width: "20%",
      },
      {
        name: "ACTION",
        cell: (row) => (
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
        width: "10%",
      },
    ];
  }, [handleDelete, handleEdit, handleView]);

  return (
    <>
      <PageBreadcrumb pageTitle="Item List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Item
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <DataTable
                columns={columns}
                data={items}
                pagination
                theme={theme === "dark" ? "tailwindDark" : "default"}
                highlightOnHover
                pointerOnHover
                progressPending={loading}
                progressComponent={<div className="p-8 text-center">Loading items...</div>}
                onRowClicked={(row) => handleView(row)}
                noDataComponent={<div className="p-8">There are no items to display.</div>}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <ItemDetail
              inline
              modeProp={formMode}
              dataProp={selectedItem}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}