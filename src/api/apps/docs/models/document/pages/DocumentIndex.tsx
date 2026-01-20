import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../../components/common/ComponentCard";

export default function DocumentIndex() {
  return (
    <>
      <PageBreadcrumb pageTitle="Documentation" />
      <ComponentCard>
        <div className="p-6 text-center">
          <h2 className="text-2xl font-semibold text-gray-800 dark:text-white mb-4">
            Documentation Center
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Documentation functionality will be implemented here.
          </p>
        </div>
      </ComponentCard>
    </>
  );
}