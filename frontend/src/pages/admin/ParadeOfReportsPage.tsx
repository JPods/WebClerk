/**
 * ParadeOfReportsPage — standalone page for the report parade.
 *
 * Launched from DataBrowser when user opens the "Parade of Reports" Report record,
 * or directly via /parade URL.
 *
 * LastChecked: 2026-08-07 | WhereUsed: Router | WhoCreated: Bill+Claude
 */
import React from 'react';
import { ParadeOfReports } from '@/components/common/ParadeOfReports';

const ParadeOfReportsPage: React.FC = () => (
  <ParadeOfReports
    open={true}
    onClose={() => window.history.back()}
    fontSize={13}
  />
);

export default ParadeOfReportsPage;
