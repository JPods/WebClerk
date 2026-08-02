/**
 * Example: Minimal setup with EnhancedGantt
 *
 * This shows how to use the enhanced Gantt with your own data.
 * Works with any data source — your ERP, a REST API, a CSV, or WC3.
 *
 * For ERP integration: map your system's tasks to the ITask shape below.
 * The Gantt doesn't care where the data comes from — it just needs
 * id, text, start, end, and optionally priority/status/assignee.
 */
import { EnhancedGantt } from "./EnhancedGantt";
import { ProjectSelector } from "./ProjectSelector";
import type { ITask } from "@svar-ui/react-gantt";

// Your tasks — map from whatever source (ERP, database, API, CSV)
const tasks: ITask[] = [
  {
    id: "1",
    text: "Design review",
    start: new Date(2026, 6, 28),
    end: new Date(2026, 7, 1),
    progress: 60,
    // Enhanced fields (read by EnhancedTaskTemplate)
    priority: "high",
    status: "in_progress",
    assignee: "Jane Smith",
    assigneeId: "jane",
    percentComplete: 60,
  },
  {
    id: "2",
    text: "Build prototype",
    start: new Date(2026, 7, 1),
    end: new Date(2026, 7, 8),
    progress: 0,
    priority: "critical",
    status: "open",
    assignee: "Bob Chen",
    assigneeId: "bob",
    percentComplete: 0,
  },
  {
    id: "3",
    text: "Write documentation",
    start: new Date(2026, 7, 5),
    end: new Date(2026, 7, 12),
    progress: 25,
    priority: "medium",
    status: "active",
    assignee: "Jane Smith",
    assigneeId: "jane",
    percentComplete: 25,
  },
];

// Dependency links (optional)
const links = [
  { id: "l1", source: "1", target: "2", type: "e2s" }, // finish-to-start
];

// Projects with hierarchy (optional — for ProjectSelector)
const projects = [
  { id: "p1", name: "Q3 Launch", actionCount: 12 },
  { id: "p2", name: "Sprint 1: Design", id_parent: "p1", actionCount: 3 },
  { id: "p3", name: "Sprint 2: Build", id_parent: "p1", actionCount: 5 },
  { id: "p4", name: "Sprint 3: Ship", id_parent: "p1", actionCount: 4 },
];

export default function Example() {
  return (
    <div style={{ display: "flex", height: "100vh" }}>
      {/* Optional: project selector with cascade */}
      <div style={{ width: "240px", borderRight: "1px solid #e5e7eb" }}>
        <ProjectSelector
          projects={projects}
          selectedIds={["p1", "p2", "p3", "p4"]}
          onSelectionChange={(ids) => console.log("Selected:", ids)}
        />
      </div>

      {/* Gantt chart */}
      <div style={{ flex: 1 }}>
        <EnhancedGantt
          tasks={tasks}
          links={links}
          onTaskDoubleClick={(task) => console.log("Open detail:", task)}
        />
      </div>
    </div>
  );
}

/**
 * ERP Integration Pattern
 *
 * If your trading partners use SAP, Oracle, NetSuite, or any ERP:
 *
 * 1. Map their task/action format to ITask:
 *
 *    function mapERPTask(erpRecord: any): ITask {
 *      return {
 *        id: erpRecord.task_number,
 *        text: erpRecord.description,
 *        start: new Date(erpRecord.planned_start),
 *        end: new Date(erpRecord.planned_finish),
 *        progress: erpRecord.pct_complete,
 *        priority: mapPriority(erpRecord.priority_code),
 *        status: mapStatus(erpRecord.status_code),
 *        assignee: erpRecord.responsible_person,
 *      };
 *    }
 *
 * 2. Fetch via their API or through WC3 as a bridge:
 *
 *    // Direct from ERP
 *    const erpTasks = await fetch('/api/erp/tasks').then(r => r.json());
 *    const tasks = erpTasks.map(mapERPTask);
 *
 *    // Or through WC3 sync (ERP → WC3 Connection+Bundle → this Gantt)
 *    const wcTasks = await fetch('/wcapi/get/?model_name=action&project_ida=Q3').then(r => r.json());
 *    const tasks = wcTasks.results.map(mapWCAction);
 *
 * The Gantt doesn't care about the source. It renders whatever you give it.
 * WC3 as a bridge means: install WC3, sync from ERP via Connection+Bundle,
 * display in this Gantt. The ERP keeps its data. WC3 keeps a synced copy.
 * Users see a better UI. Trading partners share a common view.
 */
