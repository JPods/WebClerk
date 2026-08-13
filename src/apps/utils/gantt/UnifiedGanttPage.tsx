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

import { useEffect, useMemo, useState } from "react";
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

  // Font size — listen for wc3-font-size-changed from MacTopBar
  // Scale the entire Gantt proportionally using CSS zoom relative to base 12px
  const [fontSize, setFontSize] = useState(12);
  useEffect(() => {
    const handler = (e: Event) => {
      const size = (e as CustomEvent).detail?.size;
      if (size) setFontSize(size);
    };
    window.addEventListener('wc3-font-size-changed', handler);
    return () => window.removeEventListener('wc3-font-size-changed', handler);
  }, []);

  const scale = fontSize / 12;

  return (
    <div className="space-y-1 px-2 py-1 origin-top-left" style={{ transform: `scale(${scale})`, width: `${100 / scale}%` }}>
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