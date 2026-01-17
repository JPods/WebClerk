import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, {
  ColumnFilter,
} from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { fetchPhones, deletePhone } from "../services/phoneApi";
import { getRecord } from "../../../../../api/wcapi";
import { FaEye, FaEdit, FaTrash, FaPlus } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import PhoneDetail from "./PhoneDetail";
import { dynamicData } from "../../../../../model/dynamicData";
import PhoneListMob from "./PhoneListMob";
export default function PhoneList() {
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedPhones, setSelectedPhones] = useState<dynamicData[]>([]);
  const [selectedPhone, setSelectedPhone] = useState<dynamicData | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null
  );
  const [loading, setLoading] = useState(false);

          <ComponentCard>
            <div className="w-full overflow-x-auto rounded-md cus-bg-purple-light dark:bg-[#1e2636] h-[calc(100vh-265px)]">
        dispatch(
          showToast({
            message: "Failed to delete phone",
                    dataProp={data}
          })
        );
      }
    }
  };

                  data={data}
                  columns={userColumns}
                  title="Phones"
                  storageKey="communications.phone.list"
                  loading={loading}
                  filters={filters}
                  enableExport={true}
                  enableSelection={true}
                  onSelectionChange={setSelectedPhones}
                  exportFileName="phones_export"
                  searchPlaceholder="Search phones..."
                  noDataMessage="No phones found"
                  customActions={
                    <div className="flex gap-2">
                      {selectedPhones.length > 0 && (
                        <button
                          onClick={handleBulkDelete}
                          className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                        >
                          <FaTrash className="w-4 h-4" />
                          Delete ({selectedPhones.length})
                        </button>
                      )}
                      <button
                        onClick={handleAdd}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        <FaPlus className="w-4 h-4" />
                        New Phone
                      </button>
                    </div>
                  }
                  onRowClicked={handleEdit}
                  rowClickMode="onlyIdAndActions"
                  rowClickAllowedColumnNames={["id", "action", "actions"]}
                  rowKeyField="id"
    return [
      {
        key: "opt_out",
        label: "Opt Out",
        type: "select",
        options: [
          { value: "true", label: "Yes" },
          { value: "false", label: "No" },
        ],
      },
      ...(countryCodes.length
        ? [
            {
              key: "country_code",
              label: "Country Code",
              type: "select",
              options: countryCodes,
            } as ColumnFilter,
          ]
        : []),
    ];
  }, [data]);

  const handleBulkDelete = async () => {
    if (!selectedPhones.length) return;
    if (!window.confirm(`Delete ${selectedPhones.length} phones?`)) return;

    try {
      await Promise.all(selectedPhones.map((row) => deletePhone(row.id)));
      dispatch(
        showToast({
          message: "Phones deleted successfully",
          type: "success",
        })
      );
      setSelectedPhones([]);
      getPhoneData();
    } catch (error) {
      dispatch(
        showToast({
          message: "Failed to delete phones",
          type: "error",
        })
      );
    }
  };
  /* ---------------- Columns ---------------- */
  const userColumns: TableColumn<dynamicData>[] = useMemo(
    () => [
      { name: "id", selector: (row) => row.id, sortable: true, width: "5%" },
      {
        name: "number",
        selector: (row) => row.number || "--",
        cell: (row) => (row.number ? row.number.toString() : "--"),
        sortable: true,
        width: "25%",
      },
      {
        name: "name",
        selector: (row) => row.name || "--",
        cell: (row) => (row.name ? row.name.toString() : "--"),
        sortable: true,
        width: "25%",
      },

      {
        name: "country_code",
        selector: (row) => row.country_code || "--",
        cell: (row) =>
          row.country_code ? row.country_code.toString() : "--",
        sortable: true,
        width: "15%",
      },

      {
        name: "opt_out",
        selector: (row) => (row.opt_out ? "Yes" : "No"), // Plain string for filtering
        cell: (row) => (row.opt_out ? "Yes" : "No"),
        sortable: true,
        width: "15%",
      },

      {
        name: "action",
        cell: (row) => (
          <div className="flex gap-3">
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
    ],
    [handleDelete, handleEdit, handleView]
  );

  return (
    <>
      <PageBreadcrumb pageTitle="Phone List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="w-full overflow-x-auto rounded-md cus-bg-purple-light dark:bg-[#1e2636] h-[calc(100vh-265px)]">
              {formMode ? (
                <div className="flex flex-col">
                  <PhoneListMob
                    dataProp={data}
                    handleView={handleView}
                    handleEdit={handleEdit}
                  />
                </div>
              ) : (
                <AdvancedDataTable
                  data={data}
                  columns={userColumns}
                  title="Phones"
                  storageKey="communications.phone.list"
                  loading={loading}
                  filters={filters}
                  enableExport={true}
                  enableSelection={true}
                  onSelectionChange={setSelectedPhones}
                  exportFileName="phones_export"
                  searchPlaceholder="Search phones..."
                  noDataMessage="No phones found"
                  customActions={
                    <div className="flex gap-2">
                      {selectedPhones.length > 0 && (
                        <button
                          onClick={handleBulkDelete}
                          className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                        >
                          <FaTrash className="w-4 h-4" />
                          Delete ({selectedPhones.length})
                        </button>
                      )}
                      <button
                        onClick={handleAdd}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        <FaPlus className="w-4 h-4" />
                        New Phone
                      </button>
                    </div>
                  }
                  onRowClicked={handleEdit}
                  rowClickMode="onlyIdAndActions"
                  rowClickAllowedColumnNames={["id", "action", "actions"]}
                  rowKeyField="id"
                />
              )}
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <PhoneDetail
              inline
              modeProp={formMode}
              dataProp={selectedPhone}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
