import ComponentCard from "../../../../../components/common/ComponentCard";
import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";

export default function InventoryAdjustmentList() {
  return (
    <div>
      <PageBreadcrumb pageTitle="Inventory Adjustments" />
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
