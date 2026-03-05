/**
 * EmployeeDetail - Employee detail/edit component using OrgDetail base
 * Admin-only access, uses shared org infrastructure
 */
import React from 'react';
import OrgDetail from '../../../components/OrgDetail';
import { AdminGuard } from '@/components/auth/AdminGuard';
import { PageRoutes } from '@/routes/Routes';
import type { EmployeeAddProps } from '../types/employeeType';
import { withDevIdentifier } from '@/components/common/DevIdentifier';

// Inline detail component (used by OrgList)
const EmployeeDetail: React.FC<EmployeeAddProps & { onClose?: () => void }> = ({
  modeProp,
  dataProp,
  onSaved,
  onCancelInline,
  onClose,
}) => {
  return (
    <OrgDetail
      orgType="employee"
      title="Employee"
      listPath={PageRoutes.employeeList}
      org={dataProp}
      mode={modeProp}
      onClose={onCancelInline ?? onClose}
      onSaved={onSaved}
      additionalTabs={[]}
    />
  );
};

// Standalone page component (for direct navigation)
export function EmployeeDetailPage() {
  return (
    <AdminGuard>
      <OrgDetail
        orgType="employee"
        title="Employee"
        listPath={PageRoutes.employeeList}
      />
    </AdminGuard>
  );
}

export default withDevIdentifier(EmployeeDetail, 'EmployeeDetail');