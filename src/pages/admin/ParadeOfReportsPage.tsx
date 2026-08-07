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

const darkTheme = {
  bg: '#1e1e1e', surface: '#252526', surfaceAlt: '#2d2d2d',
  border: '#3c3c3c', borderLight: '#4d4d4d',
  text: '#d4d4d4', textMuted: '#888', textDim: '#666',
  accent: '#9cdcfe', accentGreen: '#4ec98c', accentGold: '#e8c870',
  accentRed: '#e05252',
};

const ParadeOfReportsPage: React.FC = () => (
  <ParadeOfReports
    open={true}
    onClose={() => window.history.back()}
    theme={darkTheme}
    fontSize={13}
  />
);

export default ParadeOfReportsPage;
