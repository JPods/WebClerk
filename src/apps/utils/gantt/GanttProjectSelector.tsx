import { ChangeEvent, useCallback, useMemo, useState } from "react";

export interface ProjectOption {
  id: string;
  name: string;
  slug?: string;
  intent?: string;
  actionCount?: number;
  color?: string;
}

interface GanttProjectSelectorProps {
  projects: ProjectOption[];
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  isLoading: boolean;
  disabled?: boolean;
}

const PROJECT_COLOR_PALETTE = [
  "#3b82f6", // blue
  "#10b981", // emerald
  "#f59e0b", // amber
  "#8b5cf6", // violet
  "#ef4444", // red
  "#06b6d4", // cyan
  "#f97316", // orange
  "#84cc16", // lime
  "#ec4899", // pink
  "#14b8a6", // teal
];

export const getProjectColor = (projectId: string, selectedIds: string[]): string => {
  const index = selectedIds.indexOf(projectId);
  if (index === -1) {
    return PROJECT_COLOR_PALETTE[0];
  }
  return PROJECT_COLOR_PALETTE[index % PROJECT_COLOR_PALETTE.length];
};

export const GanttProjectSelector: React.FC<GanttProjectSelectorProps> = ({
  projects,
  selectedIds,
  onSelectionChange,
  isLoading,
  disabled = false,
}) => {
  const [searchTerm, setSearchTerm] = useState("");

  const filteredProjects = useMemo(() => {
    if (!searchTerm.trim()) {
      return projects;
    }
    const normalizedSearch = searchTerm.toLowerCase().trim();
    return projects.filter((project) => {
      const searchableText = [project.name, project.slug, project.intent]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return searchableText.includes(normalizedSearch);
    });
  }, [projects, searchTerm]);

  const handleSearchChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
  }, []);

  const handleToggleProject = useCallback(
    (projectId: string) => {
      if (disabled) return;
      
      const isSelected = selectedIds.includes(projectId);
      if (isSelected) {
        onSelectionChange(selectedIds.filter((id) => id !== projectId));
      } else {
        onSelectionChange([...selectedIds, projectId]);
      }
    },
    [selectedIds, onSelectionChange, disabled]
  );

  const handleSelectAll = useCallback(() => {
    if (disabled) return;
    const allVisibleIds = filteredProjects.map((p) => p.id);
    const merged = new Set([...selectedIds, ...allVisibleIds]);
    onSelectionChange(Array.from(merged));
  }, [filteredProjects, selectedIds, onSelectionChange, disabled]);

  const handleClearAll = useCallback(() => {
    if (disabled) return;
    if (searchTerm.trim()) {
      // Only clear filtered projects
      const filteredIds = new Set(filteredProjects.map((p) => p.id));
      onSelectionChange(selectedIds.filter((id) => !filteredIds.has(id)));
    } else {
      onSelectionChange([]);
    }
  }, [filteredProjects, selectedIds, onSelectionChange, searchTerm, disabled]);

  const selectedCount = selectedIds.length;
  const visibleSelectedCount = filteredProjects.filter((p) => selectedIds.includes(p.id)).length;

  return (
    <div className="flex h-full flex-col rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-900">
      {/* Header */}
      <div className="border-b border-gray-200 px-4 py-3 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            Projects
          </h3>
          <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300">
            {selectedCount} selected
          </span>
        </div>
      </div>

      {/* Search */}
      <div className="border-b border-gray-200 px-3 py-2 dark:border-gray-700">
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            value={searchTerm}
            onChange={handleSearchChange}
            placeholder="Search projects..."
            disabled={disabled || isLoading}
            className="w-full rounded-lg border border-gray-200 bg-gray-50 py-2 pl-10 pr-3 text-sm text-gray-900 placeholder-gray-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder-gray-500"
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 border-b border-gray-200 px-3 py-2 dark:border-gray-700">
        <button
          type="button"
          onClick={handleSelectAll}
          disabled={disabled || isLoading || filteredProjects.length === 0}
          className="flex-1 rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
        >
          Select All
        </button>
        <button
          type="button"
          onClick={handleClearAll}
          disabled={disabled || isLoading || selectedCount === 0}
          className="flex-1 rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
        >
          Clear{searchTerm.trim() ? " Visible" : ""}
        </button>
      </div>

      {/* Project List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="space-y-2 p-3">
            {Array.from({ length: 5 }).map((_, index) => (
              <div
                key={index}
                className="h-10 animate-pulse rounded-lg bg-gray-100 dark:bg-gray-800"
              />
            ))}
          </div>
        ) : filteredProjects.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-6 text-center">
            <svg
              className="mb-2 h-8 w-8 text-gray-300 dark:text-gray-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {searchTerm.trim() ? "No matching projects" : "No active projects"}
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-100 dark:divide-gray-800">
            {filteredProjects.map((project) => {
              const isSelected = selectedIds.includes(project.id);
              const projectColor = isSelected
                ? getProjectColor(project.id, selectedIds)
                : undefined;

              return (
                <li key={project.id}>
                  <button
                    type="button"
                    onClick={() => handleToggleProject(project.id)}
                    disabled={disabled}
                    className={`flex w-full items-center gap-3 px-3 py-2.5 text-left transition hover:bg-gray-50 disabled:cursor-not-allowed dark:hover:bg-gray-800 ${
                      isSelected ? "bg-indigo-50/50 dark:bg-indigo-500/10" : ""
                    }`}
                  >
                    {/* Checkbox */}
                    <div
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 transition ${
                        isSelected
                          ? "border-indigo-600 bg-indigo-600 dark:border-indigo-500 dark:bg-indigo-500"
                          : "border-gray-300 bg-white dark:border-gray-600 dark:bg-gray-800"
                      }`}
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

                    {/* Color indicator */}
                    {isSelected && projectColor && (
                      <div
                        className="h-3 w-3 shrink-0 rounded-full"
                        style={{ backgroundColor: projectColor }}
                      />
                    )}

                    {/* Project info */}
                    <div className="min-w-0 flex-1">
                      <p
                        className={`truncate text-sm font-medium ${
                          isSelected
                            ? "text-indigo-900 dark:text-indigo-100"
                            : "text-gray-900 dark:text-white"
                        }`}
                      >
                        {project.name || project.intent || `Project ${project.id}`}
                      </p>
                      {project.slug && (
                        <p className="truncate text-xs text-gray-500 dark:text-gray-400">
                          {project.slug}
                        </p>
                      )}
                    </div>

                    {/* Action count badge */}
                    {typeof project.actionCount === "number" && (
                      <span
                        className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                          isSelected
                            ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-500/30 dark:text-indigo-200"
                            : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300"
                        }`}
                      >
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

      {/* Footer */}
      {visibleSelectedCount > 0 && visibleSelectedCount !== filteredProjects.length && (
        <div className="border-t border-gray-200 px-3 py-2 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {visibleSelectedCount} of {filteredProjects.length} visible projects selected
          </p>
        </div>
      )}
    </div>
  );
};

export default GanttProjectSelector;
