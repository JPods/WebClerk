import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import CustomerDetail from "./CustomerDisplay";

export default function CustomerAddPage() {
  return (
    <>
      <PageBreadcrumb pageTitle="Add Customer" />
      <CustomerDetail modeProp="add" hideBreadcrumb />
    </>
  );
}
