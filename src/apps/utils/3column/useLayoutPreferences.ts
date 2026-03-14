/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useCallback, useEffect, useMemo, useState } from "react";
import type {
  AdminFieldDescriptor,
  AdminTableDefinition,
  LayoutPreference,
  LayoutPreferencesMap,
  TableLayoutPreferences,
} from "./types";

const STORAGE_NAMESPACE = "webclerk:admin:3column:layout";

type LayoutView = "list" | "detail";

type ResolveLayoutArgs = {
  table: AdminTableDefinition;
  view: LayoutView;
  preference?: LayoutPreference;
};

type ResolveFieldsArgs = ResolveLayoutArgs & {
  includeHidden?: boolean;
};

type ResolvedLayout = {
  visibleFieldIds: string[];
  hiddenFieldIds: string[];
};

type LayoutPreferencesApi = {
  preferences: LayoutPreferencesMap;
  updatePreference: (tableKey: string, view: LayoutView, preference: LayoutPreference) => void;
  resetPreference: (tableKey: string, view: LayoutView) => void;
  resolveLayout: (tableKey: string, args: ResolveLayoutArgs) => ResolvedLayout;
  resolveFields: (tableKey: string, args: ResolveFieldsArgs) => {
    visible: AdminFieldDescriptor[];
    hidden: AdminFieldDescriptor[];
  };
  getPreference: (tableKey: string, view: LayoutView) => LayoutPreference | undefined;
};

const readStorage = (key: string): LayoutPreferencesMap => {
  if (typeof window === "undefined") {
    return {};
  }
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as LayoutPreferencesMap;
    return parsed ?? {};
  } catch (error) {
    console.warn("Failed to parse admin layout preferences", error);
    return {};
  }
};

const writeStorage = (key: string, value: LayoutPreferencesMap) => {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.warn("Failed to persist admin layout preferences", error);
  }
};

const isNonEmptyString = (value: unknown): value is string => typeof value === "string" && value.trim().length > 0;

const computeDefaultFieldIds = (table: AdminTableDefinition, view: LayoutView): string[] => {
  const availableFieldIds = new Set(table.fields.map((field) => field.id));
  if (view === "list") {
    const defaults = table.defaultListFields ?? table.fields.map((field) => field.id);
    return defaults.filter((id) => availableFieldIds.has(id));
  }
  if (table.defaultDetailFields?.length) {
    return table.defaultDetailFields.filter((id) => availableFieldIds.has(id));
  }
  if (table.detailSections?.length) {
    return table.detailSections.flatMap((section) =>
      section.fieldIds.filter((id) => availableFieldIds.has(id))
    );
  }
  return table.fields.map((field) => field.id);
};

const resolveLayoutInternal = ({ table, view, preference }: ResolveLayoutArgs): ResolvedLayout => {
  const availableFieldIds = table.fields.map((field) => field.id);
  const availableSet = new Set(availableFieldIds);
  const defaultIds = computeDefaultFieldIds(table, view);

  if (!preference) {
    return {
      visibleFieldIds: defaultIds,
      hiddenFieldIds: availableFieldIds.filter((id) => !defaultIds.includes(id)),
    };
  }

  const sanitizedHidden = (preference.hidden ?? []).filter((id) => availableSet.has(id));
  const hiddenSet = new Set(sanitizedHidden);

  const sanitizedOrder = (preference.order ?? []).filter((id) => availableSet.has(id) && !hiddenSet.has(id));

  const remainingDefaults = defaultIds.filter(
    (id) => !hiddenSet.has(id) && !sanitizedOrder.includes(id)
  );

  const additionalVisible = availableFieldIds.filter(
    (id) => !hiddenSet.has(id) && !sanitizedOrder.includes(id) && !remainingDefaults.includes(id)
  );

  const visibleFieldIds = [...sanitizedOrder, ...remainingDefaults, ...additionalVisible];
  const hiddenFieldIds = sanitizedHidden;

  return { visibleFieldIds, hiddenFieldIds };
};



export const useLayoutPreferences = (
  storageKey: string = STORAGE_NAMESPACE
): LayoutPreferencesApi => {
  const [preferences, setPreferences] = useState<LayoutPreferencesMap>(() => readStorage(storageKey));

  useEffect(() => {
    writeStorage(storageKey, preferences);
  }, [storageKey, preferences]);

  const updatePreference = useCallback(
    (tableKey: string, view: LayoutView, preference: LayoutPreference) => {
      setPreferences((current) => {
        const next: LayoutPreferencesMap = { ...current };
        const existing: TableLayoutPreferences = next[tableKey] ? { ...next[tableKey] } : {};
        existing[view] = preference;
        next[tableKey] = existing;
        return next;
      });
    },
    []
  );

  const resetPreference = useCallback((tableKey: string, view: LayoutView) => {
    setPreferences((current) => {
      if (!current[tableKey]?.[view]) {
        return current;
      }
      const next: LayoutPreferencesMap = { ...current };
      const existing = { ...(next[tableKey] ?? {}) };
      delete existing[view];
      if (Object.keys(existing).length === 0) {
        delete next[tableKey];
      } else {
        next[tableKey] = existing;
      }
      return next;
    });
  }, []);

  const resolveLayout = useCallback(
    (tableKey: string, args: ResolveLayoutArgs): ResolvedLayout => {
      const preference = preferences[tableKey]?.[args.view];
      return resolveLayoutInternal({ ...args, preference });
    },
    [preferences]
  );

  const resolveFields = useCallback(
    (tableKey: string, args: ResolveFieldsArgs) => {
      const { table, view, includeHidden } = args;
      const { visibleFieldIds, hiddenFieldIds } = resolveLayout(tableKey, { table, view });
      const fieldDictionary = new Map(table.fields.map((field) => [field.id, field] as const));

      const visible = visibleFieldIds
        .map((fieldId) => fieldDictionary.get(fieldId))
        .filter((field): field is AdminFieldDescriptor => Boolean(field));

      if (!includeHidden) {
        return { visible, hidden: [] };
      }

      const hidden = hiddenFieldIds
        .map((fieldId) => fieldDictionary.get(fieldId))
        .filter((field): field is AdminFieldDescriptor => Boolean(field));

      return { visible, hidden };
    },
    [resolveLayout]
  );

  const getPreference = useCallback(
    (tableKey: string, view: LayoutView) => preferences[tableKey]?.[view],
    [preferences]
  );

  return useMemo(
    () => ({ preferences, updatePreference, resetPreference, resolveLayout, resolveFields, getPreference }),
    [preferences, updatePreference, resetPreference, resolveLayout, resolveFields, getPreference]
  );
};

export const buildTablePreferenceKey = (appId: string, tableId: string): string =>
  [appId, tableId].filter(isNonEmptyString).join(":");
