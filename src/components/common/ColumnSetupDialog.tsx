/**
 * ColumnSetupDialog – modal for viewing / editing a named column-setup configuration.
 *
 * Shows a table of columns with toggles for visibility, editable width fields,
 * drag-to-reorder rows, and sort selection.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ColumnSetupEntry, ColumnSort } from "@/hooks/useColumnSetups";

// ── Props ─────────────────────────────────────────────────────────────────────

interface ColumnMeta {
  /** Persist-key used in the setup (matches getColumnPersistKey output) */
  key: string;
  /** Human label for the column */
  label: string;
}

export interface ColumnSetupDialogProps {
  open: boolean;
  /** display title */
  title: string;
  /** Column metadata (key + label) in their *original* definition order */
  columnMetas: ColumnMeta[];
  /** The config being viewed / edited */
  config: ColumnSetupEntry;
  /** Existing setup names for duplicate checks */
  existingSetupNames?: string[];
  /** Named setup records to display/select in dialog */
  namedSetups?: Array<{ name: string; config: ColumnSetupEntry }>;
  /** Initial setup name; empty/null means current unsaved layout */
  initialSetupName?: string | null;
  /** Save current config as a named setup (create/update) */
  onSaveNamed?: (name: string, config: ColumnSetupEntry) => void;
  /** Live preview callback — fires on every order/visibility/width/sort change */
  onPreview?: (config: ColumnSetupEntry) => void;
  onClose: () => void;
  onSave: (config: ColumnSetupEntry) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export const ColumnSetupDialog = ({
  open,
  title,
  columnMetas,
  config,
  existingSetupNames = [],
  namedSetups = [],
  initialSetupName = null,
  onSaveNamed,
  onPreview,
  onClose,
  onSave,
}: ColumnSetupDialogProps) => {
  // Local edit state
  const [order, setOrder] = useState<string[]>([]);
  const [visibility, setVisibility] = useState<Record<string, boolean>>({});
  const [widths, setWidths] = useState<Record<string, string>>({});
  const [sort, setSort] = useState<ColumnSort | null>(null);
  const [jsonb, setJsonb] = useState<Record<string, Record<string, unknown>>>({});
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [draggedKey, setDraggedKey] = useState<string | null>(null);
  const [setupName, setSetupName] = useState<string>("");
  const [nameError, setNameError] = useState<string>("");
  const [selectedSetupName, setSelectedSetupName] = useState<string>("__current__");
  const [dialogPos, setDialogPos] = useState<{ x: number; y: number }>({ x: -1, y: -1 });
  const [isDraggingDialog, setIsDraggingDialog] = useState(false);
  const [dragOffset, setDragOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [configJsonDraft, setConfigJsonDraft] = useState<string>("{}");
  const [configJsonError, setConfigJsonError] = useState<string>("");
  const wasOpenRef = useRef(false);

  const parseWidthNumber = useCallback((value: unknown): number => {
    const raw = String(value ?? "").trim();
    if (!raw) return 0;
    const numeric = raw.match(/-?\d*\.?\d+/)?.[0];
    if (!numeric) return 0;
    const n = Number(numeric);
    if (!Number.isFinite(n)) return 0;
    return Math.max(0, n);
  }, []);

  const formatPercent = useCallback((value: number): string => {
    const rounded = Math.round(value);
    return `${rounded}%`;
  }, []);

  const MIN_WIDTH_PERCENT = 3;
  const BASE_TABLE_WIDTH_PX = 1200; // Reference width for px ↔ % conversion

  const pixelsToPercent = useCallback((pixels: number): number => {
    if (pixels <= 0 || BASE_TABLE_WIDTH_PX <= 0) return 0;
    return (pixels / BASE_TABLE_WIDTH_PX) * 100;
  }, []);

  const percentToPixels = useCallback((percent: number): number => {
    if (percent <= 0 || BASE_TABLE_WIDTH_PX <= 0) return 0;
    return Math.round((percent / 100) * BASE_TABLE_WIDTH_PX);
  }, []);

  const distributeIntegers = useCallback((weights: number[]): number[] => {
    if (!weights.length) return [];

    const total = weights.reduce((sum, n) => sum + n, 0);
    if (total <= 0) {
      const base = Math.floor(100 / weights.length);
      const out = Array.from({ length: weights.length }, () => base);
      let rem = 100 - base * weights.length;
      for (let i = 0; i < rem; i += 1) out[i] += 1;
      return out;
    }

    const quotas = weights.map((w) => (w / total) * 100);
    const floors = quotas.map((q) => Math.floor(q));
    let remaining = 100 - floors.reduce((sum, n) => sum + n, 0);

    const order = quotas
      .map((q, idx) => ({ idx, frac: q - Math.floor(q), q }))
      .sort((a, b) => b.frac - a.frac || b.q - a.q || a.idx - b.idx);

    for (let i = 0; i < remaining; i += 1) {
      floors[order[i % order.length].idx] += 1;
    }

    return floors;
  }, []);

  const effectiveMinWidth = useCallback((count: number): number => {
    if (count <= 0) return 0;
    // Keep a 3% floor when possible; otherwise degrade gracefully for very wide tables.
    if (count * MIN_WIDTH_PERCENT <= 100) return MIN_WIDTH_PERCENT;
    return Math.max(1, Math.floor(100 / count));
  }, []);

  const normalizeWidthMap = useCallback(
    (keys: string[], source: Record<string, unknown> | undefined): Record<string, string> => {
      const next: Record<string, string> = {};
      if (!keys.length) return next;
      if (keys.length === 1) {
        next[keys[0]] = formatPercent(100);
        return next;
      }

      const minWidth = effectiveMinWidth(keys.length);
      const values = keys.map((k) => Math.max(minWidth, Math.round(parseWidthNumber(source?.[k]))));
      const rightIdx = keys.length - 1;

      let fixedLeftSum = 0;
      for (let i = 0; i < rightIdx; i += 1) fixedLeftSum += values[i];

      let rightValue = 100 - fixedLeftSum;
      if (rightValue < minWidth) {
        // Borrow from right-to-left so left-most values dominate.
        let deficit = minWidth - rightValue;
        for (let i = rightIdx - 1; i >= 0 && deficit > 0; i -= 1) {
          const reducible = Math.max(0, values[i] - minWidth);
          if (reducible <= 0) continue;
          const delta = Math.min(reducible, deficit);
          values[i] -= delta;
          deficit -= delta;
        }
        fixedLeftSum = 0;
        for (let i = 0; i < rightIdx; i += 1) fixedLeftSum += values[i];
        rightValue = 100 - fixedLeftSum;
      }

      if (rightValue < minWidth) {
        // Last-resort fallback for edge cases where min constraints cannot all fit.
        const fallback = distributeIntegers(keys.map((k) => parseWidthNumber(source?.[k])));
        keys.forEach((key, idx) => {
          next[key] = formatPercent(Math.max(minWidth, fallback[idx]));
        });
        const sum = keys.reduce((acc, k) => acc + parseWidthNumber(next[k]), 0);
        const lastKey = keys[keys.length - 1];
        next[lastKey] = formatPercent(Math.max(minWidth, parseWidthNumber(next[lastKey]) + (100 - sum)));
        return next;
      }

      for (let i = 0; i < rightIdx; i += 1) {
        next[keys[i]] = formatPercent(values[i]);
      }
      next[keys[rightIdx]] = formatPercent(rightValue);

      keys.forEach((key) => {
        if (!(key in next)) next[key] = formatPercent(minWidth);
      });

      return next;
    },
    [parseWidthNumber, formatPercent, distributeIntegers, effectiveMinWidth],
  );

  const rebalanceWidthsForKey = useCallback(
    (
      keys: string[],
      current: Record<string, unknown>,
      targetKey: string,
      targetValue: unknown,
    ): Record<string, string> => {
      if (!keys.length) return {};
      if (!keys.includes(targetKey)) return normalizeWidthMap(keys, current);

      if (keys.length === 1) return { [keys[0]]: formatPercent(100) };

      const minWidth = effectiveMinWidth(keys.length);
      const rightKey = keys[keys.length - 1];
      const base = normalizeWidthMap(keys, current);

      const nextValues: Record<string, number> = {};
      keys.forEach((k) => {
        nextValues[k] = Math.max(minWidth, Math.round(parseWidthNumber(base[k])));
      });

      if (targetKey === rightKey) {
        const fixedSum = keys
          .filter((k) => k !== rightKey)
          .reduce((sum, k) => sum + nextValues[k], 0);
        const derivedRight = 100 - fixedSum;
        if (derivedRight >= minWidth) {
          nextValues[rightKey] = derivedRight;
          return keys.reduce<Record<string, string>>((acc, key) => {
            acc[key] = formatPercent(nextValues[key]);
            return acc;
          }, {});
        }
        return normalizeWidthMap(keys, nextValues);
      }

      const fixedKeys = keys.filter((k) => k !== targetKey && k !== rightKey);
      const fixedSum = fixedKeys.reduce((sum, k) => sum + nextValues[k], 0);

      const minTarget = minWidth;
      const maxTarget = 100 - fixedSum - minWidth;
      if (maxTarget < minTarget) return normalizeWidthMap(keys, nextValues);

      const requested = Math.round(parseWidthNumber(targetValue));
      const clampedTarget = Math.max(minTarget, Math.min(maxTarget, requested));
      const computedRight = 100 - fixedSum - clampedTarget;
      if (computedRight < minWidth) return normalizeWidthMap(keys, nextValues);

      nextValues[targetKey] = clampedTarget;
      nextValues[rightKey] = computedRight;

      return keys.reduce<Record<string, string>>((acc, key) => {
        acc[key] = formatPercent(nextValues[key]);
        return acc;
      }, {});
    },
    [normalizeWidthMap, parseWidthNumber, effectiveMinWidth, formatPercent],
  );

  const toDisplayName = useCallback((key: string): string => {
    const i = key.indexOf(":");
    return i >= 0 ? key.slice(i + 1).trim() : key;
  }, []);

  const toPersistKey = useCallback(
    (name: string, fallbackByIndex: string): string => {
      const trimmed = String(name ?? "").trim();
      if (!trimmed) return fallbackByIndex;

      // Search current order first (exact, then by display name)
      const direct = order.find((k) => k === trimmed);
      if (direct) return direct;

      const byDisplay = order.find((k) => toDisplayName(k).toLowerCase() === trimmed.toLowerCase());
      if (byDisplay) return byDisplay;

      // Also search all available columnMetas so new columns can be added by name
      const metaDirect = columnMetas.find((m) => m.key === trimmed);
      if (metaDirect) return metaDirect.key;

      const metaByDisplay = columnMetas.find(
        (m) => toDisplayName(m.key).toLowerCase() === trimmed.toLowerCase() ||
               (m.label ?? "").toLowerCase() === trimmed.toLowerCase()
      );
      if (metaByDisplay) return metaByDisplay.key;

      // Unknown name but non-empty — use it as-is so user-typed columns aren't silently dropped
      return trimmed || fallbackByIndex;
    },
    [order, toDisplayName, columnMetas],
  );

  const hydrateFromConfig = useCallback(
    (nextConfig: ColumnSetupEntry) => {
      // Build order: start from config.order, then add any missing keys
      const allKeys = columnMetas.map((m) => m.key);
      const existing = new Set(nextConfig.order.filter((k) => allKeys.includes(k)));
      const ordered = [
        ...nextConfig.order.filter((k) => existing.has(k)),
        ...allKeys.filter((k) => !existing.has(k)),
      ];
      setOrder(ordered);
      setVisibility({ ...nextConfig.visibility });
      
      // Convert any % values to pixels when loading
      const convertedWidths: Record<string, string> = {};
      for (const [key, value] of Object.entries(nextConfig.widths || {})) {
        const strValue = String(value ?? "");
        if (strValue.includes("%")) {
          // Extract percentage number and convert to pixels
          const percentValue = parseWidthNumber(strValue);
          const pixelValue = percentToPixels(percentValue);
          convertedWidths[key] = String(Math.max(0, pixelValue));
        } else {
          // Already in pixels or numeric, just ensure no units
          const pixelValue = parseWidthNumber(strValue);
          convertedWidths[key] = String(Math.max(0, pixelValue));
        }
      }
      setWidths(convertedWidths);
      
      setSort(nextConfig.sort ?? null);
      setJsonb({ ...(nextConfig.jsonb ?? {}) });
      const firstKey = ordered[0] ?? null;
      setSelectedKey(firstKey);

    },
    [columnMetas, parseWidthNumber, percentToPixels],
  );

  // Hydrate from config only when dialog first opens (avoid resetting while editing)
  useEffect(() => {
    if (!open) {
      wasOpenRef.current = false;
      return;
    }
    if (!wasOpenRef.current) {
      hydrateFromConfig(config);
      setSetupName(initialSetupName ?? "");
      setSelectedSetupName(initialSetupName ? initialSetupName : "__current__");
      setNameError("");
      setDialogPos({ x: -1, y: -1 });
      setIsDraggingDialog(false);
      wasOpenRef.current = true;
    }
  }, [open, config, initialSetupName, hydrateFromConfig]);

  useEffect(() => {
    if (!open) return;
    if (selectedSetupName === "__current__") return;
    const selected = namedSetups.find((s) => s.name === selectedSetupName);
    if (!selected) return;
    hydrateFromConfig(selected.config);
    setSetupName(selected.name);
    setNameError("");
  }, [selectedSetupName, namedSetups, open, hydrateFromConfig]);

  useEffect(() => {
    if (!isDraggingDialog) return;

    const onMouseMove = (e: MouseEvent) => {
      setDialogPos({
        x: e.clientX - dragOffset.x,
        y: e.clientY - dragOffset.y,
      });
    };

    const onMouseUp = () => {
      setIsDraggingDialog(false);
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [isDraggingDialog, dragOffset]);

  const labelFor = useCallback(
    (key: string) => columnMetas.find((m) => m.key === key)?.label ?? key,
    [columnMetas],
  );

  const moveItem = (index: number, direction: "up" | "down") => {
    setOrder((prev) => {
      const next = [...prev];
      const target = direction === "up" ? index - 1 : index + 1;
      if (target < 0 || target >= next.length) return prev;
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  };

  const selectColumn = useCallback(
    (key: string) => {
      setSelectedKey(key);
    },
    [],
  );

  // Flat config for save / preview (matches ColumnSetupEntry)
  const buildConfig = useMemo<ColumnSetupEntry>(
    () => ({ order, visibility, widths, sort, jsonb }),
    [order, visibility, widths, sort, jsonb],
  );

  // Columnar display format for the JSON editor (plain array — no position keys)
  const configForDisplay = useMemo(() => {
    const columns = order.map((key) => {
      const pixelValue = parseWidthNumber(widths[key]);
      const col: Record<string, unknown> = {
        name: toDisplayName(key),
        visibility: visibility[key] !== false,
        width: String(pixelValue),
        sort: sort?.field === key ? (sort.direction === "asc" ? "a" : "d") : null,
      };
      const jb = jsonb[key];
      if (jb && Object.keys(jb).length > 0) col.jsonb = jb;
      return col;
    });
    return { columns };
  }, [order, visibility, widths, sort, jsonb, toDisplayName, parseWidthNumber]);

  // Keep the JSON draft in sync with left-panel edits
  useEffect(() => {
    setConfigJsonDraft(JSON.stringify(configForDisplay, null, 2));
    setConfigJsonError("");
  }, [configForDisplay]);

  // Live preview: push changes to parent as user edits
  useEffect(() => {
    if (!open || !onPreview) return;
    onPreview(buildConfig);
  }, [open, onPreview, buildConfig]);

  const applyConfigDraft = useCallback(() => {
    try {
      const parsed = JSON.parse(configJsonDraft);
      if (!parsed?.columns || !Array.isArray(parsed.columns)) {
        setConfigJsonError("JSON must have a 'columns' array");
        return;
      }

      const newOrder: string[] = [];
      const newVis: Record<string, boolean> = {};
      const newWidths: Record<string, string> = {};
      const newJsonb: Record<string, Record<string, unknown>> = {};
      let newSort: ColumnSort | null = null;

      (parsed.columns as unknown[]).forEach((col, idx) => {
        const c = col as Record<string, unknown>;
        const fallbackByIndex = order[idx] ?? "";
        const key = toPersistKey(String(c.name ?? ""), fallbackByIndex);
        if (!key) return;
        newOrder.push(key);
        newVis[key] = c.visibility !== false;
        if (c.width != null) {
          const pixelValue = parseWidthNumber(c.width);
          newWidths[key] = String(Math.max(0, pixelValue));
        }
        if (c.sort === "a" || c.sort === "asc") newSort = { field: key, direction: "asc" };
        else if (c.sort === "d" || c.sort === "desc") newSort = { field: key, direction: "desc" };
        if (c.jsonb && typeof c.jsonb === "object" && !Array.isArray(c.jsonb))
          newJsonb[key] = c.jsonb as Record<string, unknown>;
      });

      setOrder(newOrder);
      setVisibility(newVis);
      setWidths(newWidths);
      setSort(newSort);
      setJsonb(newJsonb);
      setConfigJsonError("");
    } catch (err) {
      setConfigJsonError((err as Error).message);
    }
  }, [configJsonDraft, order, toPersistKey, parseWidthNumber]);

  const moveKey = useCallback((dragKey: string, dropKey: string) => {
    if (dragKey === dropKey) return;
    setOrder((prev) => {
      const dragIndex = prev.indexOf(dragKey);
      const dropIndex = prev.indexOf(dropKey);
      if (dragIndex < 0 || dropIndex < 0) return prev;
      const next = [...prev];
      next.splice(dragIndex, 1);
      next.splice(dropIndex, 0, dragKey);
      return next;
    });
  }, []);

  const handleSave = () => {
    const nextConfig = { order, visibility, widths, sort, jsonb };
    if (onSaveNamed && setupName.trim()) {
      onSaveNamed(setupName.trim(), nextConfig);
    }
    onSave(nextConfig);
    onClose();
  };

  const handleSaveNamedOnly = useCallback(() => {
    const trimmed = setupName.trim();
    if (!trimmed) {
      setNameError("Setup name is required");
      return;
    }
    const duplicate = existingSetupNames.includes(trimmed);
    const isRenamingDifferent =
      (initialSetupName ?? "").trim() !== "" && trimmed !== (initialSetupName ?? "").trim();
    if (duplicate && isRenamingDifferent) {
      const ok = window.confirm(`A setup named "${trimmed}" already exists. Overwrite it?`);
      if (!ok) return;
    }

    setNameError("");
    onSaveNamed?.(trimmed, { order, visibility, widths, sort, jsonb });
    setSelectedSetupName(trimmed);
    setSetupName(trimmed);
  }, [
    setupName,
    existingSetupNames,
    initialSetupName,
    onSaveNamed,
    order,
    visibility,
    widths,
    sort,
    jsonb,
  ]);

  if (!open) return null;

  const sortableKeys = order.filter((k) => visibility[k] !== false);

  const startDialogDrag = (e: React.MouseEvent<HTMLElement>) => {
    if ((e.target as HTMLElement).closest("button,input,select,textarea")) {
      return;
    }

    const rect = (e.currentTarget.parentElement as HTMLElement | null)?.getBoundingClientRect();
    if (!rect) return;

    setDragOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
    setIsDraggingDialog(true);
  };

  return (
    <div className="fixed inset-0 z-50 p-4 bg-slate-900/10 pointer-events-none">
      <div
        className="pointer-events-auto w-full max-w-4xl rounded-lg bg-white shadow-2xl dark:bg-slate-900 flex flex-col max-h-[88vh]"
        style={{
          position: "fixed",
          left: dialogPos.x < 0 ? "auto" : `${dialogPos.x}px`,
          right: dialogPos.x < 0 ? "16px" : "auto",
          top: dialogPos.y < 0 ? "auto" : `${dialogPos.y}px`,
          bottom: dialogPos.y < 0 ? "16px" : "auto",
          transform:
            dialogPos.x < 0 && dialogPos.y < 0
              ? "translate(0, 0)"
              : "translate(0, 0)",
          margin: 0,
        }}
      >
        {/* Header */}
        <header
          onMouseDown={startDialogDrag}
          className="flex items-center justify-between border-b border-slate-200 px-6 py-3 dark:border-slate-800 cursor-move"
          title="Drag dialog"
        >
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Edit Column Setup
            </p>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {title}
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="rounded-md bg-sky-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-sky-700"
            >
              Save
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 dark:hover:bg-slate-800"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </header>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
            <div className="space-y-4 lg:col-span-2">
              {/* Setup name + save */}
              <div>
                {namedSetups.length > 0 && (
                  <div className="mb-2 flex items-center gap-2">
                    <label className="text-xs font-medium text-slate-700 dark:text-slate-300 whitespace-nowrap">
                      Current
                    </label>
                    <select
                      value={selectedSetupName}
                      onChange={(e) => setSelectedSetupName(e.target.value)}
                      className="flex-1 text-xs px-2 py-1.5 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                    >
                      <option value="__current__">Current (unsaved)</option>
                      {namedSetups.map((setup) => (
                        <option key={setup.name} value={setup.name}>
                          {setup.name}
                        </option>
                      ))}
                    </select>
                    <label className="text-xs font-medium text-slate-700 dark:text-slate-300 whitespace-nowrap">
                      Sort
                    </label>
                    <select
                      value={sort?.field ?? ""}
                      onChange={(e) => {
                        const field = e.target.value;
                        if (!field) {
                          setSort(null);
                        } else {
                          setSort({ field, direction: sort?.direction ?? "asc" });
                        }
                      }}
                      className="flex-1 text-xs px-2 py-1.5 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                    >
                      <option value="">None</option>
                      {sortableKeys.map((key) => (
                        <option key={key} value={key}>
                          {labelFor(key)}
                        </option>
                      ))}
                    </select>
                    {sort && (
                      <button
                        type="button"
                        onClick={() =>
                          setSort({
                            ...sort,
                            direction: sort.direction === "asc" ? "desc" : "asc",
                          })
                        }
                        className="px-2 py-1.5 text-xs rounded border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                      >
                        {sort.direction === "asc" ? "↑" : "↓"}
                      </button>
                    )}
                  </div>
                )}
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Configuration Name
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={setupName}
                    onChange={(e) => {
                      setSetupName(e.target.value);
                      setNameError("");
                    }}
                    placeholder="e.g. customer_compact"
                    className="flex-1 text-xs px-2 py-1.5 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                  />
                  <button
                    type="button"
                    onClick={handleSaveNamedOnly}
                    className="rounded bg-slate-700 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-slate-800 dark:bg-slate-600 dark:hover:bg-slate-500"
                  >
                    Save Setup
                  </button>
                </div>
                {nameError && (
                  <p className="mt-1 text-[11px] text-red-600 dark:text-red-400">{nameError}</p>
                )}
              </div>

              {/* Column list */}
              <div>
                <h3 className="text-xs font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Columns (drag rows to reorder)
                </h3>
                <div className="border border-slate-200 dark:border-slate-700 rounded-md divide-y divide-slate-200 dark:divide-slate-700 max-h-[294px] overflow-y-auto">
                  {order.map((key, index) => {
                    const isVisible = visibility[key] !== false;
                    const isSelected = selectedKey === key;
                    return (
                      <div
                        key={key}
                        draggable
                        onDragStart={(e) => {
                          setDraggedKey(key);
                          e.dataTransfer.effectAllowed = "move";
                          e.dataTransfer.setData("text/plain", key);
                        }}
                        onDragOver={(e) => {
                          e.preventDefault();
                          e.dataTransfer.dropEffect = "move";
                        }}
                        onDrop={(e) => {
                          e.preventDefault();
                          if (draggedKey) {
                            moveKey(draggedKey, key);
                            setDraggedKey(null);
                          }
                        }}
                        onDragEnd={() => setDraggedKey(null)}
                        onClick={() => selectColumn(key)}
                        className={`flex cursor-pointer items-center gap-2 px-3 py-2 text-sm ${
                          isVisible ? "" : "opacity-50"
                        } ${
                          isSelected
                            ? "bg-sky-50 dark:bg-sky-900/20"
                            : "hover:bg-slate-50 dark:hover:bg-slate-800/40"
                        }`}
                      >
                        <span className="text-xs text-slate-400" title="Drag">
                          ==
                        </span>

                        <div className="flex flex-col gap-0.5">
                          <button
                            type="button"
                            disabled={index === 0}
                            onClick={(e) => {
                              e.stopPropagation();
                              moveItem(index, "up");
                            }}
                            className="text-[10px] leading-none text-slate-400 hover:text-slate-700 disabled:opacity-30 dark:hover:text-slate-200"
                          >
                            ▲
                          </button>
                          <button
                            type="button"
                            disabled={index === order.length - 1}
                            onClick={(e) => {
                              e.stopPropagation();
                              moveItem(index, "down");
                            }}
                            className="text-[10px] leading-none text-slate-400 hover:text-slate-700 disabled:opacity-30 dark:hover:text-slate-200"
                          >
                            ▼
                          </button>
                        </div>

                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setVisibility((prev) => ({
                              ...prev,
                              [key]: !isVisible,
                            }));
                          }}
                          className={`w-5 h-5 flex items-center justify-center rounded text-xs ${
                            isVisible
                              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                              : "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400"
                          }`}
                          title={isVisible ? "Hide" : "Show"}
                        >
                          {isVisible ? "on" : "off"}
                        </button>

                        <span className="flex-1 font-medium text-slate-800 dark:text-slate-200 truncate">
                          {labelFor(key)}
                        </span>

                        <div className="flex items-center gap-1">
                          <input
                            type="text"
                            value={widths[key] ?? ""}
                            onChange={(e) =>
                              setWidths((prev) => ({
                                ...prev,
                                [key]: String(Math.max(0, parseWidthNumber(e.target.value))),
                              }))
                            }
                            onClick={(e) => e.stopPropagation()}
                            placeholder="px"
                            className="w-14 text-xs px-1.5 py-1 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-right"
                            title="Width in pixels"
                          />
                          <span className="text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                            ({formatPercent(pixelsToPercent(parseWidthNumber(widths[key])))})
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Side panel */}
            <aside className="rounded-md border border-slate-200 bg-slate-50/60 p-3 dark:border-slate-700 dark:bg-slate-900/40 lg:col-span-3 flex flex-col">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Configuration JSON
                </h3>
                <button
                  type="button"
                  onClick={() => {
                    try {
                      const parsed = JSON.parse(configJsonDraft);
                      const cols = Array.isArray(parsed?.columns) ? parsed.columns : [];
                      cols.push({ name: "", visibility: true, width: "2", sort: null });
                      setConfigJsonDraft(JSON.stringify({ ...parsed, columns: cols }, null, 2));
                      setConfigJsonError("");
                    } catch {
                      // append to raw text as a fallback
                      const blank = `  {\n    "name": "",\n    "visibility": true,\n    "width": "100",\n    "sort": null\n  }`;
                      const trimmed = configJsonDraft.trimEnd();
                      // insert before closing ] of columns array if possible
                      const insertAt = trimmed.lastIndexOf("]");
                      if (insertAt >= 0) {
                        const before = trimmed.slice(0, insertAt).trimEnd();
                        const sep = before.endsWith("{") ? "\n" : ",\n";
                        setConfigJsonDraft(before + sep + blank + "\n]" + trimmed.slice(insertAt + 1));
                      }
                    }
                  }}
                  className="rounded bg-slate-200 px-2 py-0.5 text-[11px] font-medium text-slate-700 hover:bg-slate-300 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600"
                >
                  + Add
                </button>
              </div>
              <textarea
                value={configJsonDraft}
                onChange={(e) => {
                  setConfigJsonDraft(e.target.value);
                  setConfigJsonError("");
                }}
                rows={28}
                className="flex-1 w-full rounded border border-slate-200 bg-white p-2 font-mono text-[11px] text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 resize-y"
              />
              {configJsonError && (
                <p className="mt-1 text-[11px] text-red-600 dark:text-red-400">{configJsonError}</p>
              )}
              <button
                type="button"
                onClick={applyConfigDraft}
                className="mt-2 self-start rounded bg-slate-700 px-2 py-1 text-xs font-medium text-white hover:bg-slate-800 dark:bg-slate-600 dark:hover:bg-slate-500"
              >
                Apply JSON
              </button>
            </aside>
          </div>
        </div>

      </div>
    </div>
  );
};
