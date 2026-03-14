/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import type {
  AdminAppDefinition,
  AdminFieldDescriptor,
  AdminListQuery,
  AdminRecord,
  AdminRecordId,
  AdminTableDataSource,
  AdminTableDefinition,
} from "./types";

type StaticDataSourceOptions = {
  searchableFields?: string[];
  filterableFields?: string[];
};

type InMemoryDataset = {
  records: AdminRecord[];
  descriptor: {
    primaryKey: string;
    searchable: Set<string>;
    filterable: Set<string>;
  };
};

const applySearchFilter = (records: AdminRecord[], query: AdminListQuery, dataset: InMemoryDataset): AdminRecord[] => {
  if (!query.search?.trim()) {
    return records;
  }
  const searchNeedle = query.search.trim().toLowerCase();
  const searchableFields = dataset.descriptor.searchable;
  return records.filter((record) => {
    for (const fieldId of searchableFields) {
      const rawValue = record[fieldId];
      if (rawValue === undefined || rawValue === null) {
        continue;
      }
      if (Array.isArray(rawValue)) {
        if (rawValue.some((entry) => String(entry).toLowerCase().includes(searchNeedle))) {
          return true;
        }
        continue;
      }
      const stringValue = String(rawValue).toLowerCase();
      if (stringValue.includes(searchNeedle)) {
        return true;
      }
    }
    return false;
  });
};

const applyFieldFilters = (records: AdminRecord[], filters: Record<string, unknown> = {}): AdminRecord[] => {
  const filterEntries = Object.entries(filters);
  if (!filterEntries.length) {
    return records;
  }
  return records.filter((record) =>
    filterEntries.every(([fieldId, filterValue]) => {
      if (filterValue === undefined || filterValue === null || filterValue === "") {
        return true;
      }
      const value = record[fieldId];
      if (Array.isArray(filterValue)) {
        if (!Array.isArray(value)) {
          return false;
        }
        return filterValue.every((needle) => value.includes(needle));
      }
      if (typeof filterValue === "object" && filterValue !== null) {
        const maybeRange = filterValue as { from?: string | number; to?: string | number };
        if (typeof value === "number") {
          const meetsFrom = maybeRange.from !== undefined ? value >= Number(maybeRange.from) : true;
          const meetsTo = maybeRange.to !== undefined ? value <= Number(maybeRange.to) : true;
          return meetsFrom && meetsTo;
        }
        const raw = value ? new Date(String(value)).getTime() : NaN;
        if (!Number.isNaN(raw)) {
          const fromTime = maybeRange.from ? new Date(String(maybeRange.from)).getTime() : NaN;
          const toTime = maybeRange.to ? new Date(String(maybeRange.to)).getTime() : NaN;
          const meetsFrom = Number.isNaN(fromTime) ? true : raw >= fromTime;
          const meetsTo = Number.isNaN(toTime) ? true : raw <= toTime;
          return meetsFrom && meetsTo;
        }
        return String(value) === String(filterValue);
      }
      if (typeof filterValue === "boolean") {
        return Boolean(value) === filterValue;
      }
      return String(value).toLowerCase().includes(String(filterValue).toLowerCase());
    })
  );
};

const applySorting = (records: AdminRecord[], sortField?: string, direction: "asc" | "desc" = "asc"): AdminRecord[] => {
  if (!sortField) {
    return records;
  }
  return [...records].sort((a, b) => {
    const aValue = a[sortField];
    const bValue = b[sortField];
    if (aValue === bValue) {
      return 0;
    }
    if (aValue === undefined || aValue === null) {
      return direction === "asc" ? -1 : 1;
    }
    if (bValue === undefined || bValue === null) {
      return direction === "asc" ? 1 : -1;
    }
    if (typeof aValue === "number" && typeof bValue === "number") {
      return direction === "asc" ? aValue - bValue : bValue - aValue;
    }
    const aString = String(aValue).toLowerCase();
    const bString = String(bValue).toLowerCase();
    if (aString < bString) {
      return direction === "asc" ? -1 : 1;
    }
    if (aString > bString) {
      return direction === "asc" ? 1 : -1;
    }
    return 0;
  });
};

export const createStaticDataSource = (
  initialRecords: AdminRecord[],
  options: StaticDataSourceOptions = {}
): AdminTableDataSource => {
  const dataset: InMemoryDataset = {
    records: [...initialRecords],
    descriptor: {
      primaryKey: "id",
      searchable: new Set(options.searchableFields ?? ["id", "name", "title", "email"]),
      filterable: new Set(options.filterableFields ?? []),
    },
  };

  const list = async (query: AdminListQuery) => {
    const page = Math.max(1, query.page ?? 1);
    const pageSize = Math.max(1, query.pageSize ?? 25);

    let result = [...dataset.records];
    result = applySearchFilter(result, query, dataset);
    result = applyFieldFilters(result, query.filters ?? {});

    const sortField = query.sort?.fieldId;
    const sortDirection = query.sort?.direction ?? "asc";
    if (sortField) {
      result = applySorting(result, sortField, sortDirection);
    }

    const total = result.length;
    const start = (page - 1) * pageSize;
    const end = start + pageSize;
    const items = result.slice(start, end);

    await new Promise((resolve) => setTimeout(resolve, 120));

    return {
      items,
      total,
      page,
      pageSize,
    };
  };

  const retrieve = async (id: AdminRecordId) => {
    await new Promise((resolve) => setTimeout(resolve, 60));
    return dataset.records.find((record) => record.id === id) ?? null;
  };

  const update = async (id: AdminRecordId, payload: Partial<AdminRecord>) => {
    const index = dataset.records.findIndex((record) => record.id === id);
    if (index === -1) {
      throw new Error(`Record with id ${id} not found`);
    }
    const updated = { ...dataset.records[index], ...payload, id };
    dataset.records[index] = updated;
    await new Promise((resolve) => setTimeout(resolve, 100));
    return updated;
  };

  return {
    list,
    retrieve,
    update,
  };
};

const customerFields: AdminFieldDescriptor[] = [
  { id: "id", label: "ID", kind: "integer", sortable: true, width: "80px" },
  { id: "name", label: "Name", kind: "text", sortable: true, searchable: true },
  { id: "email", label: "Email", kind: "email", sortable: true, searchable: true },
  { id: "status", label: "Status", kind: "status", sortable: true },
  { id: "city", label: "City", kind: "text", sortable: true, searchable: true },
  { id: "createdAt", label: "Created", kind: "datetime", sortable: true },
  { id: "tags", label: "Tags", kind: "tag" },
];

const orderFields: AdminFieldDescriptor[] = [
  { id: "id", label: "Order", kind: "integer", sortable: true, width: "90px" },
  { id: "number", label: "Number", kind: "text", sortable: true },
  { id: "status", label: "Status", kind: "status", sortable: true },
  { id: "total", label: "Total", kind: "currency", sortable: true },
  { id: "orderedAt", label: "Ordered At", kind: "datetime", sortable: true },
  { id: "salesChannel", label: "Channel", kind: "text" },
];

const buildCustomerRecords = (): AdminRecord[] =>
  Array.from({ length: 48 }, (_, index) => {
    const id = index + 1;
    return {
      id,
      name: `Customer ${id}`,
      email: `customer${id}@example.com`,
      status: id % 3 === 0 ? "Inactive" : id % 3 === 1 ? "Active" : "Pending",
      city: ["Seattle", "Portland", "San Francisco", "Denver"][id % 4],
      createdAt: new Date(Date.now() - id * 86_400_000).toISOString(),
      tags: id % 2 === 0 ? ["wholesale", "priority"] : ["retail"],
    } satisfies AdminRecord;
  });

const buildOrderRecords = (): AdminRecord[] =>
  Array.from({ length: 62 }, (_, index) => {
    const id = index + 101;
    return {
      id,
      number: `SO-${1000 + id}`,
      status: id % 4 === 0 ? "Processing" : id % 4 === 1 ? "Completed" : id % 4 === 2 ? "Cancelled" : "Draft",
      total: Number((Math.random() * 3200 + 120).toFixed(2)),
      orderedAt: new Date(Date.now() - index * 43_200_000).toISOString(),
      salesChannel: ["Web", "Mobile", "In-Store"][index % 3],
    } satisfies AdminRecord;
  });

export const demoThreeColumnConfig: AdminAppDefinition[] = [
  {
    id: "accounts",
    label: "Accounts",
    description: "Key account entities",
    tables: [
      {
        id: "customers",
        label: "Customers",
        description: "Manage customer records",
        defaultListFields: ["id", "name", "email", "status", "city", "createdAt"],
        defaultDetailFields: ["id", "name", "email", "status", "city", "createdAt", "tags"],
        fields: customerFields,
        filterDefinitions: [
          { id: "status", label: "Status", type: "select", options: ["Active", "Inactive", "Pending"].map((label) => ({ value: label, label })) },
          { id: "city", label: "City", type: "select", options: ["Seattle", "Portland", "San Francisco", "Denver"].map((label) => ({ value: label, label })) },
          { id: "createdAt", label: "Created", type: "date-range" },
        ],
        dataSource: createStaticDataSource(buildCustomerRecords(), {
          searchableFields: ["name", "email", "city"],
        }),
      } satisfies AdminTableDefinition,
    ],
  },
  {
    id: "sales",
    label: "Sales",
    description: "Commerce activity",
    tables: [
      {
        id: "orders",
        label: "Sales Orders",
        description: "Incoming sales orders",
        defaultListFields: ["id", "number", "status", "total", "orderedAt"],
        defaultDetailFields: ["id", "number", "status", "total", "orderedAt", "salesChannel"],
        fields: orderFields,
        filterDefinitions: [
          { id: "status", label: "Status", type: "multi-select", options: ["Processing", "Completed", "Cancelled", "Draft"].map((label) => ({ value: label, label })) },
          { id: "orderedAt", label: "Ordered", type: "date-range" },
        ],
        dataSource: createStaticDataSource(buildOrderRecords(), {
          searchableFields: ["number", "status", "salesChannel"],
        }),
      } satisfies AdminTableDefinition,
    ],
  },
];
