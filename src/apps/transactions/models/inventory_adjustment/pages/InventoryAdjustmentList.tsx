import ComponentCard from "../../../../../components/common/ComponentCard";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function InventoryAdjustmentList() {
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
    <div>
      <ButtonToolbar
        pageTitle="Inventory Adjustments"
        title="Inventory Adjustments"
        modelKey="inventory_adjustments"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getData}
        columns={columns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="inventory_adjustments-list"
        filterValues={filterValues}
        onFilterValuesChange={setFilterValues}
        filtersOpen={filtersOpen}
        onFiltersOpenChange={setFiltersOpen}
      />
<ComponentCard title="Inventory Adjustments">
        <div className="p-6 text-center text-gray-500 dark:text-gray-400">
          <h2 className="text-xl font-semibold mb-4">Inventory Adjustments</h2>
          <p className="mb-4">
            This page will list inventory adjustments for manual quantity corrections,
            cycle counts, and other inventory modifications.
          </p>
          <p className="text-sm">
            Coming soon - API integration pending.
          </p>
        </div>
      </ComponentCard>
    </div>
  );
}
