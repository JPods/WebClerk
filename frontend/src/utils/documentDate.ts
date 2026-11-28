/**
 * A document's date, changed by an admin or superuser before it is journalized (Bill, 2026-11-27:
 * "dt_created will be best... If they need to adjust it, an admin or superuser can adjust it").
 *
 * dt_created is a system stamp everywhere else. On these four documents it is the period the GL
 * rows carry (dt_document), so an admin or superuser may unlock it. The server is the gate
 * (save.py DOCUMENT_DATE_MODELS): it takes the change only with `_unlock: ["dt_created"]`, only
 * from a superuser or an admin login, only while dt_journaled is empty. This only decides
 * whether the form offers the lock button; any refusal is the server's, shown as it comes.
 */

/** Mirrors backend save.py DOCUMENT_DATE_MODELS; the server's list is authoritative. */
export const DOCUMENT_DATE_MODELS = ['invoice', 'cash', 'receipt', 'workorder'];
export const DOCUMENT_DATE_FIELD = 'dt_created';

interface Login { is_superuser?: boolean; role?: string | null }

/** True when this login may unlock this saved, unjournalized document's date. */
export function mayChangeDocumentDate(user: Login | null | undefined, modelName: string, record: any): boolean {
  if (!user || !DOCUMENT_DATE_MODELS.includes(modelName)) return false;
  if (!record?.id || record?.dt_journaled) return false;
  return !!user.is_superuser || user.role === 'admin';
}

/** The fields this login may unlock on this record (for the form's rows). */
export function unlockableFields(user: Login | null | undefined, modelName: string, record: any): string[] {
  return mayChangeDocumentDate(user, modelName, record) ? [DOCUMENT_DATE_FIELD] : [];
}

/** The save body: a changed document date goes as UTC epoch ms with its `_unlock` signal.
 *  An unchanged date is not in the body (changedFields), so no signal goes either. */
export function withDocumentDateUnlock(modelName: string, body: Record<string, any>): Record<string, any> {
  if (!DOCUMENT_DATE_MODELS.includes(modelName) || !(DOCUMENT_DATE_FIELD in body)) return body;
  const value = body[DOCUMENT_DATE_FIELD];
  const ms = typeof value === 'string' && !/^-?\d+$/.test(value.trim()) ? Date.parse(value) : Number(value);
  return { ...body, [DOCUMENT_DATE_FIELD]: Number.isFinite(ms) ? ms : value, _unlock: [DOCUMENT_DATE_FIELD] };
}
