import { useState, useMemo, useCallback } from "react";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import { KanbanTask, TaskPriority } from "../../type/kanban";
import clsx from "clsx";

// Sample data for Gantt chart based on Kanban tasks
const ganttTasks: KanbanTask[] = [
  {
    id: "task-1",
    title: "Persona maps & discovery notes",
    description: "Synthesize user interviews into actionable personas for the growth epic.",
    priority: "high",
    assignee: "Maya Patel",
    dueDate: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString(),
    tags: ["Discovery", "Research"],
    progress: 35,
    children: [
      { id: "task-1-1", name: "Conduct user interviews" },
      { id: "task-1-2", name: "Create persona templates" }
    ]
  },
  {
    id: "task-1-1",
    title: "Conduct user interviews",
    description: "Schedule and conduct interviews with 5-8 target users",
    priority: "medium",
    assignee: "Maya Patel",
    dueDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
    tags: ["Research"],
    progress: 80,
  },
  {
    id: "task-1-2",
    title: "Create persona templates",
    description: "Design reusable persona templates based on research findings",
    priority: "medium",
    assignee: "Maya Patel",
    dueDate: new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString(),
    tags: ["Design"],
    progress: 20,
  },
  {
    id: "task-2",
    title: "Backend contract for v2 API",
    description: "Define request/response schema and agree on pagination strategy with backend team.",
    priority: "critical",
    assignee: "Colin Rivera",
    dueDate: new Date(Date.now() + 21 * 24 * 60 * 60 * 1000).toISOString(),
    tags: ["API", "Backend"],
    progress: 10,
  },
  {
    id: "task-3",
    title: "Visual design refresh",
    description: "Update typography scale and audit existing color usage to match new design tokens.",
    priority: "medium",
    assignee: "Akari Watanabe",
    dueDate: new Date(Date.now() + 28 * 24 * 60 * 60 * 1000).toISOString(),
    tags: ["Design", "UI"],
    progress: 55,
  },
  {
    id: "task-4",
    title: "QA regression suite",
    description: "Automate the top ten revenue-critical flows in Playwright.",
    priority: "high",
    assignee: "Enzo García",
    dueDate: new Date(Date.now() + 35 * 24 * 60 * 60 * 1000).toISOString(),
    tags: ["QA", "Automation"],
    progress: 20,
  }
];

const priorityColors: Record<TaskPriority, string> = {
  low: "bg-emerald-500",
  medium: "bg-amber-500",
  high: "bg-orange-500",
  critical: "bg-rose-500",
};

const priorityBgColors: Record<TaskPriority, string> = {
  low: "bg-emerald-50 border-emerald-200 dark:bg-emerald-500/10 dark:border-emerald-500/20",
  medium: "bg-amber-50 border-amber-200 dark:bg-amber-500/10 dark:border-amber-500/20",
  high: "bg-orange-50 border-orange-200 dark:bg-orange-500/10 dark:border-orange-500/20",
  critical: "bg-rose-50 border-rose-200 dark:bg-rose-500/10 dark:border-rose-500/20",
};

interface GanttDateRange {
  start: Date;
  end: Date;
}

interface GanttBarProps {
  task: KanbanTask;
  dateRange: GanttDateRange;
  isSubtask?: boolean;
}

const GanttBar: React.FC<GanttBarProps> = ({ task, dateRange, isSubtask = false }) => {
  const taskStart = new Date();
  const taskEnd = task.dueDate ? new Date(task.dueDate) : new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
  
  const totalDays = Math.ceil((dateRange.end.getTime() - dateRange.start.getTime()) / (1000 * 60 * 60 * 24));
  const startOffset = Math.ceil((taskStart.getTime() - dateRange.start.getTime()) / (1000 * 60 * 60 * 24));
  const duration = Math.ceil((taskEnd.getTime() - taskStart.getTime()) / (1000 * 60 * 60 * 24));
  
  const leftPercentage = (startOffset / totalDays) * 100;
  const widthPercentage = (duration / totalDays) * 100;

  const isOverdue = taskEnd < new Date() && (task.progress || 0) < 100;
  const isCritical = task.priority === 'critical';
  const isCompleted = (task.progress || 0) >= 100;

  return (
    <div 
      className="relative h-10 rounded-lg shadow-sm transition-all hover:shadow-md group"
      style={{
        left: `${Math.max(0, leftPercentage)}%`,
        width: `${Math.max(8, Math.min(widthPercentage, 100 - leftPercentage))}%`,
      }}
    >
      <div className={clsx(
        "h-full rounded-lg border-2 relative overflow-hidden transition-all",
        {
          [priorityBgColors[task.priority]]: !isOverdue && !isCompleted,
          "bg-rose-100 border-rose-300 dark:bg-rose-500/20 dark:border-rose-500/40": isOverdue,
          "bg-emerald-100 border-emerald-300 dark:bg-emerald-500/20 dark:border-emerald-500/40": isCompleted,
          "h-8 ml-4": isSubtask,
          "ring-2 ring-orange-400 ring-opacity-50": isCritical,
        }
      )}>
        {/* Progress bar */}
        <div 
          className={clsx(
            "h-full rounded-md transition-all",
            {
              [priorityColors[task.priority]]: !isOverdue && !isCompleted,
              "bg-rose-500": isOverdue,
              "bg-emerald-500": isCompleted,
            }
          )}
          style={{ width: `${task.progress || 0}%` }}
        />
        
        {/* Task title overlay */}
        <div className="absolute inset-0 flex items-center justify-between px-3">
          <span className={clsx(
            "text-sm font-medium truncate flex-1",
            task.progress && task.progress > 50 ? "text-white" : "text-gray-700 dark:text-gray-300",
            isSubtask && "text-xs"
          )}>
            {task.title}
          </span>
          
          {/* Status indicators */}
          <div className="flex items-center gap-1 ml-2">
            {isCompleted && (
              <svg className="h-3 w-3 text-white" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            )}
            {isOverdue && (
              <svg className="h-3 w-3 text-white" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            )}
          </div>
        </div>

        {/* Hover tooltip */}
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 whitespace-nowrap">
          <div className="font-medium">{task.title}</div>
          <div className="text-gray-300">Progress: {task.progress || 0}%</div>
          <div className="text-gray-300">Due: {taskEnd.toLocaleDateString()}</div>
          {task.assignee && <div className="text-gray-300">Assignee: {task.assignee}</div>}
        </div>
      </div>
    </div>
  );
};

interface TimelineHeaderProps {
  dateRange: GanttDateRange;
}

const TimelineHeader: React.FC<TimelineHeaderProps> = ({ dateRange }) => {
  const days = useMemo(() => {
    const result: Date[] = [];
    const current = new Date(dateRange.start);
    
    while (current <= dateRange.end) {
      result.push(new Date(current));
      current.setDate(current.getDate() + 1);
    }
    
    return result;
  }, [dateRange]);

  return (
    <div className="flex border-b border-gray-200 dark:border-gray-700">
      {days.map((day, index) => {
        const isToday = day.toDateString() === new Date().toDateString();
        const isWeekend = day.getDay() === 0 || day.getDay() === 6;
        
        return (
          <div
            key={index}
            className={clsx(
              "flex-1 min-w-0 px-2 py-4 text-center border-r border-gray-100 dark:border-gray-800",
              {
                "bg-indigo-50 dark:bg-indigo-500/10": isToday,
                "bg-gray-50 dark:bg-gray-800/50": isWeekend,
              }
            )}
          >
            <div className="text-xs font-medium text-gray-500 dark:text-gray-400">
              {day.toLocaleDateString('en', { weekday: 'short' })}
            </div>
            <div className={clsx(
              "text-sm font-semibold",
              isToday ? "text-indigo-600 dark:text-indigo-400" : "text-gray-900 dark:text-white"
            )}>
              {day.getDate()}
            </div>
          </div>
        );
      })}
    </div>
  );
};

const KanbanGanttPage: React.FC = () => {
  const [selectedTimeRange, setSelectedTimeRange] = useState<'week' | 'month' | 'quarter'>('month');
  const [selectedTask, setSelectedTask] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'gantt' | 'timeline'>('gantt');
  const [showCompletedTasks, setShowCompletedTasks] = useState<boolean>(true);

  const dateRange = useMemo((): GanttDateRange => {
    const start = new Date();
    const end = new Date();
    
    switch (selectedTimeRange) {
      case 'week':
        end.setDate(start.getDate() + 7);
        break;
      case 'month':
        end.setDate(start.getDate() + 30);
        break;
      case 'quarter':
        end.setDate(start.getDate() + 90);
        break;
    }
    
    return { start, end };
  }, [selectedTimeRange]);

  const organizedTasks = useMemo(() => {
    const result: Array<{ task: KanbanTask; isSubtask: boolean }> = [];
    const taskMap = new Map(ganttTasks.map(task => [task.id, task]));
    
    // Filter tasks based on completion status
    const filteredTasks = showCompletedTasks 
      ? ganttTasks 
      : ganttTasks.filter(task => (task.progress || 0) < 100);
    
    // Find parent tasks
    const parentTasks = filteredTasks.filter(task => 
      task.children && task.children.length > 0 && 
      !filteredTasks.some(otherTask => 
        otherTask.children?.some(child => child.id === task.id)
      )
    );
    
    // Find standalone tasks
    const standaloneTasks = filteredTasks.filter(task => 
      (!task.children || task.children.length === 0) &&
      !filteredTasks.some(otherTask => 
        otherTask.children?.some(child => child.id === task.id)
      )
    );
    
    // Add standalone tasks
    standaloneTasks.forEach(task => {
      result.push({ task, isSubtask: false });
    });
    
    // Add parent tasks and their children
    parentTasks.forEach(parentTask => {
      result.push({ task: parentTask, isSubtask: false });
      
      parentTask.children?.forEach(child => {
        const childTask = taskMap.get(child.id.toString());
        if (childTask && (showCompletedTasks || (childTask.progress || 0) < 100)) {
          result.push({ task: childTask, isSubtask: true });
        }
      });
    });
    
    return result;
  }, [showCompletedTasks]);

  const handleTaskClick = useCallback((taskId: string) => {
    setSelectedTask(selectedTask === taskId ? null : taskId);
  }, [selectedTask]);

  const taskStats = useMemo(() => {
    const total = ganttTasks.length;
    const completed = ganttTasks.filter(task => (task.progress || 0) >= 100).length;
    const inProgress = ganttTasks.filter(task => (task.progress || 0) > 0 && (task.progress || 0) < 100).length;
    const notStarted = ganttTasks.filter(task => (task.progress || 0) === 0).length;
    
    return { total, completed, inProgress, notStarted };
  }, []);

  return (
    <div className="space-y-6">
      <PageBreadcrumb pageTitle="Kanban Gantt Chart" />

      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Project Timeline</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Visualize task dependencies and progress in a timeline view for better project planning.
          </p>
        </div>
        
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex rounded-lg border border-gray-200 bg-white p-1 dark:border-gray-700 dark:bg-gray-900">
            {(['week', 'month', 'quarter'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setSelectedTimeRange(range)}
                className={clsx(
                  "px-3 py-1.5 text-sm font-medium rounded-md transition-all",
                  selectedTimeRange === range
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                )}
              >
                {range.charAt(0).toUpperCase() + range.slice(1)}
              </button>
            ))}
          </div>
          
          <div className="flex rounded-lg border border-gray-200 bg-white p-1 dark:border-gray-700 dark:bg-gray-900">
            {(['gantt', 'timeline'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={clsx(
                  "px-3 py-1.5 text-sm font-medium rounded-md transition-all",
                  viewMode === mode
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                )}
              >
                {mode.charAt(0).toUpperCase() + mode.slice(1)}
              </button>
            ))}
          </div>

          <label className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-500 shadow-sm dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300">
            <input
              type="checkbox"
              checked={showCompletedTasks}
              onChange={(e) => setShowCompletedTasks(e.target.checked)}
              className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span>Show Completed</span>
          </label>
          
          <a 
            href="/kanban-board"
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M9 11H3m6 0V9m0 2v2m0-2h6m-6 0a3 3 0 003 3v-3m-3 0a3 3 0 00-3 3v-3" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Kanban View
          </a>
          
          <button className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Export
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-800">
              <svg className="h-5 w-5 text-gray-600 dark:text-gray-400" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 11H3m6 0V9m0 2v2m0-2h6m-6 0a3 3 0 003 3v-3m-3 0a3 3 0 00-3 3v-3" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Tasks</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{taskStats.total}</p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 dark:bg-emerald-500/10">
              <svg className="h-5 w-5 text-emerald-600 dark:text-emerald-400" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
                <path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9 9 4.03 9 9z" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Completed</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{taskStats.completed}</p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100 dark:bg-amber-500/10">
              <svg className="h-5 w-5 text-amber-600 dark:text-amber-400" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2l2 7h7l-5.5 4.5L17 21l-5-4-5 4 1.5-7.5L3 9h7l2-7z" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">In Progress</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{taskStats.inProgress}</p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-800">
              <svg className="h-5 w-5 text-gray-600 dark:text-gray-400" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 8v4l3 3" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
                <path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9 9 4.03 9 9z" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Not Started</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{taskStats.notStarted}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Legend</h3>
        <div className="flex flex-wrap items-center gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-4 h-2 rounded bg-emerald-500"></div>
            <span className="text-gray-600 dark:text-gray-300">Low Priority</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-2 rounded bg-amber-500"></div>
            <span className="text-gray-600 dark:text-gray-300">Medium Priority</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-2 rounded bg-orange-500"></div>
            <span className="text-gray-600 dark:text-gray-300">High Priority</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-2 rounded bg-rose-500 ring-2 ring-orange-400 ring-opacity-50"></div>
            <span className="text-gray-600 dark:text-gray-300">Critical Priority</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-2 rounded bg-emerald-100 border-2 border-emerald-300 dark:bg-emerald-500/20 dark:border-emerald-500/40"></div>
            <span className="text-gray-600 dark:text-gray-300">Completed</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-2 rounded bg-rose-100 border-2 border-rose-300 dark:bg-rose-500/20 dark:border-rose-500/40"></div>
            <span className="text-gray-600 dark:text-gray-300">Overdue</span>
          </div>
        </div>
      </div>

      {/* Gantt Chart */}
      <div className="rounded-3xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
        <div className="border-b border-gray-200 px-6 py-4 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Project Timeline</h2>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Track progress and dependencies across all tasks
              </p>
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Showing {organizedTasks.length} tasks • {selectedTimeRange} view
            </div>
          </div>
        </div>

        <div className="flex">
          {/* Task List */}
          <div className="w-96 flex-shrink-0 border-r border-gray-200 dark:border-gray-700">
            <div className="border-b border-gray-200 px-4 py-3 dark:border-gray-700">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Tasks</h3>
            </div>
            <div className="divide-y divide-gray-100 dark:divide-gray-800">
              {organizedTasks.map(({ task, isSubtask }) => (
                <div
                  key={task.id}
                  onClick={() => handleTaskClick(task.id)}
                  className={clsx(
                    "cursor-pointer px-4 py-6 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50",
                    {
                      "bg-indigo-50 dark:bg-indigo-500/10": selectedTask === task.id,
                      "pl-8 py-4": isSubtask,
                    }
                  )}
                >
                  <div className="flex items-start gap-3">
                    {isSubtask && (
                      <div className="mt-1 flex-shrink-0">
                        <div className="h-2 w-2 rounded-full bg-gray-300 dark:bg-gray-600" />
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <h4 className={clsx(
                        "font-semibold truncate leading-tight",
                        isSubtask ? "text-sm text-gray-600 dark:text-gray-400" : "text-base text-gray-900 dark:text-white"
                      )}>
                        {task.title}
                      </h4>
                      <div className="mt-2 flex items-center gap-3">
                        <span className={clsx(
                          "inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold",
                          priorityBgColors[task.priority]
                        )}>
                          {task.priority.toUpperCase()}
                        </span>
                        <div className="flex items-center gap-1">
                          <div className="w-16 bg-gray-200 rounded-full h-1.5 dark:bg-gray-700">
                            <div 
                              className={clsx("h-1.5 rounded-full transition-all", priorityColors[task.priority])}
                              style={{ width: `${task.progress || 0}%` }}
                            />
                          </div>
                          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                            {task.progress || 0}%
                          </span>
                        </div>
                      </div>
                      {task.assignee && (
                        <p className="mt-2 text-sm font-medium text-gray-600 dark:text-gray-300">
                          👤 {task.assignee}
                        </p>
                      )}
                      {task.dueDate && (
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                          📅 Due: {new Date(task.dueDate).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Timeline */}
          <div className="flex-1 overflow-x-auto">
            <TimelineHeader dateRange={dateRange} />
            
            <div className="divide-y divide-gray-100 dark:divide-gray-800">
              {organizedTasks.map(({ task, isSubtask }) => (
                <div
                  key={task.id}
                  className={clsx(
                    "relative h-20 flex items-center px-4",
                    {
                      "bg-indigo-50 dark:bg-indigo-500/10": selectedTask === task.id,
                      "h-16": isSubtask,
                    }
                  )}
                >
                  <GanttBar task={task} dateRange={dateRange} isSubtask={isSubtask} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Task Details Panel */}
      {selectedTask && (
        <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
          {(() => {
            const task = ganttTasks.find(t => t.id === selectedTask);
            if (!task) return null;
            
            return (
              <div>
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{task.title}</h3>
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{task.description}</p>
                  </div>
                  <button
                    onClick={() => setSelectedTask(null)}
                    className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
                  >
                    <svg className="h-5 w-5" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M6 6l8 8M14 6l-8 8" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </button>
                </div>
                
                <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-3">
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Progress</h4>
                    <div className="mt-2 flex items-center gap-3">
                      <div className="flex-1 bg-gray-200 rounded-full h-2 dark:bg-gray-700">
                        <div 
                          className={clsx("h-2 rounded-full transition-all", priorityColors[task.priority])}
                          style={{ width: `${task.progress || 0}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        {task.progress || 0}%
                      </span>
                    </div>
                  </div>
                  
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Assignee</h4>
                    <p className="mt-2 text-sm text-gray-900 dark:text-white">{task.assignee || 'Unassigned'}</p>
                  </div>
                  
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Due Date</h4>
                    <p className="mt-2 text-sm text-gray-900 dark:text-white">
                      {task.dueDate ? new Date(task.dueDate).toLocaleDateString() : 'No due date'}
                    </p>
                  </div>
                </div>
                
                {task.tags && task.tags.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Tags</h4>
                    <div className="flex flex-wrap gap-2">
                      {task.tags.map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600 dark:bg-gray-700/60 dark:text-gray-200"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
};

export default KanbanGanttPage;