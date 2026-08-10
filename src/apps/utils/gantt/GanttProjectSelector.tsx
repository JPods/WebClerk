/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * GanttProjectSelector - Multi-select project listbox for Gantt chart
 */

import React, { useState, useEffect, useMemo, useCallback } from "react";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

export interface ProjectPrefs {
  action?: {
    color?: string;  // Hex color for project tasks, e.g., "#3b82f6"
  };
  gantt?: {
    weight?: number; // 0=hidden, 1-2=low, 3=normal, 4-5=pinned
  };
}

export interface ProjectOption {
  id: string;
  name?: string;
  slug?: string;
  intent?: string;
  ida?: string;
  actionCount?: number;
  prefs?: ProjectPrefs;
  id_parent?: string | number | null;
  category?: string;
  dt_start?: number;
  dt_end?: number;
}

interface GanttPrefs {
  categories?: string[];
  byid?: number[];
}

interface GanttProjectSelectorProps {
  projects: ProjectOption[];
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  isLoading?: boolean;
  disabled?: boolean;
  ganttPrefs?: GanttPrefs;
  onSaveGanttPrefs?: (prefs: GanttPrefs) => void;
}

// Color palette for projects
const PROJECT_COLOR_PALETTE = [
  "#3b82f6", // blue-500
  "#10b981", // emerald-500
  "#f59e0b", // amber-500
  "#ef4444", // red-500
  "#8b5cf6", // violet-500
  "#ec4899", // pink-500
  "#06b6d4", // cyan-500
  "#84cc16", // lime-500
  "#f97316", // orange-500
  "#6366f1", // indigo-500
];

/**
 * Get the color for a project.
 * Priority: project.prefs.action.color > palette based on selection order
 */
export const getProjectColor = (
  projectId: string,
  selectedIds: string[],
  projectPrefsColor?: string
): string => {
  // Prefer explicitly set color from project.prefs.action.color
  if (projectPrefsColor && /^#[0-9A-Fa-f]{6}$/.test(projectPrefsColor)) {
    return projectPrefsColor;
  }
  // Fall back to palette based on selection order
  const index = selectedIds.indexOf(projectId);
  if (index === -1) return PROJECT_COLOR_PALETTE[0];
  return PROJECT_COLOR_PALETTE[index % PROJECT_COLOR_PALETTE.length];
};

/**
 * Get project color using full ProjectOption (convenience wrapper)
 */
export const getProjectColorFromOption = (
  project: ProjectOption,
  selectedIds: string[]
): string => {
  return getProjectColor(project.id, selectedIds, project.prefs?.action?.color);
};

export const GanttProjectSelector: React.FC<GanttProjectSelectorProps> = ({
  projects,
  selectedIds,
  onSelectionChange,
  isLoading = false,
  disabled = false,
  ganttPrefs,
  onSaveGanttPrefs,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  // If ganttPrefs not passed from Redux (stale login), fetch from current user
  const [fetchedPrefs, setFetchedPrefs] = useState<GanttPrefs | null>(null);
  useEffect(() => {
    if (!ganttPrefs?.categories?.length) {
      (async () => {
        try {
          const res = await fetch('/wcapi/me/');
          const json = await res.json();
          const me = json.data?.record || json.data || json;
          if (me?.prefs?.gantt) setFetchedPrefs(me.prefs.gantt);
        } catch { /* no prefs */ }
      })();
    }
  }, [ganttPrefs]);
  const effectivePrefs = ganttPrefs?.categories?.length ? ganttPrefs : (fetchedPrefs || ganttPrefs);
  const [showAllLevels, setShowAllLevels] = useState(() => {
    try {
      const stored = localStorage.getItem('wc3_wcui_prefs');
      if (stored) {
        const prefs = JSON.parse(stored);
        if (typeof prefs.gantt_show_all_levels === 'boolean') return prefs.gantt_show_all_levels;
      }
    } catch {}
    return false;
  });

  // Build dynamic gantt list from categories + byid
  const ganttListItems = useMemo(() => {
    const items: { label: string; ids: string[] }[] = [];
    const now = Date.now();
    const categories = effectivePrefs?.categories || [];
    const byid = effectivePrefs?.byid || [];

    for (const cat of categories) {
      const catProjects = projects
        .filter(p => p.category?.toLowerCase() === cat.toLowerCase() && p.dt_start && p.dt_end)
        .sort((a, b) => (a.dt_start || 0) - (b.dt_start || 0));

      const last = [...catProjects].reverse().find(p => (p.dt_end || 0) < now);
      const current = catProjects.find(p => (p.dt_start || 0) <= now && (p.dt_end || 0) >= now);
      const next = catProjects.find(p => (p.dt_start || 0) > now);

      const label = cat.toUpperCase();
      if (last) items.push({ label: `${label} — Last Sprint`, ids: [last.id] });
      if (current) items.push({ label: `${label} — Current Sprint`, ids: [current.id] });
      if (next) items.push({ label: `${label} — Next Sprint`, ids: [next.id] });
    }

    // byid — specific projects
    for (const id of byid) {
      const p = projects.find(proj => String(proj.id) === String(id));
      if (p) items.push({ label: p.name || p.ida || `#${id}`, ids: [p.id] });
    }

    return items;
  }, [projects, effectivePrefs]);

  const filteredProjects = useMemo(() => {
    let list = projects;
    // When collapsed, show only top-level projects (no parent)
    if (!showAllLevels) {
      list = list.filter((p) => p.id_parent == null);
    }
    if (!searchTerm.trim()) return list;
    const lower = searchTerm.toLowerCase();
    return list.filter(
      (p) =>
        p.name?.toLowerCase().includes(lower) ||
        p.slug?.toLowerCase().includes(lower) ||
        p.intent?.toLowerCase().includes(lower) ||
        p.id.includes(lower)
    );
  }, [projects, searchTerm, showAllLevels]);

  // Get all descendant project ids (children, grandchildren, etc.)
  const getDescendantIds = useCallback((parentId: string): string[] => {
    const descendants: string[] = [];
    const queue = [parentId];
    while (queue.length > 0) {
      const current = queue.shift()!;
      for (const p of projects) {
        if (String(p.id_parent) === current && !descendants.includes(p.id)) {
          descendants.push(p.id);
          queue.push(p.id);
        }
      }
    }
    return descendants;
  }, [projects]);

  const handleToggle = (id: string) => {
    if (disabled) return;
    const childIds = getDescendantIds(id);
    const idsToToggle = [id, ...childIds];

    if (selectedIds.includes(id)) {
      // Deselect parent and all children
      onSelectionChange(selectedIds.filter((sid) => !idsToToggle.includes(sid)));
    } else {
      // Select parent and all children
      const newIds = new Set([...selectedIds, ...idsToToggle]);
      onSelectionChange(Array.from(newIds));
    }
  };

  // Select all visible projects (+ descendants when in top-level mode)
  const handleSelectAll = () => {
    if (disabled) return;
    const visibleIds = filteredProjects.map((p) => p.id);
    const allSelected = visibleIds.every((id) => selectedIds.includes(id));
    if (allSelected) {
      // Deselect visible + their descendants
      const toRemove = new Set(visibleIds);
      if (!showAllLevels) {
        for (const id of visibleIds) {
          for (const d of getDescendantIds(id)) toRemove.add(d);
        }
      }
      onSelectionChange(selectedIds.filter((sid) => !toRemove.has(sid)));
    } else {
      // Select visible + their descendants
      const toAdd = new Set([...selectedIds, ...visibleIds]);
      if (!showAllLevels) {
        for (const id of visibleIds) {
          for (const d of getDescendantIds(id)) toAdd.add(d);
        }
      }
      onSelectionChange(Array.from(toAdd));
    }
  };

  const handleClear = () => {
    if (disabled) return;
    onSelectionChange([]);
  };

  const allFilteredSelected =
    filteredProjects.length > 0 &&
    filteredProjects.every((p) => selectedIds.includes(p.id));

  const hasHierarchy = projects.some((p) => p.id_parent != null);

  return (
    <div className="flex h-full flex-col rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-2 dark:border-gray-700">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            Projects
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {selectedIds.length} of {projects.length} selected
          </p>
        </div>
        <select
          className="rounded border border-gray-300 bg-white px-1 py-0.5 text-[10px] text-gray-600 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300"
          style={{ width: 80, maxWidth: '100%' }}
          title="Load a project set"
          value=""
          onChange={(e) => {
            const val = e.target.value;
            if (!val) return;
            if (val === '__save__') {
              // Add current selection as byid entries
              const currentByid = ganttPrefs?.byid || [];
              const newIds = selectedIds.map(Number).filter(n => !isNaN(n) && !currentByid.includes(n));
              if (newIds.length === 0) return;
              onSaveGanttPrefs?.({ ...ganttPrefs, byid: [...currentByid, ...newIds] });
              return;
            }
            const idx = Number(val);
            if (!isNaN(idx) && ganttListItems[idx]) {
              onSelectionChange(ganttListItems[idx].ids);
            }
          }}
        >
          <option value="">My Sprints...</option>
          {ganttListItems.map((item, i) => (
            <option key={i} value={i}>{item.label}</option>
          ))}
          {ganttListItems.length > 0 && <option disabled>───</option>}
          <option value="__save__">Add Current to My List...</option>
        </select>
      </div>

      {/* Search */}
      <div className="border-b border-gray-200 px-3 py-2 dark:border-gray-700">
        <input
          type="text"
          placeholder="Search projects..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          disabled={disabled || isLoading}
          className="w-full rounded-lg border border-gray-300 bg-gray-50 px-3 py-1.5 text-sm text-gray-900 placeholder-gray-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder-gray-500"
        />
      </div>

      {/* Action buttons — minimal style matching DataBrowser toolbars */}
      <div className="flex items-center gap-1 border-b border-gray-200 px-3 py-1 dark:border-gray-700" style={{ fontSize: 12, color: '#9cdcfe' }}>
        <button type="button" onClick={handleSelectAll}
          disabled={disabled || isLoading || filteredProjects.length === 0}
          style={{ padding: '4px 8px', border: '1px solid transparent', borderRadius: 4, background: 'transparent', cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.4 : 1, fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', color: '#9cdcfe' }}
        >📋 {allFilteredSelected ? "Deselect" : "Select All"}</button>
        <button type="button" onClick={handleClear}
          disabled={disabled || isLoading || selectedIds.length === 0}
          style={{ padding: '4px 8px', border: '1px solid transparent', borderRadius: 4, background: 'transparent', cursor: disabled ? 'default' : 'pointer', opacity: (disabled || selectedIds.length === 0) ? 0.4 : 1, fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', color: '#9cdcfe' }}
        >✕ Clear</button>
        {hasHierarchy && (
          <button type="button"
            onClick={() => {
              const next = !showAllLevels;
              setShowAllLevels(next);
              try {
                const stored = localStorage.getItem('wc3_wcui_prefs');
                const prefs = stored ? JSON.parse(stored) : {};
                prefs.gantt_show_all_levels = next;
                localStorage.setItem('wc3_wcui_prefs', JSON.stringify(prefs));
              } catch {}
            }}
            disabled={disabled || isLoading}
            style={{ padding: '4px 8px', border: '1px solid transparent', borderRadius: 4, background: 'transparent', cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.4 : 1, fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', color: '#9cdcfe' }}
          >{showAllLevels ? "▴ Top Only" : "▾ Sub-Projects"}</button>
        )}
      </div>

      {/* Project list */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" />
          </div>
        ) : filteredProjects.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
            {searchTerm ? "No projects match your search" : "No projects available"}
          </div>
        ) : (
          <ul className="divide-y divide-gray-100 dark:divide-gray-800">
            {filteredProjects.map((project) => {
              const isSelected = selectedIds.includes(project.id);
              // Use project.prefs.action.color if available, otherwise use palette color
              const color = isSelected
                ? getProjectColor(project.id, selectedIds, project.prefs?.action?.color)
                : undefined;

              const isChild = project.id_parent != null;
              const hasChildren = projects.some(p => String(p.id_parent) === project.id);

              return (
                <li key={project.id}>
                  <button
                    type="button"
                    onClick={(e) => {
                      if (e.shiftKey) {
                        // Shift-click → open Kanban for this project in new window
                        window.open(`/kanban-board?project=${project.id}`, '_blank');
                        return;
                      }
                      handleToggle(project.id);
                    }}
                    disabled={disabled}
                    className="flex w-full items-center gap-3 py-2.5 text-left transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:hover:bg-gray-800"
                    style={{ paddingLeft: isChild ? '28px' : '16px', paddingRight: '16px' }}
                    title="Click to select · Shift-click to open Kanban"
                  >
                    {/* Checkbox */}
                    <div
                      className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border transition ${
                        isSelected
                          ? "border-transparent"
                          : "border-gray-300 bg-white dark:border-gray-600 dark:bg-gray-800"
                      }`}
                      style={isSelected ? { backgroundColor: color } : undefined}
                    >
                      {isSelected && (
                        <svg
                          className="h-3 w-3 text-white"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth={3}
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M5 13l4 4L19 7"
                          />
                        </svg>
                      )}
                    </div>

                    {/* Project info */}
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium text-gray-900 dark:text-white">
                        {hasChildren && <span className="mr-1 text-xs text-gray-400">▸</span>}
                        {isChild && <span className="mr-1 text-xs text-gray-400">└</span>}
                        {project.name || project.intent || `Project ${project.id}`}
                      </div>
                      {project.slug && (
                        <div className="truncate text-xs text-gray-500 dark:text-gray-400">
                          {project.slug}
                        </div>
                      )}
                    </div>

                    {/* Action count badge */}
                    {project.actionCount !== undefined && (
                      <span className="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                        {project.actionCount}
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
};

export default withDevIdentifier(GanttProjectSelector, 'GanttProjectSelector', 'rose', 'apps/utils/gantt/GanttProjectSelector.tsx');