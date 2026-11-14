/** A converted document's lines before its first save (Bill, 2026-11-13: "save the record to get
 *  the ida, but keep the lines as an array without ida while users adjust quantities").
 *
 *  Convert saves the parent only. The server proposes the lines (POST /wcapi/<model>/<id>/propose/),
 *  each naming its source line as `_from`; the form holds them unsaved. The first save sends each
 *  as `{_from, ...what the person changed}` and the server builds the line from its source line,
 *  so stock moves once, at the quantity the person settled on. One reader and one writer here. */

/** The record with its proposed lines in place of the lines it does not have yet. */
export function withProposed(record: any, proposal: any[]): any {
  if (!proposal.length) return record;
  return { ...record, lines: proposal.map((line) => ({ ...line, _new: true, _dirty: true })) };
}

/** True when this document's lines are still the server's proposal. */
export function isProposed(line: any): boolean {
  return line?._from != null;
}

const NOT_SENT = new Set(['id', 'version', '_new', '_dirty', '_from', '_index', 'totals']);

/** What the first save sends for a proposed line: its source line and only what the person
 *  changed. A changed quantity goes as `quantity.active` alone; the rest of the quantity is the
 *  server's. A line the person did not touch goes as `{_from}` and takes what its source has
 *  left (for an invoice, what is in stock) at the moment of the save. */
export function proposedLineToSend(line: any, proposal: any | undefined): Record<string, any> {
  const out: Record<string, any> = { _from: line._from, _dirty: true };
  for (const [key, value] of Object.entries(line)) {
    if (NOT_SENT.has(key)) continue;
    if (proposal && JSON.stringify(proposal[key]) === JSON.stringify(value)) continue;
    if (key === 'quantity') {
      const active = (value as any)?.active;
      if (active !== undefined && active !== proposal?.quantity?.active) out.quantity = { active };
      continue;
    }
    out[key] = value;
  }
  return out;
}
