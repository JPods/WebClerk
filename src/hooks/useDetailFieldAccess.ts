/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useAppSelector } from "@/store/hooks";
import {
  DetailFieldSettingRecord,
  getDetailFieldSetting,
  saveDetailFieldSetting,
} from "@/api/wcapi";

export type DetailFieldAccessConfig = {
  hidden: string[];
  readOnly: string[];
};

type DetailFieldAccessState = {
  config: DetailFieldAccessConfig;
  settingId?: number;
};

const DEFAULT_CONFIG: DetailFieldAccessConfig = {
  hidden: [],
  readOnly: [],
};

const DETAIL_PURPOSE = "detail_field_access";

const toSet = (values: string[]) => {
  return new Set(values);
};

const normalizeConfig = (
  config: DetailFieldAccessConfig | null | undefined,
  fieldNames: string[]
): DetailFieldAccessConfig => {
  const allowed = new Set(fieldNames);
  const hidden = Array.from(
    new Set((config?.hidden ?? []).filter((field) => allowed.has(field)))
  );
  const readOnly = Array.from(
    new Set((config?.readOnly ?? []).filter((field) => allowed.has(field)))
  );
  return {
    hidden,
    readOnly,
  };
};

const configsEqual = (
  a: DetailFieldAccessConfig,
  b: DetailFieldAccessConfig
): boolean => {
  if (a.hidden.length !== b.hidden.length) return false;
  if (a.readOnly.length !== b.readOnly.length) return false;
  const hiddenA = toSet(a.hidden);
  const hiddenB = toSet(b.hidden);
  for (const value of hiddenA) {
    if (!hiddenB.has(value)) return false;
  }
  const readOnlyA = toSet(a.readOnly);
  const readOnlyB = toSet(b.readOnly);
  for (const value of readOnlyA) {
    if (!readOnlyB.has(value)) return false;
  }
  return true;
};

const hasAdminRole = (role: unknown): boolean => {
  if (typeof role === "string") {
    return role.toLowerCase().includes("admin");
  }
  if (Array.isArray(role)) {
    return role.some(
      (item) => typeof item === "string" && item.toLowerCase().includes("admin")
    );
  }
  if (role && typeof role === "object") {
    const values = Object.values(role as Record<string, unknown>);
    return values.some(
      (value) => typeof value === "string" && value.toLowerCase().includes("admin")
    );
  }
  return false;
};

export type UseDetailFieldAccessResult = {
  isAdmin: boolean;
  loading: boolean;
  saving: boolean;
  error: string | null;
  config: DetailFieldAccessConfig;
  isFieldVisible: (fieldName: string) => boolean;
  isFieldReadOnly: (fieldName: string) => boolean;
  setFieldVisible: (fieldName: string, visible: boolean) => void;
  setFieldReadOnly: (fieldName: string, readOnly: boolean) => void;
  resetConfig: () => void;
  saveConfig: () => Promise<void>;
  isDirty: boolean;
};

export function useDetailFieldAccess(
  modelName: string,
  fieldNames: string[]
): UseDetailFieldAccessResult {
  const { user } = useAppSelector((state) => state.auth);
  const [state, setState] = useState<DetailFieldAccessState>({
    config: normalizeConfig(DEFAULT_CONFIG, fieldNames),
  });
  const [initialConfig, setInitialConfig] = useState<DetailFieldAccessConfig>(
    normalizeConfig(DEFAULT_CONFIG, fieldNames)
  );
  const [loading, setLoading] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const isAdmin = useMemo(() => {
    if (!user) return false;
    if (user.is_superuser) return true;
    if (user.is_staff) return true;
    return hasAdminRole(user.role);
  }, [user]);

  useEffect(() => {
    setState((prev) => ({
      ...prev,
      config: normalizeConfig(prev.config, fieldNames),
    }));
    setInitialConfig((prev) => normalizeConfig(prev, fieldNames));
  }, [fieldNames]);

  useEffect(() => {
    if (!modelName) return;
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const existing = await getDetailFieldSetting(modelName);
        if (cancelled) return;
        const normalized = normalizeConfig(existing?.data, fieldNames);
        setState({
          config: normalized,
          settingId: existing?.id,
        });
        setInitialConfig(normalized);
      } catch (err: unknown) {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Failed to load field access";
        setError(message);
      } finally {
        if (cancelled) return;
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [modelName, fieldNames]);

  const hiddenSet = useMemo(() => new Set(state.config.hidden), [state.config.hidden]);
  const readOnlySet = useMemo(() => new Set(state.config.readOnly), [state.config.readOnly]);

  const isFieldVisible = useCallback(
    (fieldName: string) => {
      if (!fieldNames.includes(fieldName)) return true;
      return !hiddenSet.has(fieldName);
    },
    [fieldNames, hiddenSet]
  );

  const isFieldReadOnly = useCallback(
    (fieldName: string) => {
      if (!fieldNames.includes(fieldName)) return false;
      return readOnlySet.has(fieldName);
    },
    [fieldNames, readOnlySet]
  );

  const setFieldVisible = useCallback((fieldName: string, visible: boolean) => {
    setState((prev) => {
      const hidden = new Set(prev.config.hidden);
      if (visible) {
        hidden.delete(fieldName);
      } else {
        hidden.add(fieldName);
      }
      return {
        ...prev,
        config: {
          ...prev.config,
          hidden: Array.from(hidden),
        },
      };
    });
  }, []);

  const setFieldReadOnly = useCallback((fieldName: string, readOnly: boolean) => {
    setState((prev) => {
      const next = new Set(prev.config.readOnly);
      if (readOnly) {
        next.add(fieldName);
      } else {
        next.delete(fieldName);
      }
      return {
        ...prev,
        config: {
          ...prev.config,
          readOnly: Array.from(next),
        },
      };
    });
  }, []);

  const resetConfig = useCallback(() => {
    setState((prev) => ({
      ...prev,
      config: initialConfig,
    }));
  }, [initialConfig]);

  const saveConfig = useCallback(async () => {
    if (!isAdmin || !modelName) return;
    try {
      setSaving(true);
      setError(null);
      const payload: DetailFieldSettingRecord = {
        id: state.settingId,
        model_name: modelName,
        purpose: DETAIL_PURPOSE,
        data: {
          hidden: state.config.hidden,
          readOnly: state.config.readOnly,
        },
      };
      const response = await saveDetailFieldSetting(payload);
      const nextId = typeof response?.id === "number" ? response.id : state.settingId;
      setState((prev) => ({
        ...prev,
        settingId: nextId,
      }));
      const normalized = normalizeConfig(state.config, fieldNames);
      setInitialConfig(normalized);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to save field access";
      setError(message);
    } finally {
      setSaving(false);
    }
  }, [fieldNames, isAdmin, modelName, state.config, state.settingId]);

  const isDirty = useMemo(() => {
    return !configsEqual(state.config, initialConfig);
  }, [state.config, initialConfig]);

  return {
    isAdmin,
    loading,
    saving,
    error,
    config: state.config,
    isFieldVisible,
    isFieldReadOnly,
    setFieldVisible,
    setFieldReadOnly,
    resetConfig,
    saveConfig,
    isDirty,
  };
}
