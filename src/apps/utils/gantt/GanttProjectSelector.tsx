/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * GanttProjectSelector - Multi-select project listbox for Gantt chart
 */

import React, { useState, useMemo } from "react";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

export interface ProjectPrefs {
  action?: {
    color?: string;  // Hex color for project tasks, e.g., "#3b82f6"
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
}

interface GanttProjectSelectorProps {
  projects: ProjectOption[];
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  isLoading?: boolean;
  disabled?: boolean;
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
}) => {
  const [searchTerm, setSearchTerm] = useState("");

  const filteredProjects = useMemo(() => {
    if (!searchTerm.trim()) return projects;
    const lower = searchTerm.toLowerCase();
    return projects.filter(
      (p) =>
        p.name?.toLowerCase().includes(lower) ||
        p.slug?.toLowerCase().includes(lower) ||
        p.intent?.toLowerCase().includes(lower) ||
        p.id.includes(lower)
    );
  }, [projects, searchTerm]);

  const handleToggle = (id: string) => {
    if (disabled) return;
    if (selectedIds.includes(id)) {
      onSelectionChange(selectedIds.filter((sid) => sid !== id));
    } else {
      onSelectionChange([...selectedIds, id]);
    }
  };

  const handleSelectAll = () => {
    if (disabled) return;
    const filteredIds = filteredProjects.map((p) => p.id);
    const allSelected = filteredIds.every((id) => selectedIds.includes(id));
    if (allSelected) {
      // Deselect all filtered
      onSelectionChange(selectedIds.filter((id) => !filteredIds.includes(id)));
    } else {
      // Select all filtered
      const newIds = new Set([...selectedIds, ...filteredIds]);
      onSelectionChange(Array.from(newIds));
    }
  };

  const handleClear = () => {
    if (disabled) return;
    onSelectionChange([]);
  };

  const allFilteredSelected =
    filteredProjects.length > 0 &&
    filteredProjects.every((p) => selectedIds.includes(p.id));

  return (
    <div className="flex h-full flex-col rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-900">
      {/* Header */}
      <div className="border-b border-gray-200 px-4 py-3 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
          Projects
        </h3>
        <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
          {selectedIds.length} of {projects.length} selected
        </p>
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

      {/* Action buttons */}
      <div className="flex gap-2 border-b border-gray-200 px-3 py-2 dark:border-gray-700">
        <button
          type="button"
          onClick={handleSelectAll}
          disabled={disabled || isLoading || filteredProjects.length === 0}
          className="flex-1 rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-700 transition hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
        >
          {allFilteredSelected ? "Deselect All" : "Select All"}
        </button>
        <button
          type="button"
          onClick={handleClear}
          disabled={disabled || isLoading || selectedIds.length === 0}
          className="flex-1 rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-700 transition hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
        >
          Clear
        </button>
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

              return (
                <li key={project.id}>
                  <button
                    type="button"
                    onClick={() => handleToggle(project.id)}
                    disabled={disabled}
                    className="flex w-full items-center gap-3 px-4 py-2.5 text-left transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:hover:bg-gray-800"
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

export default withDevIdentifier(GanttProjectSelector, 'GanttProjectSelector');