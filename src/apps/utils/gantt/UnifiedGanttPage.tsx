/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * UnifiedGanttPage - Full page wrapper for UnifiedGantt
 * 
 * Handles URL parameters for project selection and provides
 * the page layout with breadcrumb navigation.
 * 
 * URL Parameters:
 * - /gantt                    - Full page with project selector
 * - /gantt?project=123        - Pre-select single project
 * - /gantt?projects=123,456   - Pre-select multiple projects
 */

import { useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import { Link } from "react-router-dom";
import { UnifiedGantt } from "./UnifiedGantt";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

const UnifiedGanttPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  
  // Parse URL parameters
  const { projectId, initialProjectIds } = useMemo(() => {
    // Single project: ?project=123
    const singleProject = searchParams.get("project");
    if (singleProject) {
      return { projectId: singleProject, initialProjectIds: [] };
    }
    
    // Multiple projects: ?projects=123,456,789
    const multipleProjects = searchParams.get("projects");
    if (multipleProjects) {
      const ids = multipleProjects.split(",").map((id) => id.trim()).filter(Boolean);
      return { projectId: undefined, initialProjectIds: ids };
    }
    
    return { projectId: undefined, initialProjectIds: [] };
  }, [searchParams]);
  
  // Determine page title based on mode
  const pageTitle = projectId 
    ? "Project Gantt Chart" 
    : "Multi-Project Gantt";

  // Read font size from global prefs (same source as DataBrowser)
  const [baseFontSize] = useState(() => {
    try {
      const stored = localStorage.getItem('wc3_wcui_prefs');
      if (stored) { const p = JSON.parse(stored); if (p.font_size) return p.font_size; }
    } catch {}
    return 12;
  });

  // Listen for font size changes from the header dropdown
  // The header dispatches a storage event when prefs change
  const [fontSize, setFontSize] = useState(baseFontSize);
  useState(() => {
    const handler = () => {
      try {
        const stored = localStorage.getItem('wc3_wcui_prefs');
        if (stored) { const p = JSON.parse(stored); if (p.font_size) setFontSize(p.font_size); }
      } catch {}
    };
    window.addEventListener('storage', handler);
    // Also listen for custom wcui-prefs-changed event
    window.addEventListener('wcui-prefs-changed', handler);
    return () => { window.removeEventListener('storage', handler); window.removeEventListener('wcui-prefs-changed', handler); };
  });

  return (
    <div className="space-y-1 px-2 py-1" style={{ fontSize }}>
      <UnifiedGantt
        projectId={projectId}
        initialProjectIds={initialProjectIds}
        showSelector={!projectId}
        autoRefresh={true}
      />
    </div>
  );
};

export default withDevIdentifier(UnifiedGanttPage, 'UnifiedGanttPage', 'rose', 'apps/utils/gantt/UnifiedGanttPage.tsx');