import {
  ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type {
  AdminAppDefinition,
  AdminListQuery,
  AdminRecord,
  AdminRecordId,
  AdminTableDefinition,
  AdminWorkspaceConfig,
  AdminQuerySort,
  LayoutPreference,
} from "./types";
import { buildTablePreferenceKey, useLayoutPreferences } from "./useLayoutPreferences";

type AdminListState = {
  items: AdminRecord[];
  total: number;
  page: number;
  pageSize: number;
  loading: boolean;
  error: string | null;
  search: string;
  filters: Record<string, unknown>;
  sort: AdminQuerySort | null;
  pageSizeOptions: number[];
};

type AdminDetailState = {
  record: AdminRecord | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
};

type AdminWorkspaceContextValue = {
  apps: AdminAppDefinition[];
  selectedAppId: string | null;
  selectedTableId: string | null;
  selectedRecordId: AdminRecordId | null;
  selectedApp?: AdminAppDefinition;
  selectedTable?: AdminTableDefinition;
  list: AdminListState;
  detail: AdminDetailState;
  listFields: AdminTableDefinition["fields"];
  hiddenListFields: AdminTableDefinition["fields"];
  detailFields: AdminTableDefinition["fields"];
  hiddenDetailFields: AdminTableDefinition["fields"];
  setSelectedAppId: (appId: string) => void;
  setSelectedTableId: (tableId: string) => void;
  setSelectedRecordId: (recordId: AdminRecordId | null) => void;
  setListSearch: (value: string) => void;
  setListFilters: (filters: Record<string, unknown>) => void;
  resetListFilters: () => void;
  setListSort: (sort: AdminQuerySort | null) => void;
  setListPage: (page: number) => void;
  setListPageSize: (pageSize: number) => void;
  refreshList: () => void;
  refreshRecord: () => void;
  updateCurrentRecord: (payload: Partial<AdminRecord>) => Promise<AdminRecord | null>;
  updateListLayout: (preference: LayoutPreference) => void;
  resetListLayout: () => void;
  updateDetailLayout: (preference: LayoutPreference) => void;
  resetDetailLayout: () => void;
};

const AdminWorkspaceContext = createContext<AdminWorkspaceContextValue | undefined>(undefined);

const DEFAULT_PAGE_SIZES = [10, 25, 50, 100];

const coerceErrorMessage = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === "string") {
    return error;
  }
  try {
    return JSON.stringify(error);
  } catch (serializationError) {
    console.warn("Unable to serialize error", serializationError);
    return "Unexpected error";
  }
};

const derivePageSizeOptions = (
  table?: AdminTableDefinition,
  fallback?: number[]
): number[] => {
  if (table?.pageSizeOptions?.length) {
    return table.pageSizeOptions;
  }
  if (fallback?.length) {
    return fallback;
  }
  return DEFAULT_PAGE_SIZES;
};

const deriveDefaultPageSize = (
  table?: AdminTableDefinition,
  fallback?: number
): number => {
  if (table?.defaultPageSize) {
    return table.defaultPageSize;
  }
  if (fallback) {
    return fallback;
  }
  return 25;
};

type ProviderProps = {
  config: AdminWorkspaceConfig;
  children: ReactNode;
};

export const AdminWorkspaceProvider = ({ config, children }: ProviderProps) => {
  const { apps } = config;

  const [selectedAppId, setSelectedAppId] = useState<string | null>(() => {
    if (config.initialAppId) {
      return config.initialAppId;
    }
    return apps[0]?.id ?? null;
  });

  const selectedApp = useMemo(
    () => apps.find((app) => app.id === selectedAppId) ?? apps[0],
    [apps, selectedAppId]
  );

  const [selectedTableId, setSelectedTableId] = useState<string | null>(() => {
    if (config.initialTableId) {
      return config.initialTableId;
    }
    return selectedApp?.tables[0]?.id ?? null;
  });

  useEffect(() => {
    if (!selectedApp) {
      setSelectedTableId(null);
      return;
    }
    if (!selectedApp.tables.length) {
      setSelectedTableId(null);
      return;
    }
    if (!selectedTableId || !selectedApp.tables.some((table) => table.id === selectedTableId)) {
      setSelectedTableId(selectedApp.tables[0]?.id ?? null);
    }
  }, [selectedApp, selectedTableId]);

  const selectedTable = useMemo(
    () => selectedApp?.tables.find((table) => table.id === selectedTableId),
    [selectedApp, selectedTableId]
  );

  const [listPage, setListPageState] = useState(1);
  const [listPageSizeState, setListPageSizeState] = useState(() =>
    deriveDefaultPageSize(selectedTable, config.defaultPageSize)
  );
  const [listSearch, setListSearch] = useState("");
  const [listFilters, setListFiltersState] = useState<Record<string, unknown>>({});
  const [listSort, setListSort] = useState<AdminQuerySort | null>(selectedTable?.defaultSort ?? null);
  const [listReloadToken, setListReloadToken] = useState(0);

  const pageSizeOptions = useMemo(
    () => derivePageSizeOptions(selectedTable, config.pageSizeOptions),
    [selectedTable, config.pageSizeOptions]
  );

  const [listItems, setListItems] = useState<AdminRecord[]>([]);
  const [listTotal, setListTotal] = useState(0);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);

  const [detailRecord, setDetailRecord] = useState<AdminRecord | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailSaving, setDetailSaving] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    setListPageState(1);
    setListSearch("");
    setListFiltersState({});
    setListSort(selectedTable?.defaultSort ?? null);
    setListPageSizeState(deriveDefaultPageSize(selectedTable, config.defaultPageSize));
    setSelectedRecordId(null);
    setDetailRecord(null);
    setDetailError(null);
  }, [selectedTable?.id, config.defaultPageSize]);

  const [selectedRecordId, setSelectedRecordId] = useState<AdminRecordId | null>(null);

  const { resolveFields, updatePreference, resetPreference } = useLayoutPreferences(config.storageKey);

  const tablePreferenceKey = useMemo(() => {
    if (!selectedApp || !selectedTable) {
      return null;
    }
    return buildTablePreferenceKey(selectedApp.id, selectedTable.id);
  }, [selectedApp, selectedTable]);

  const { visible: listFields, hidden: hiddenListFields } = useMemo(() => {
    if (!selectedTable || !tablePreferenceKey) {
      return { visible: [], hidden: [] };
    }
    return resolveFields(tablePreferenceKey, { table: selectedTable, view: "list", includeHidden: true });
  }, [resolveFields, selectedTable, tablePreferenceKey]);

  const { visible: detailFields, hidden: hiddenDetailFields } = useMemo(() => {
    if (!selectedTable || !tablePreferenceKey) {
      return { visible: [], hidden: [] };
    }
    return resolveFields(tablePreferenceKey, { table: selectedTable, view: "detail", includeHidden: true });
  }, [resolveFields, selectedTable, tablePreferenceKey]);

  const listPageSize = listPageSizeState;

  const setListPage = useCallback((page: number) => {
    setListPageState(Math.max(1, page));
  }, []);

  const setListPageSize = useCallback((pageSize: number) => {
    setListPageState(1);
    setListPageSizeState(pageSize);
  }, []);

  const setListFilters = useCallback((filters: Record<string, unknown>) => {
    setListPageState(1);
    setListFiltersState(filters);
  }, []);

  const resetListFilters = useCallback(() => {
    setListPageState(1);
    setListFiltersState({});
  }, []);

  const refreshList = useCallback(() => {
    setListReloadToken((token) => token + 1);
  }, []);

  const refreshRecord = useCallback(() => {
    setListReloadToken((token) => token + 1);
  }, []);

  const listQuery: AdminListQuery | null = useMemo(() => {
    if (!selectedTable) {
      return null;
    }
    return {
      page: listPage,
      pageSize: listPageSize,
      search: listSearch || undefined,
      filters: Object.keys(listFilters).length ? listFilters : undefined,
      sort: listSort ?? undefined,
    };
  }, [selectedTable, listPage, listPageSize, listSearch, listFilters, listSort]);

  useEffect(() => {
    if (!selectedTable || !listQuery) {
      setListItems([]);
      setListTotal(0);
      setListLoading(false);
      return;
    }

    let isCancelled = false;
    setListLoading(true);
    setListError(null);

    selectedTable.dataSource
      .list(listQuery)
      .then((result) => {
        if (isCancelled) {
          return;
        }
        setListItems(result.items ?? []);
        setListTotal(result.total ?? result.items.length ?? 0);
        setListPageState(result.page ?? listQuery.page);
        setListPageSizeState(result.pageSize ?? listQuery.pageSize);

        if (!result.items?.length) {
          setSelectedRecordId(null);
          setDetailRecord(null);
          return;
        }

        setSelectedRecordId((current) => {
          if (current && result.items?.some((item) => item.id === current)) {
            return current;
          }
          return result.items[0]?.id ?? null;
        });
      })
      .catch((error) => {
        if (isCancelled) {
          return;
        }
        setListError(coerceErrorMessage(error));
      })
      .finally(() => {
        if (!isCancelled) {
          setListLoading(false);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [selectedTable, listQuery, listReloadToken]);

  useEffect(() => {
    if (!selectedTable) {
      setDetailRecord(null);
      setDetailError(null);
      setDetailLoading(false);
      return;
    }

    if (!selectedRecordId) {
      setDetailRecord(null);
      setDetailError(null);
      setDetailLoading(false);
      return;
    }

    const inlineRecord = listItems.find((item) => item.id === selectedRecordId) ?? null;

    if (!selectedTable.dataSource.retrieve) {
      setDetailRecord(inlineRecord);
      setDetailError(null);
      setDetailLoading(false);
      return;
    }

    let isCancelled = false;
    setDetailLoading(true);
    setDetailError(null);

    selectedTable.dataSource
      .retrieve(selectedRecordId)
      .then((record) => {
        if (isCancelled) {
          return;
        }
        setDetailRecord(record ?? inlineRecord ?? null);
      })
      .catch((error) => {
        if (isCancelled) {
          return;
        }
        setDetailError(coerceErrorMessage(error));
      })
      .finally(() => {
        if (!isCancelled) {
          setDetailLoading(false);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [selectedTable, selectedRecordId, listItems]);

  const updateCurrentRecord = useCallback(
    async (payload: Partial<AdminRecord>) => {
      if (!selectedTable || !selectedRecordId || !selectedTable.dataSource.update) {
        return null;
      }
      setDetailSaving(true);
      setDetailError(null);
      try {
        const updated = await selectedTable.dataSource.update(selectedRecordId, payload);
        setDetailRecord((current) => ({ ...(current ?? {}), ...updated }));
        setListItems((current) =>
          current.map((item) => (item.id === updated.id ? { ...item, ...updated } : item))
        );
        return updated;
      } catch (error) {
        setDetailError(coerceErrorMessage(error));
        throw error;
      } finally {
        setDetailSaving(false);
      }
    },
    [selectedTable, selectedRecordId]
  );

  const updateListLayout = useCallback(
    (preference: LayoutPreference) => {
      if (!tablePreferenceKey) {
        return;
      }
      updatePreference(tablePreferenceKey, "list", preference);
    },
    [updatePreference, tablePreferenceKey]
  );

  const resetListLayout = useCallback(() => {
    if (!tablePreferenceKey) {
      return;
    }
    resetPreference(tablePreferenceKey, "list");
  }, [resetPreference, tablePreferenceKey]);

  const updateDetailLayout = useCallback(
    (preference: LayoutPreference) => {
      if (!tablePreferenceKey) {
        return;
      }
      updatePreference(tablePreferenceKey, "detail", preference);
    },
    [updatePreference, tablePreferenceKey]
  );

  const resetDetailLayout = useCallback(() => {
    if (!tablePreferenceKey) {
      return;
    }
    resetPreference(tablePreferenceKey, "detail");
  }, [resetPreference, tablePreferenceKey]);

  const listState: AdminListState = useMemo(
    () => ({
      items: listItems,
      total: listTotal,
      page: listPage,
      pageSize: listPageSize,
      loading: listLoading,
      error: listError,
      search: listSearch,
      filters: listFilters,
      sort: listSort,
      pageSizeOptions,
    }),
    [
      listItems,
      listTotal,
      listPage,
      listPageSize,
      listLoading,
      listError,
      listSearch,
      listFilters,
      listSort,
      pageSizeOptions,
    ]
  );

  const detailState: AdminDetailState = useMemo(
    () => ({
      record: detailRecord,
      loading: detailLoading,
      saving: detailSaving,
      error: detailError,
    }),
    [detailRecord, detailLoading, detailSaving, detailError]
  );

  const contextValue: AdminWorkspaceContextValue = useMemo(
    () => ({
      apps,
      selectedAppId,
      selectedTableId,
      selectedRecordId,
      selectedApp,
      selectedTable,
      list: listState,
      detail: detailState,
      listFields,
      hiddenListFields,
      detailFields,
      hiddenDetailFields,
      setSelectedAppId: (appId: string) => {
        setSelectedAppId(appId);
      },
      setSelectedTableId: (tableId: string) => {
        setSelectedTableId(tableId);
      },
      setSelectedRecordId,
      setListSearch,
      setListFilters,
      resetListFilters,
      setListSort,
      setListPage,
      setListPageSize,
      refreshList,
      refreshRecord,
      updateCurrentRecord,
      updateListLayout,
      resetListLayout,
      updateDetailLayout,
      resetDetailLayout,
    }),
    [
      apps,
      selectedAppId,
      selectedTableId,
      selectedRecordId,
      selectedApp,
      selectedTable,
      listState,
      detailState,
      listFields,
      hiddenListFields,
      detailFields,
      hiddenDetailFields,
      setListFilters,
      resetListFilters,
      setListSort,
      setListPage,
      setListPageSize,
      refreshList,
      refreshRecord,
      updateCurrentRecord,
      updateListLayout,
      resetListLayout,
      updateDetailLayout,
      resetDetailLayout,
    ]
  );

  return <AdminWorkspaceContext.Provider value={contextValue}>{children}</AdminWorkspaceContext.Provider>;
};

export const useAdminWorkspace = (): AdminWorkspaceContextValue => {
  const context = useContext(AdminWorkspaceContext);
  if (!context) {
    throw new Error("useAdminWorkspace must be used within an AdminWorkspaceProvider");
  }
  return context;
};
