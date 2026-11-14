/** What a convert command made: the target model and its id. The server saves the parent only
 *  (Bill, 2026-11-13); the form that opens it asks for its proposed lines and holds them unsaved
 *  until the first save (utils/proposedLines.ts). Null for any other result. One reader for
 *  every host. */
export interface ConvertedTarget { model: string; id: number }

export function convertedTarget(result: any): ConvertedTarget | null {
  if (!result) return null;
  for (const model of ['order', 'invoice', 'purchase', 'receipt', 'workorder']) {
    const id = result[`${model}_id`];
    if (id) return { model, id: Number(id) };
  }
  return null;
}
