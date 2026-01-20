import { deleteRecord, getRecord, getRecords, saveRecord } from "../../../wcapi";
import type {
  AdminListQuery,
  AdminListResult,
  AdminRecord,
  AdminRecordId,
  AdminTableDataSource,
} from "./types";

export type WcapiDataSourceOptions = {
  modelName: string;
  primaryKeyField?: string;
  listExtraParams?: Record<string, unknown> | ((query: AdminListQuery) => Record<string, unknown>);
  mapFilters?: (filters: Record<string, unknown>) => Record<string, unknown>;
  mapRecord?: (record: Record<string, unknown>) => AdminRecord;
  mapOutgoingRecord?: (record: Partial<AdminRecord>) => Record<string, unknown>;
};

const DEFAULT_PAGE_SIZE = 25;

const normalizeRecord = (
  record: Record<string, unknown>,
  primaryKeyField: string,
  mapRecord?: (record: Record<string, unknown>) => AdminRecord
): AdminRecord => {
  const normalized: Record<string, unknown> = { ...record };
  const primaryKeyValue = normalized[primaryKeyField];
  if (primaryKeyField !== "id") {
    normalized.id = primaryKeyValue ?? normalized.id ?? null;
  }
  if (!normalized.id) {
    normalized.id = primaryKeyValue ?? normalized.ida ?? null;
  }
  return mapRecord ? mapRecord(normalized) : (normalized as AdminRecord);
};

const sanitizeFilters = (filters?: Record<string, unknown>): Record<string, unknown> => {
  if (!filters) {
    return {};
  }
  const entries = Object.entries(filters).filter(([_, value]) => {
    if (value === null || value === undefined) {
      return false;
    }
    if (typeof value === "string" && value.trim().length === 0) {
      return false;
    }
    if (Array.isArray(value) && value.length === 0) {
      return false;
    }
    if (typeof value === "object" && !Array.isArray(value)) {
      const { from, to } = value as { from?: unknown; to?: unknown };
      if (!from && !to) {
        return false;
      }
    }
    return true;
  });
  return Object.fromEntries(entries);
};

const buildListParams = (
  query: AdminListQuery,
  options: WcapiDataSourceOptions
): Record<string, unknown> => {
  const params: Record<string, unknown> = {
    limit: query.pageSize ?? DEFAULT_PAGE_SIZE,
    offset: Math.max(0, (query.page - 1) * (query.pageSize ?? DEFAULT_PAGE_SIZE)),
  };

  if (query.search) {
    params.search = query.search;
    params.q = query.search;
  }

  const filters = options.mapFilters ? options.mapFilters(query.filters ?? {}) : sanitizeFilters(query.filters);
  Object.assign(params, filters);

  if (query.sort?.fieldId) {
    const directionPrefix = query.sort.direction === "desc" ? "-" : "";
    params.order_by = `${directionPrefix}${query.sort.fieldId}`;
  }

  const extra = typeof options.listExtraParams === "function"
    ? options.listExtraParams(query)
    : options.listExtraParams;

  if (extra && typeof extra === "object") {
    Object.assign(params, extra);
  }

  return params;
};

const prepareOutgoingRecord = (
  id: AdminRecordId | null,
  payload: Partial<AdminRecord>,
  primaryKeyField: string,
  mapOutgoingRecord?: (record: Partial<AdminRecord>) => Record<string, unknown>
): Record<string, unknown> => {
  const base: Record<string, unknown> = mapOutgoingRecord ? mapOutgoingRecord(payload) : { ...payload };

  if (primaryKeyField === "id") {
    base.id = id ?? base.id;
  } else {
    const primaryKeyValue = (payload as Record<string, unknown>)[primaryKeyField] ?? base[primaryKeyField] ?? id;
    if (primaryKeyValue !== undefined) {
      base[primaryKeyField] = primaryKeyValue;
    }
    if (id != null) {
      base.id = id;
    }
  }

  return base;
};

export const createWcapiDataSource = (options: WcapiDataSourceOptions): AdminTableDataSource => {
  const primaryKeyField = options.primaryKeyField ?? "id";

  return {
    list: async (query: AdminListQuery): Promise<AdminListResult> => {
      const params = buildListParams(query, options);
      const response = await getRecords(options.modelName, params);
      const rawItems = (response?.results ?? []) as Record<string, unknown>[];
      const items = rawItems.map((item) => normalizeRecord(item, primaryKeyField, options.mapRecord));
      const total = (response?.total ?? rawItems.length) as number;
      const limit = (response?.limit ?? params.limit ?? query.pageSize ?? DEFAULT_PAGE_SIZE) as number;
      const offset = (response?.offset ?? params.offset ?? (query.page - 1) * limit) as number;
      const page = Math.floor(offset / limit) + 1;

      return {
        items,
        total,
        page,
        pageSize: limit,
        aggregates: (response as any)?.aggregates ?? undefined,
      };
    },
    retrieve: async (id: AdminRecordId) => {
      const response = await getRecord(options.modelName, Number(id));
      const record = (response?.record ?? response) as Record<string, unknown> | null;
      if (!record) {
        return null;
      }
      return normalizeRecord(record, primaryKeyField, options.mapRecord);
    },
    update: async (id: AdminRecordId, payload: Partial<AdminRecord>) => {
      const resolvedId = id ?? (payload?.id as AdminRecordId | undefined) ?? null;
      const wcapiPayload = prepareOutgoingRecord(resolvedId, payload, primaryKeyField, options.mapOutgoingRecord);
      const response = await saveRecord(options.modelName, wcapiPayload);
      const record = (response?.record ?? response) as Record<string, unknown> | null;
      if (!record) {
        return { ...(payload as Record<string, unknown>), id: resolvedId } as AdminRecord;
      }
      return normalizeRecord(record, primaryKeyField, options.mapRecord);
    },
    create: async (payload: Partial<AdminRecord>) => {
      const wcapiPayload = prepareOutgoingRecord(null, payload, primaryKeyField, options.mapOutgoingRecord);
      const response = await saveRecord(options.modelName, wcapiPayload);
      const record = (response?.record ?? response) as Record<string, unknown> | null;
      if (!record) {
        throw new Error("WCAPI save did not return a record");
      }
      return normalizeRecord(record, primaryKeyField, options.mapRecord);
    },
    remove: async (id: AdminRecordId) => {
      await deleteRecord(options.modelName, Number(id));
    },
  };
};
