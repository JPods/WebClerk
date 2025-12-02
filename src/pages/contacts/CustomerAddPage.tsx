import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import CustomerForm from "../../components/CustomerForm";

export default function CustomerAddPage() {
  return (
    <>
      <PageBreadcrumb pageTitle="Add New Customer" />
      <CustomerForm
        modeProp="add"
        onSaved={() => {
          // Navigate back or to list
          console.log("Customer added");
        }}
      />
    </>
  );
}