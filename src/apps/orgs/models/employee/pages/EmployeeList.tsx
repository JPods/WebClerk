/**
 * EmployeeList - Employee listing page using OrgList base component
 * Admin-only access, uses shared org infrastructure
 */
import React from 'react';
import { TableColumn } from 'react-data-table-component';
import OrgList from '../../../components/OrgList';
import EmployeeDetail from './EmployeeDetail';
import type { Organization } from '../../../types/orgTypes';
import { AdminGuard } from '@/components/auth/AdminGuard';

// Employee-specific columns (extend base columns)
const employeeColumns: TableColumn<Organization>[] = [
  // Add employee-specific columns here if needed
  // Base OrgList already includes: ID, Name, Status, Active, Contacts, Locations
];

function EmployeeList() {
  return (
    <OrgList
      orgType="employee"
      title="Employees"
      detailPath="/org/employee"
      additionalColumns={employeeColumns}
      showInlineDetail={true}
      DetailComponent={EmployeeDetail}
    />
  );
}

// Export with AdminGuard wrapper for route protection
export default function EmployeeListPage() {
  return (
    <AdminGuard>
      <EmployeeList />
    </AdminGuard>
  );
}
