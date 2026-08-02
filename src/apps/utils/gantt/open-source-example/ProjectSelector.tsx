/**
 * ProjectSelector — Multi-select project list with hierarchy and cascade selection
 *
 * Click a parent project to select/deselect all its descendants.
 * Visual indicators: ▸ for parents, └ for children, indented.
 *
 * MIT License — https://github.com/webclerk/gantt-enhancements
 */
import { FC, useState, useMemo, useCallback } from "react";

export interface ProjectOption {
  id: string;
  name: string;
  id_parent?: string | number | null;
  actionCount?: number;
  color?: string;
}

interface ProjectSelectorProps {
  projects: ProjectOption[];
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  disabled?: boolean;
}

// Color palette for projects without explicit colors
const PALETTE = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
  "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16",
];

export const getProjectColor = (id: string, selectedIds: string[], explicit?: string): string => {
  if (explicit) return explicit;
  const idx = selectedIds.indexOf(id);
  return PALETTE[(idx === -1 ? 0 : idx) % PALETTE.length];
};

export const ProjectSelector: FC<ProjectSelectorProps> = ({
  projects, selectedIds, onSelectionChange, disabled = false,
}) => {
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim()) return projects;
    const lower = search.toLowerCase();
    return projects.filter(p => p.name.toLowerCase().includes(lower));
  }, [projects, search]);

  // Walk the tree to find all descendants
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
      onSelectionChange(selectedIds.filter(sid => !idsToToggle.includes(sid)));
    } else {
      onSelectionChange([...new Set([...selectedIds, ...idsToToggle])]);
    }
  };

  return (
    <div style={{
      display: "flex", flexDirection: "column", height: "100%",
      border: "1px solid #e5e7eb", borderRadius: "8px", overflow: "hidden",
      fontSize: "13px",
    }}>
      {/* Header */}
      <div style={{ padding: "8px 12px", borderBottom: "1px solid #e5e7eb" }}>
        <div style={{ fontWeight: 600 }}>Projects</div>
        <div style={{ fontSize: "11px", color: "#6b7280" }}>
          {selectedIds.length} of {projects.length} selected
        </div>
      </div>

      {/* Search */}
      <div style={{ padding: "6px 8px", borderBottom: "1px solid #e5e7eb" }}>
        <input
          type="text"
          placeholder="Search..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            width: "100%", padding: "4px 8px", borderRadius: "4px",
            border: "1px solid #d1d5db", fontSize: "12px",
          }}
        />
      </div>

      {/* List */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {filtered.map(project => {
          const isSelected = selectedIds.includes(project.id);
          const isChild = project.id_parent != null;
          const hasChildren = projects.some(p => String(p.id_parent) === project.id);
          const color = isSelected ? getProjectColor(project.id, selectedIds, project.color) : undefined;

          return (
            <button
              key={project.id}
              onClick={() => handleToggle(project.id)}
              disabled={disabled}
              style={{
                display: "flex", alignItems: "center", gap: "8px",
                width: "100%", border: "none", background: "none",
                padding: "6px 12px", paddingLeft: isChild ? "28px" : "12px",
                cursor: disabled ? "not-allowed" : "pointer",
                textAlign: "left", borderBottom: "1px solid #f3f4f6",
              }}
            >
              {/* Checkbox */}
              <div style={{
                width: "14px", height: "14px", borderRadius: "3px", flexShrink: 0,
                border: isSelected ? "none" : "1px solid #d1d5db",
                backgroundColor: isSelected ? color : "white",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                {isSelected && (
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3">
                    <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </div>

              {/* Name */}
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {hasChildren && <span style={{ color: "#9ca3af", marginRight: "4px" }}>▸</span>}
                {isChild && <span style={{ color: "#9ca3af", marginRight: "4px" }}>└</span>}
                {project.name}
              </span>

              {/* Count */}
              {project.actionCount !== undefined && (
                <span style={{
                  fontSize: "11px", color: "#6b7280",
                  background: "#f3f4f6", borderRadius: "8px", padding: "1px 6px",
                }}>
                  {project.actionCount}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default ProjectSelector;
