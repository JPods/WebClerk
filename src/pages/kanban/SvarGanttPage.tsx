import { useMemo, useState } from "react";
import { Gantt, Willow } from "@svar-ui/react-gantt";
import type { IColumnConfig, ITask } from "@svar-ui/react-gantt";
import "@svar-ui/react-gantt/all.css";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
const screenshotInspiredTasks = [
  { id: 1, text: "Project planning", start: new Date(2024, 3, 2), duration: 16, type: "summary", progress: 65 },
  { id: 2, parent: 1, text: "Marketing analysis", start: new Date(2024, 3, 3), duration: 3, type: "task" },
  { id: 3, parent: 1, text: "Discussions", start: new Date(2024, 3, 6), duration: 2, type: "task" },
  { id: 4, parent: 1, text: "Project management", start: new Date(2024, 3, 2), duration: 10, type: "task" },
  { id: 5, parent: 1, text: "Approval of strategy", start: new Date(2024, 3, 9), duration: 0, type: "milestone" },
  { id: 6, parent: 1, text: "New Task", start: new Date(2024, 3, 3), duration: 1, type: "task" },
  { id: 7, text: "Development", start: new Date(2024, 3, 2), duration: 43, type: "summary", progress: 40 },
  { id: 8, parent: 7, text: "Prototyping", start: new Date(2024, 3, 2), duration: 13, type: "task" },
  { id: 9, parent: 7, text: "Basic functionality", start: new Date(2024, 3, 15), duration: 15, type: "task" },
  { id: 10, parent: 7, text: "Finalizing MVA", start: new Date(2024, 3, 30), duration: 11, type: "task" },
  { id: 11, text: "Testing", start: new Date(2024, 3, 2), duration: 46, type: "summary" },
  { id: 12, parent: 11, text: "Testing prototype", start: new Date(2024, 3, 2), duration: 6, type: "task" },
  { id: 13, parent: 11, text: "Testing basic features", start: new Date(2024, 3, 8), duration: 15, type: "task" },
  { id: 14, parent: 11, text: "Testing MVA", start: new Date(2024, 3, 23), duration: 15, type: "task" },
  { id: 15, parent: 11, text: "Beta testing", start: new Date(2024, 4, 8), duration: 10, type: "task" },
  { id: 16, text: "Release 1.0.0", start: new Date(2024, 4, 25), duration: 0, type: "milestone" },
];

const screenshotInspiredLinks = [
  { id: 1, source: 2, target: 3, type: "e2e" },
  { id: 2, source: 3, target: 4, type: "e2s" },
  { id: 3, source: 4, target: 5, type: "fs" },
  { id: 4, source: 8, target: 9, type: "fs" },
  { id: 5, source: 9, target: 10, type: "fs" },
  { id: 6, source: 12, target: 13, type: "fs" },
  { id: 7, source: 13, target: 14, type: "fs" },
  { id: 8, source: 14, target: 15, type: "fs" },
  { id: 9, source: 15, target: 16, type: "fs" },
];

const ganttDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

const formatDate = (value?: Date) => (value ? ganttDateFormatter.format(value) : "-");

const ganttColumns: IColumnConfig[] = [
  { id: "text", header: "Task name", flexgrow: 1, sort: true },
  {
    id: "start",
    header: "Start date",
    width: 140,
    align: "center",
    sort: true,
    template: (task: ITask) => formatDate(task.start),
  },
  {
    id: "duration",
    header: "Duration",
    width: 110,
    align: "center",
    template: (task: ITask) => (task.duration ? `${task.duration} d` : "-"),
  },
  {
    id: "add-task",
    header: "",
    width: 48,
    align: "center",
    resize: false,
  },
];

type ScalePresetKey = "month" | "week";
type ScaleConfig = { unit: string; step: number; format: string };

const scalePresets: Record<ScalePresetKey, ScaleConfig[]> = {
  month: [
    { unit: "month", step: 1, format: "MMMM yyyy" },
    { unit: "day", step: 1, format: "d" },
  ],
  week: [
    { unit: "week", step: 1, format: "'Week' w" },
    { unit: "day", step: 1, format: "EEE d" },
  ],
};

const scaleButtons: Array<{ id: ScalePresetKey; label: string }> = [
  { id: "month", label: "Month" },
  { id: "week", label: "Week" },
];

const SvarGanttPage: React.FC = () => {
  const ganttData = useMemo(
    () => ({ tasks: screenshotInspiredTasks, links: screenshotInspiredLinks }),
    []
  );
  const [scalePreset, setScalePreset] = useState<ScalePresetKey>("month");
  const activeScales = scalePresets[scalePreset];

  return (
    <div className="space-y-6">
      <PageBreadcrumb pageTitle="SVAR React Gantt" />

      <section className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900/70">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Classic timeline view</h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
              This layout mirrors the official SVAR demo: tree grid on the left, fully interactive bars on the right,
              and default plus buttons for adding work items directly inside the chart.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            <span className="rounded-full bg-gray-100 px-3 py-1 dark:bg-gray-800">Drag & drop</span>
            <span className="rounded-full bg-gray-100 px-3 py-1 dark:bg-gray-800">Dependencies</span>
            <span className="rounded-full bg-gray-100 px-3 py-1 dark:bg-gray-800">Milestones</span>
          </div>
        </div>

        <div className="mt-5 rounded-2xl border border-gray-200 bg-gray-50/70 dark:border-gray-800 dark:bg-gray-900">
          <div className="flex flex-col gap-3 border-b border-gray-100 px-4 py-3 text-sm dark:border-gray-800 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-wrap gap-2">
              {scaleButtons.map((button) => (
                <button
                  key={button.id}
                  type="button"
                  onClick={() => setScalePreset(button.id)}
                  className={`rounded-full px-4 py-1 font-semibold transition ${
                    scalePreset === button.id
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "border border-gray-300 text-gray-600 hover:border-indigo-300 hover:text-indigo-600 dark:border-gray-700 dark:text-gray-300"
                  }`}
                >
                  {button.label}
                </button>
              ))}
            </div>
            <a
              href="https://svar.dev/demos/react/gantt/"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-full border border-indigo-200 px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-indigo-700 transition hover:border-indigo-400 hover:text-indigo-900 dark:border-indigo-500/40 dark:text-indigo-200"
            >
              View official demo
              <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path
                  d="M7 5h8v8m0-8-8 8"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </a>
          </div>

          <div className="h-[640px] overflow-hidden rounded-b-2xl">
            <Willow>
              <Gantt tasks={ganttData.tasks} links={ganttData.links} columns={ganttColumns} scales={activeScales} />
            </Willow>
          </div>
        </div>
      </section>
    </div>
  );
};

export default SvarGanttPage;
