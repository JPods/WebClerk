import React from "react";

interface SidebarSection {
  id: string;
  title: string;
  description: string;
  href?: string;
  badge?: string;
}

interface SidebarCta {
  label: string;
  href: string;
  description?: string;
}

interface SvarGanttSidebarProps {
  sections: SidebarSection[];
  cta?: SidebarCta;
}

const SvarGanttSidebar: React.FC<SvarGanttSidebarProps> = ({ sections, cta }) => {
  return (
    <aside className="w-full lg:w-64 flex-shrink-0">
      <div className="sticky top-[calc(var(--app-header-height,4.5rem)+1.5rem)] space-y-5 rounded-3xl border border-gray-200 bg-white/90 p-5 shadow-sm backdrop-blur supports-[backdrop-filter]:backdrop-blur dark:border-gray-800 dark:bg-gray-900/70">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-500 dark:text-indigo-300">Navigation</p>
          <h2 className="mt-1 text-xl font-semibold text-gray-900 dark:text-white">SVAR Gantt Toolkit</h2>
          <p className="mt-2 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
            Jump between key sections or open the official resources directly from this contextual menu.
          </p>
        </div>

        <nav className="space-y-3" aria-label="SVAR Gantt menu">
          {sections.map((section) => (
            <a
              key={section.id}
              href={section.href ?? `#${section.id}`}
              className="block rounded-2xl border border-gray-100 px-4 py-3 text-left transition hover:border-indigo-200 hover:bg-indigo-50/70 dark:border-gray-800 dark:hover:border-indigo-500/60 dark:hover:bg-indigo-500/10"
            >
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-gray-900 dark:text-white">{section.title}</span>
                {section.badge && (
                  <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-200">
                    {section.badge}
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{section.description}</p>
            </a>
          ))}
        </nav>

        {cta && (
          <div className="rounded-2xl border border-dashed border-indigo-300/60 bg-indigo-50/80 p-4 text-sm text-indigo-900 dark:border-indigo-500/40 dark:bg-indigo-500/15 dark:text-indigo-100">
            <p className="font-semibold">Need the original docs?</p>
            {cta.description && <p className="mt-1 text-xs opacity-80">{cta.description}</p>}
            <a
              href={cta.href}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-flex items-center gap-2 rounded-full bg-indigo-600 px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-white shadow-sm transition hover:bg-indigo-500"
            >
              {cta.label}
              <svg className="h-3 w-3" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path
                  d="M5 10h10m0 0l-4-4m4 4l-4 4"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </a>
          </div>
        )}
      </div>
    </aside>
  );
};

export default SvarGanttSidebar;
