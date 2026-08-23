/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
interface SingleWindowSectionProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}
function SingleWindowSection({
  title,
  children,
  className = "",
}: SingleWindowSectionProps) {
  return (
    <section
      className={`rounded-sm border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 ${className}`}
    >
      <div className="px-2 py-1 text-[10px] font-semibold tracking-wide uppercase text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 border-b border-slate-300 dark:border-slate-700">
        {title}
      </div>
      <div className="p-2">{children}</div>
    </section>
  );
}
export default SingleWindowSection;
