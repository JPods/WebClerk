/**
 * Workorders — the one way stock is corrected or built (workorder plan 2026-09-26, stock plan §16b).
 *
 * A correction is a count workorder: count lines (what was counted; the server records the book)
 * and adjust lines (a change, with its reason as a comments.process entry). A build is a production
 * workorder: one item per line, signed — build (+), consume (−), scrap (−) — expanded from the BOM
 * and completed all or nothing (Bill: one workorder per build). Every save goes through the door;
 * the server's line door and Pending applier move the stock.
 */
import { getRecords, newRecord, wcapiSave } from './wcapi';
import apiClient from './axios';

export type CorrectionLine = {
  item_id: number;
  /** The item's code and name, kept on the line so it reads without a lookup. */
  ida?: string;
  description?: string;
  /** 'count': quantity is what was counted. 'adjust': quantity is the signed change. */
  line_type: 'count' | 'adjust';
  quantity: number;
  /** Required on an adjust line; recorded in comments.process. */
  reason?: string;
  /** A count or adjustment of one layer names it. */
  layer_id?: number | null;
  /** Unit cost for found stock (a count or adjustment that adds). */
  unit_cost?: number;
};

export type BuildLine = {
  item_id: number;
  ida?: string;
  description?: string;
  line_type: 'build' | 'consume' | 'scrap';
  /** Signed: + for build, − for consume and scrap. */
  quantity: number;
  unit_cost?: number;
};

export function lineBody(line: CorrectionLine | BuildLine, i: number): Record<string, unknown> {
  const body: Record<string, unknown> = {
    id: -(i + 1),
    line_type: line.line_type,
    item: {
      item_id: line.item_id,
      ...(line.ida ? { ida: line.ida } : {}),
      ...(line.description ? { description: line.description } : {}),
    },
    quantity: { active: line.quantity },
  };
  if (line.unit_cost !== undefined) body.cost = { unit: line.unit_cost };
  const c = line as CorrectionLine;
  if (c.layer_id) body.physical = { layer_id: c.layer_id };
  if (c.reason && c.reason.trim()) body.comments = { process: [{ mgs: c.reason.trim() }] };
  return body;
}

/** Save a workorder's kind and lines: new lines (negative ids), changed ones ({id, _dirty}),
 * removed ones ({id, _delete}). Count and adjust lines move stock as they save. */
export async function saveWorkorderLines(workorderId: number, kind: 'count' | 'production',
                                         lines: Record<string, unknown>[]) {
  return wcapiSave<any>('workorder', { kind, lines }, undefined, workorderId);
}

/** A new, empty workorder of this kind; returns its id. */
export async function createWorkorder(kind: 'count' | 'production'): Promise<number> {
  const made = await newRecord('workorder');
  await wcapiSave<any>('workorder', { kind }, undefined, made.id);
  return made.id;
}

/** A new workorder of this kind with these lines; returns the saved record. */
async function newWorkorder(kind: 'count' | 'production', lines: Record<string, unknown>[]) {
  const made = await newRecord('workorder');
  return wcapiSave<any>('workorder', { kind, lines }, undefined, made.id);
}

/** Save stock corrections as one count workorder. Returns the workorder record. */
export async function saveCorrection(lines: CorrectionLine[]) {
  if (!lines.length) throw new Error('Nothing to correct.');
  const missing = lines.find((l) => l.line_type === 'adjust' && !(l.reason || '').trim());
  if (missing) throw new Error('An adjustment needs its reason.');
  return newWorkorder('count', lines.map(lineBody));
}

/** POST /wcapi/workorder/<id>/expand/ — a build line's BOM, one level (1) or all of it (0). */
export async function expandWorkorder(workorderId: number, lineId: number, depth: 0 | 1) {
  const res = await apiClient.post(`/wcapi/workorder/${workorderId}/expand/`, { line_id: lineId, depth });
  return res.data?.data?.result ?? res.data?.data ?? res.data;   // a command answers {result}
}

/** POST /wcapi/workorder/<id>/complete/ — the build moves its stock, all or nothing. */
export async function completeWorkorder(workorderId: number) {
  const res = await apiClient.post(`/wcapi/workorder/${workorderId}/complete/`, {});
  return res.data?.data?.result ?? res.data?.data ?? res.data;
}

/** Build qty of an item from its BOM on a new workorder: build line → expand → complete. */
export async function buildItem(itemId: number, qty: number, depth: 0 | 1 = 1) {
  const wo = await newWorkorder('production', [lineBody({ item_id: itemId, line_type: 'build', quantity: qty }, 0)]);
  const record = wo?.record ?? wo;
  let buildLine = (record?.lines || []).find((l: any) => l.line_type === 'build');
  if (!buildLine) {
    const found: any = await getRecords('workorder_line', { workorder_id: record.id, line_type: 'build' });
    buildLine = (found?.results || found?.records || [])[0];
  }
  if (!buildLine) throw new Error('The workorder saved without its build line.');
  await expandWorkorder(record.id, buildLine.id, depth);
  const done = await completeWorkorder(record.id);
  return { workorder_id: record.id, ...done };
}
