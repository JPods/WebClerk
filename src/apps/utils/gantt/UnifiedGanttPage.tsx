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

import { useMemo } from "react";
import { useSearchParams } from "react-router";
import PageBreadcrumb from "../../../components/common/PageBreadCrumb";
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

  return (
    <div className="space-y-4 px-4 py-3 md:px-5 lg:px-6">
      <PageBreadcrumb pageTitle={pageTitle} />
      
      <UnifiedGantt
        projectId={projectId}
        initialProjectIds={initialProjectIds}
        showSelector={!projectId}
        autoRefresh={true}
      />
    </div>
  );
};

export default withDevIdentifier(UnifiedGanttPage, 'UnifiedGanttPage');