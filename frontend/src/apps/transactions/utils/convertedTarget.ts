/** What a convert command made: the target model, its id, and the lines it returns for review
 *  (the user saves them — review before save, Bill 2026-09-27); null lines when the server
 *  saved them itself (a receipt). Null for any other result. One reader for every host. */
export interface ConvertedTarget { model: string; id: number; lines: any[] | null }

export function convertedTarget(result: any): ConvertedTarget | null {
  if (!result) return null;
  for (const model of ['order', 'invoice', 'purchase', 'receipt', 'workorder']) {
    const id = result[`${model}_id`];
    if (id) {
      const lines = Array.isArray(result.lines) && result.lines.length ? result.lines : null;
      return { model, id: Number(id), lines };
    }
  }
  return null;
}
