/** What a convert command made: the target model and its id. The server saves the target with
 *  its lines (Bill, 2026-11-08: "save with lines"), so the host only opens it. Null for any
 *  other result. One reader for every host. */
export interface ConvertedTarget { model: string; id: number }

export function convertedTarget(result: any): ConvertedTarget | null {
  if (!result) return null;
  for (const model of ['order', 'invoice', 'purchase', 'receipt', 'workorder']) {
    const id = result[`${model}_id`];
    if (id) return { model, id: Number(id) };
  }
  return null;
}
