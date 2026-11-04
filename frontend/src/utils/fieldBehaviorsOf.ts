/**
 * fieldBehaviorsOf — a model's field behaviors as the screen reads them, from its wc:model Setting.
 *
 * One option source: config.selectlists (Bill, 2026-11-03: "my norm phrase is selectlists").
 * A field named there is a select with exactly those options, whatever config.behaviors says.
 * Every reader of behaviors goes through here — DataBrowser, the transaction form, the dynamic
 * detail and the list config once each read config.behaviors on their own, and only one of them
 * folded the selectlists in, so a cash showed status "active" for a completed one (readme 104).
 */
export function fieldBehaviorsOf(config: any): Record<string, any> {
  const behaviors: Record<string, any> = { ...((config && config.behaviors) || {}) };
  const selectlists = config && config.selectlists;
  if (selectlists && typeof selectlists === 'object') {
    for (const [field, opts] of Object.entries(selectlists)) {
      if (Array.isArray(opts) && opts.length > 0) {
        behaviors[field] = { ...(behaviors[field] || {}), type: 'select', options: opts };
      }
    }
  }
  return behaviors;
}
