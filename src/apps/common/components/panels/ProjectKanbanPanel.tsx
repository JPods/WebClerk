/**
 * ProjectKanbanPanel — Kanban board for projects linked to a contact.
 *
 * Columns = project status: draft → active → onhold/blocked → done/canceled
 * Cards = project records where id_contact = this contact
 * Drag to change status. Click to open in DataBrowser.
 *
 * Lightweight — not the full KanbanBoardPage. Designed to embed in
 * contact detail tabs.
 *
 * LastChecked: 2026-08-05 | WhereUsed: ContactDetailJson tabs | WhoCreated: Bill+Claude
 */
import React, { useState, useEffect, useCallback } from 'react';
import { DndProvider, useDrag, useDrop } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { getRecords, saveRecord } from '@/api/wcapi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Project {
  id: number;
  ida: string;
  name: string;
  status: string;
  attention: string;
  priority: number;
  percent_complete: number;
  dt_start: number;
  dt_end: number;
  dt_kanban: string;
  intent: string;
  category: string;
}

interface ProjectKanbanPanelProps {
  contactId: number;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const COLUMNS = [
  { key: 'draft', label: 'Draft', color: '#6b7280' },
  { key: 'active', label: 'Active', color: '#2563eb' },
  { key: 'onhold', label: 'On Hold', color: '#d97706' },
  { key: 'blocked', label: 'Blocked', color: '#dc2626' },
  { key: 'done', label: 'Done', color: '#16a34a' },
  { key: 'canceled', label: 'Canceled', color: '#9ca3af' },
];

const ATTENTION_COLORS: Record<string, string> = {
  low: '#6b7280',
  normal: '#3b82f6',
  high: '#f59e0b',
  critical: '#ef4444',
};

const DRAG_TYPE = 'PROJECT_CARD';

// ---------------------------------------------------------------------------
// Card
// ---------------------------------------------------------------------------

function ProjectCard({ project, onStatusChange }: { project: Project; onStatusChange: (id: number, status: string) => void }) {
  const [{ isDragging }, drag] = useDrag({
    type: DRAG_TYPE,
    item: { id: project.id, status: project.status },
    collect: (monitor) => ({ isDragging: monitor.isDragging() }),
  });

  const pctColor = project.percent_complete >= 80 ? '#4ade80'
    : project.percent_complete >= 40 ? '#fbbf24' : '#888';

  return (
    <div
      ref={drag}
      style={{
        padding: '8px 10px', marginBottom: 6, borderRadius: 6,
        background: '#2a2a3a', border: '1px solid #3a3a4a',
        cursor: 'grab', opacity: isDragging ? 0.4 : 1,
        borderLeft: `3px solid ${ATTENTION_COLORS[project.attention] || '#3b82f6'}`,
      }}
      onDoubleClick={() => window.open(`/project?search=${encodeURIComponent(project.name)}`, '_blank')}
      title="Double-click to open in DataBrowser"
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 600, fontSize: 12, color: '#ddd' }}>{project.name}</span>
        <span style={{ fontSize: 10, color: pctColor, fontWeight: 600 }}>{project.percent_complete}%</span>
      </div>
      {project.intent && (
        <div style={{ fontSize: 11, color: '#888', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {project.intent}
        </div>
      )}
      <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
        {project.category && (
          <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3, background: '#3a3a4a', color: '#999' }}>
            {project.category}
          </span>
        )}
        {project.attention && project.attention !== 'normal' && (
          <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3, background: ATTENTION_COLORS[project.attention] + '22', color: ATTENTION_COLORS[project.attention] }}>
            {project.attention}
          </span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Column
// ---------------------------------------------------------------------------

function KanbanCol({ colKey, label, color, projects, onDrop }: {
  colKey: string; label: string; color: string;
  projects: Project[];
  onDrop: (projectId: number, newStatus: string) => void;
}) {
  const [{ isOver }, drop] = useDrop({
    accept: DRAG_TYPE,
    drop: (item: { id: number }) => onDrop(item.id, colKey),
    collect: (monitor) => ({ isOver: monitor.isOver() }),
  });

  return (
    <div
      ref={drop}
      style={{
        flex: 1, minWidth: 140,
        background: isOver ? 'rgba(37,99,235,0.08)' : 'transparent',
        borderRadius: 6, padding: 6,
        transition: 'background 0.15s',
      }}
    >
      <div style={{
        fontSize: 11, fontWeight: 700, color, textTransform: 'uppercase',
        padding: '4px 6px', marginBottom: 6, borderBottom: `2px solid ${color}33`,
        display: 'flex', justifyContent: 'space-between',
      }}>
        <span>{label}</span>
        <span style={{ color: '#666' }}>{projects.length}</span>
      </div>
      {projects.map(p => (
        <ProjectCard key={p.id} project={p} onStatusChange={onDrop} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Panel
// ---------------------------------------------------------------------------

export default function ProjectKanbanPanel({ contactId }: ProjectKanbanPanelProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchProjects = useCallback(async () => {
    try {
      const res = await getRecords('project', { id_contact: contactId, is_active: true });
      const rows = res?.results || res?.records || res?.data?.results || [];
      setProjects(rows);
    } catch (e) {
      console.error('[ProjectKanbanPanel] fetch failed:', e);
    } finally {
      setLoading(false);
    }
  }, [contactId]);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  const handleDrop = useCallback(async (projectId: number, newStatus: string) => {
    // Optimistic update
    setProjects(prev => prev.map(p => p.id === projectId ? { ...p, status: newStatus } : p));
    try {
      await saveRecord('project', { id: projectId, status: newStatus });
    } catch {
      fetchProjects(); // revert on failure
    }
  }, [fetchProjects]);

  if (loading) return <div style={{ padding: 16, color: '#888', fontSize: 12 }}>Loading projects...</div>;
  if (projects.length === 0) return <div style={{ padding: 16, color: '#666', fontSize: 12, textAlign: 'center' }}>No projects for this contact</div>;

  return (
    <DndProvider backend={HTML5Backend}>
      <div style={{ display: 'flex', gap: 4, overflowX: 'auto', padding: '4px 0', minHeight: 200 }}>
        {COLUMNS.map(col => (
          <KanbanCol
            key={col.key}
            colKey={col.key}
            label={col.label}
            color={col.color}
            projects={projects.filter(p => p.status === col.key)}
            onDrop={handleDrop}
          />
        ))}
      </div>
    </DndProvider>
  );
}
