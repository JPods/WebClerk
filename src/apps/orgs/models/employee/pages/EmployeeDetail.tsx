/**
 * EmployeeDetail - Employee detail/edit component using OrgDetail base
 * Admin-only access, uses shared org infrastructure
 */
import React from 'react';
import OrgDetail from '../../../components/OrgDetail';
import type { Organization } from '../../../types/orgTypes';
import { AdminGuard } from '@/components/auth/AdminGuard';

// Props interface for inline usage in OrgList
interface EmployeeDetailProps {
  org: Organization;
  mode: 'view' | 'edit' | 'add';
  onClose: () => void;
  onSaved: () => void;
}

// Inline detail component (used by OrgList)
const EmployeeDetail: React.FC<EmployeeDetailProps> = ({ org, mode, onClose, onSaved }) => {
  return (
    <OrgDetail
      orgType="employee"
      title="Employee"
      listPath="/org/employees"
      org={org}
      mode={mode}
      onClose={onClose}
      onSaved={onSaved}
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
        listPath="/org/employees"
      />
    </AdminGuard>
  );
}

export default EmployeeDetail;
