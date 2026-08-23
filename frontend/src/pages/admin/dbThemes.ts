/* LastChecked: 2026-08-14 | WhereUsed: DataBrowser + child components | WhoCreated: Bill+Claude */

// ---------------------------------------------------------------------------
// Theme tokens — kept for passing to child components (DataGrid, BehaviorField)
// that still use inline styles. DataBrowser itself uses CSS custom properties.
// ---------------------------------------------------------------------------

export const themes = {
  dark: {
    bg: '#1e1e1e', surface: '#252526', surfaceAlt: '#2d2d2d',
    border: '#3c3c3c', borderLight: '#4d4d4d',
    text: '#d4d4d4', textMuted: '#888', textDim: '#666',
    accent: '#9cdcfe', accentGreen: '#4ec98c', accentGold: '#e8c870',
    accentRed: '#e05252', accentPurple: '#c8a8e8',
    btnBg: '#2d2d2d', btnPrimary: '#0e639c', btnSave: '#1a6b2e',
    btnDanger: '#6b1a1a', btnDangerBorder: '#964040', btnSaveBorder: '#2f8f45',
    inputBg: '#2a2a2a', inputBorder: '#555',
    rowHover: '#2a2d2e', rowActive: '#094771', rowChecked: '#3a3a1a',
    resizeHandle: '#4a9eff',
  },
  light: {
    bg: '#f8f9fa', surface: '#ffffff', surfaceAlt: '#f1f3f5',
    border: '#dee2e6', borderLight: '#e9ecef',
    text: '#212529', textMuted: '#6c757d', textDim: '#adb5bd',
    accent: '#0d6efd', accentGreen: '#198754', accentGold: '#fd7e14',
    accentRed: '#dc3545', accentPurple: '#6f42c1',
    btnBg: '#ffffff', btnPrimary: '#0d6efd', btnSave: '#198754',
    btnDanger: '#dc3545', btnDangerBorder: '#dc3545', btnSaveBorder: '#157347',
    inputBg: '#ffffff', inputBorder: '#ced4da',
    rowHover: '#f1f3f5', rowActive: '#cfe2ff', rowChecked: '#fff3cd',
    resizeHandle: '#0d6efd',
  },
};

export type ThemeKey = keyof typeof themes;
