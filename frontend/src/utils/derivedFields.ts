/**
 * derivedFields.ts — fields a form fills from other fields while the user types.
 *
 * Bill, 2026-10-16: entering a contact's first and last name populates attention
 * when attention is empty. "Empty" includes a value this rule wrote itself: typing
 * "Susy" fills "Susy", and typing the last name then updates it to "Susy Que".
 * A value the user typed is theirs and is never overwritten.
 *
 * The backend applies the same rule on save (Contact.save), so a record saved by
 * any channel ends up the same.
 */

type Derivation = { from: string[]; join: string };

const DERIVED: Record<string, Record<string, Derivation>> = {
  contact: {
    attention: { from: ['name_first', 'name_last'], join: ' ' },
  },
};

function compose(record: any, d: Derivation): string {
  return d.from.map(f => String(record?.[f] ?? '').trim()).filter(Boolean).join(d.join);
}

/** Apply a field change, then refill any derived field that is empty or still derived. */
export function applyDerived(modelName: string, prev: any, next: any, field: string): any {
  const rules = DERIVED[modelName];
  if (!rules || !prev || !next) return next;
  let out = next;
  for (const [target, d] of Object.entries(rules)) {
    if (!d.from.includes(field)) continue;
    const current = String(prev[target] ?? '').trim();
    if (current && current !== compose(prev, d)) continue;   // the user's own value
    out = { ...out, [target]: compose(out, d) };
  }
  return out;
}
