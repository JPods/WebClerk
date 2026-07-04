/**
 * widgetTypes — canonical widget type schema for DataBrowser.
 *
 * Single source of truth for all field widget types.
 * Used by: BehaviorField rendering, getDefaultFieldSpec(), seed_field_access.py validation.
 *
 * Each type defines its display defaults, sizing behavior, and capabilities.
 * Adding a new widget type = one entry here + one render case in BehaviorField.tsx.
 */

export type WidgetTypeDef = {
  defaultWidth: number;
  sizing: 'fixed' | 'grow';
  sortable: boolean;
  editable: boolean;
  filterType: 'text' | 'number' | 'date' | 'boolean' | 'select' | 'lookup' | 'none';
  actionable?: boolean;    // true = label is clickable (mailto, tel, map link)
  labelColor?: 'accent' | 'green' | 'purple' | 'dim' | 'muted';
  span2?: boolean;         // true = spans full width in detail view
};

export const WIDGET_TYPES: Record<string, WidgetTypeDef> = {
  text: {
    defaultWidth: 150,
    sizing: 'grow',
    sortable: true,
    editable: true,
    filterType: 'text',
    labelColor: 'muted',
  },
  number: {
    defaultWidth: 80,
    sizing: 'fixed',
    sortable: true,
    editable: true,
    filterType: 'number',
    labelColor: 'muted',
  },
  currency: {
    defaultWidth: 100,
    sizing: 'fixed',
    sortable: true,
    editable: true,
    filterType: 'number',
    labelColor: 'muted',
  },
  email: {
    defaultWidth: 180,
    sizing: 'grow',
    sortable: true,
    editable: true,
    filterType: 'text',
    actionable: true,
    labelColor: 'accent',
  },
  phone: {
    defaultWidth: 120,
    sizing: 'fixed',
    sortable: true,
    editable: true,
    filterType: 'text',
    actionable: true,
    labelColor: 'accent',
  },
  url: {
    defaultWidth: 180,
    sizing: 'grow',
    sortable: true,
    editable: true,
    filterType: 'text',
    actionable: true,
    labelColor: 'accent',
  },
  address: {
    defaultWidth: 220,
    sizing: 'grow',
    sortable: true,
    editable: true,
    filterType: 'text',
    actionable: true,
    labelColor: 'accent',
  },
  geo: {
    defaultWidth: 100,
    sizing: 'fixed',
    sortable: false,
    editable: true,
    filterType: 'none',
    actionable: true,
    labelColor: 'accent',
  },
  lookup: {
    defaultWidth: 140,
    sizing: 'grow',
    sortable: true,
    editable: true,
    filterType: 'lookup',
    labelColor: 'purple',
  },
  select: {
    defaultWidth: 100,
    sizing: 'fixed',
    sortable: true,
    editable: true,
    filterType: 'select',
    labelColor: 'green',
  },
  boolean: {
    defaultWidth: 50,
    sizing: 'fixed',
    sortable: true,
    editable: true,
    filterType: 'boolean',
    labelColor: 'muted',
  },
  date: {
    defaultWidth: 100,
    sizing: 'fixed',
    sortable: true,
    editable: true,
    filterType: 'date',
    labelColor: 'muted',
  },
  timestamp: {
    defaultWidth: 100,
    sizing: 'fixed',
    sortable: true,
    editable: false,
    filterType: 'date',
    labelColor: 'dim',
  },
  json: {
    defaultWidth: 60,
    sizing: 'fixed',
    sortable: false,
    editable: false,
    filterType: 'none',
    labelColor: 'dim',
    span2: true,
  },
  textarea: {
    defaultWidth: 200,
    sizing: 'grow',
    sortable: false,
    editable: true,
    filterType: 'text',
    labelColor: 'muted',
    span2: true,
  },
  readonly: {
    defaultWidth: 100,
    sizing: 'fixed',
    sortable: true,
    editable: false,
    filterType: 'text',
    labelColor: 'dim',
  },
  masked: {
    defaultWidth: 100,
    sizing: 'fixed',
    sortable: false,
    editable: false,
    filterType: 'none',
    labelColor: 'dim',
  },
} as const;

/** All valid widget type names */
export type WidgetTypeName = keyof typeof WIDGET_TYPES;

/** Get widget type definition with fallback to 'text' */
export function getWidgetType(typeName: string): WidgetTypeDef {
  return WIDGET_TYPES[typeName] || WIDGET_TYPES.text;
}

/** Check if a type name is valid */
export function isValidWidgetType(typeName: string): typeName is WidgetTypeName {
  return typeName in WIDGET_TYPES;
}
