import OrgEntityList from "@/apps/orgs/components/OrgEntityList";
import { fetchVendors, deleteVendor } from "../services/vendorApi";
import VendorDetail from "./VendorDetail";

const columns = [
  { id: "id", name: "ID", selector: (row: any) => row.id, sortable: true, width: "80px" },
  { id: "display_name", name: "Display Name", selector: (row: any) => row.display_name || "--", sortable: true, width: "25%" },
  { id: "org_type", name: "Org Type", selector: (row: any) => row.org_type || "--", sortable: true, width: "12%" },
  { id: "status", name: "Status", selector: (row: any) => row.status || "--", sortable: true, width: "15%" },
  { id: "is_active", name: "Active", selector: (row: any) => (row.is_active ? "yes" : "no"), sortable: true, width: "10%" },
  { id: "version", name: "Version", selector: (row: any) => row.version || "--", sortable: true, width: "10%" },
];

export default function VendorList() {
  return (
    <OrgEntityList
      modelKey="vendor"
      title="Vendors"
      fetchFn={fetchVendors}
      deleteFn={deleteVendor}
      columns={columns}
      storageKey="vendor-list"
      exportFileName="vendors_export"
      displayComponent={VendorDetail}
    />
  );
}
