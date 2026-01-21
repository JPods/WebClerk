import { ReactNode } from "react";

export type AdminRecordId = string | number;

export type AdminFieldKind =
  | "text"
  | "number"
  | "integer"
  | "currency"
  | "boolean"
  | "date"
  | "datetime"
  | "tag"
  | "badge"
  | "json"
  | "relation"
  | "email"
  | "url"
  | "status";

export type AdminFieldDescriptor = {
  id: string;
  label: string;
  kind?: AdminFieldKind;
  description?: string;
  width?: string;
  minWidth?: string;
  align?: "left" | "center" | "right";
  sortable?: boolean;
  filterable?: boolean;
  searchable?: boolean;
  editable?: boolean;
  readOnly?: boolean;
  required?: boolean;
  hasChoices?: boolean;
  locked?: boolean;
  placeholder?: string;
  format?: (value: unknown, record: AdminRecord) => ReactNode;
  renderListCell?: (value: unknown, record: AdminRecord) => ReactNode;
  renderDetail?: (value: unknown, record: AdminRecord) => ReactNode;
};

export type AdminRecord = Record<string, unknown> & {
  id: AdminRecordId;
  [key: string]: unknown;
};

export type AdminFilterOption = {
  value: string;
  label: string;
  count?: number;
};

type BaseFilterDefinition = {
  id: string;
  label: string;
  helperText?: string;
  defaultValue?: unknown;
};

export type AdminFilterDefinition =
  | (BaseFilterDefinition & {
      type: "text" | "search";
      placeholder?: string;
    })
  | (BaseFilterDefinition & {
      type: "select" | "multi-select";
      options: AdminFilterOption[];
    })
  | (BaseFilterDefinition & {
      type: "boolean";
      trueLabel?: string;
      falseLabel?: string;
    })
  | (BaseFilterDefinition & {
      type: "date" | "datetime";
    })
  | (BaseFilterDefinition & {
      type: "date-range" | "number-range";
    });

export type AdminQuerySortDirection = "asc" | "desc";

export type AdminQuerySort = {
  fieldId: string;
  direction: AdminQuerySortDirection;
};

export type AdminListQuery = {
  page: number;
  pageSize: number;
  search?: string;
  filters?: Record<string, unknown>;
  sort?: AdminQuerySort | null;
};

export type AdminListResult = {
  items: AdminRecord[];
  total: number;
  page: number;
  pageSize: number;
  aggregates?: Record<string, unknown>;
};

export type AdminTableDataSource = {
  list: (query: AdminListQuery) => Promise<AdminListResult>;
  retrieve?: (id: AdminRecordId) => Promise<AdminRecord | null>;
  update?: (id: AdminRecordId, payload: Partial<AdminRecord>) => Promise<AdminRecord>;
  create?: (payload: Partial<AdminRecord>) => Promise<AdminRecord>;
  remove?: (id: AdminRecordId) => Promise<void>;
};

export type AdminDetailSection = {
  id: string;
  label?: string;
  description?: string;
  fieldIds: string[];
};

export type AdminTableDefinition = {
  id: string;
  label: string;
  description?: string;
  icon?: ReactNode;
  primaryKey?: string;
  fields: AdminFieldDescriptor[];
  defaultListFields?: string[];
  defaultDetailFields?: string[];
  detailSections?: AdminDetailSection[];
  filterDefinitions?: AdminFilterDefinition[];
  defaultSort?: AdminQuerySort;
  dataSource: AdminTableDataSource;
  pageSizeOptions?: number[];
  defaultPageSize?: number;
};

export type AdminAppDefinition = {
  id: string;
  label: string;
  description?: string;
  icon?: ReactNode;
  tables: AdminTableDefinition[];
};

export type AdminWorkspaceConfig = {
  apps: AdminAppDefinition[];
  storageKey?: string;
  initialAppId?: string;
  initialTableId?: string;
  defaultPageSize?: number;
  pageSizeOptions?: number[];
};

export type LayoutPreference = {
  order: string[];
  hidden: string[];
};

export type TableLayoutPreferences = {
  list?: LayoutPreference;
  detail?: LayoutPreference;
};

export type LayoutPreferencesMap = Record<string, TableLayoutPreferences>;
