import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import ComponentCard from "../../components/common/ComponentCard";

import DataTable, { TableColumn } from 'react-data-table-component';
import { useState } from "react";

export default function ContactList() {

const [globalFilter, setGlobalFilter] = useState('');
interface User {
  id: number;
  email: string;
  role: string[]; // ArrayField
  role_default?: string;
  company?: string;
  name_first: string;
  name_last: string;
  name_middle?: string;
  rank?: string;
  date_joined: string;
}


const columns: TableColumn<User>[] = [
  {
    name: 'Name',
    selector: row => row.name_first,
    sortable: true,
  },
  {
    name: 'Email',
    selector: row => row.email,
    sortable: true,
  },
];

const userColumns: TableColumn<User>[] = [
  { name: 'First Name', selector: row => row.name_first, sortable: true },
  { name: 'Last Name', selector: row => row.name_last, sortable: true },
  { name: 'Email', selector: row => row.email, sortable: true },
  { name: 'Company', selector: row => row.company || '-', sortable: true },
  { name: 'Role(s)', selector: row => row.role.join(', '), sortable: false },
  { name: 'Default Role', selector: row => row.role_default || '-', sortable: true },
  { name: 'Date Joined', selector: row => row.date_joined, sortable: true },
];
const data: User[] = [
  {
    id: 1,
    email: 'admin@example.com',
    role: ['SUPER', 'ADMIN'],
    role_default: 'ADMIN',
    company: 'Webclerk Ltd.',
    name_first: 'Riju',
    name_last: 'Karar',
    name_middle: '',
    rank: 'Top',
    date_joined: '2024-12-15T09:30:00Z',
  },
  {
    id: 2,
    email: 'vendor1@example.com',
    role: ['VENDOR'],
    role_default: 'VENDOR',
    company: 'VendorCorp Pvt. Ltd.',
    name_first: 'Anita',
    name_last: 'Sharma',
    rank: 'Mid',
    date_joined: '2024-10-01T10:00:00Z',
 },
  {
    id: 3,
    email: 'customer99@example.com',
    role: ['CUSTOMER', 'USER'],
    role_default: 'CUSTOMER',   
    name_first: 'Rahul',
    name_last: 'Verma',
    name_middle: '',   
    date_joined: '2025-01-15T08:00:00Z',
  }
];

  return (
    <>
      <PageBreadcrumb pageTitle="Contact List" />
      <div className="space-y-6">
        <ComponentCard>              
                {/* <input
                    type="text"
                    className="border p-2 w-full max-w-md"
                    placeholder="Global search..."
                    value={globalFilter}
                    onChange={e => setGlobalFilter(e.target.value)}
                /> */}
                <div className="overflow-x-auto">
                    <DataTable
                    // title="User List"
                    columns={userColumns}
                    data={data}
                    pagination
                    />  
                </div>        
        </ComponentCard>       
      </div>
    </>
  );
}
