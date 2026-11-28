/**
 * dt_created on every form and every list (Bill, 2026-11-27).
 *
 * Every model inherits dt_created from CoreModel (backend common/models.py: "Forms required
 * baseline"), so it is shown whether or not a layout names it. Bill: "dt_create is not the most
 * import field. So it can go the right side of lists." A form that does not name it gets it at
 * the end of its header's last column; a list that does not name it gets it after its stored
 * columns. A layout that names it keeps it where it is: nothing is reordered or shown twice.
 */
export const BASELINE_DATE = 'dt_created';

const names = (value: unknown): boolean => JSON.stringify(value ?? null).includes(`"${BASELINE_DATE}"`);

/** True when the form's sections, or the cards its headers draw, name dt_created. */
export function formNamesBaselineDate(layout: { sections?: any[]; card?: Record<string, any> } | null | undefined): boolean {
  const sections = layout?.sections || [];
  if (names(sections)) return true;
  const cards = sections.flatMap((s: any) => s?.header?.cards || []);
  return cards.some((c: string) => names(layout?.card?.[c]));
}

/** The form's sections with dt_created added when the layout does not name it. */
export function sectionsWithBaselineDate(layout: { sections?: any[]; card?: Record<string, any> } | null | undefined): any[] {
  const sections = layout?.sections || [];
  if (!layout || formNamesBaselineDate(layout)) return sections;
  const field = { field: BASELINE_DATE, label: BASELINE_DATE };
  const at = sections.findIndex((s: any) => s?.type === 'header' && s?.layout === 'three-column' && s?.columns?.length);
  if (at < 0) return [{ type: 'header', layout: 'three-column', columns: [{ fields: [field] }] }, ...sections];
  const header = sections[at];
  const columns = header.columns.map((c: any, i: number) =>
    i === header.columns.length - 1 ? { ...c, fields: [...(c.fields || []), field] } : c);
  return sections.map((s: any, i: number) => (i === at ? { ...header, columns } : s));
}

/** A list's columns with dt_created after them when they do not name it and the model has it. */
export function listWithBaselineDate<T extends string | { field: string }>(columns: T[], modelFields: string[]): T[] {
  const named = columns.some((c) => (typeof c === 'string' ? c : c?.field) === BASELINE_DATE);
  if (named || !modelFields.includes(BASELINE_DATE)) return columns;
  return [...columns, BASELINE_DATE as T];
}
