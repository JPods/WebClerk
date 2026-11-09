/**
 * toastActions — the one thing a toast may offer: a button that runs a function.
 *
 * Redux state holds only data, so the toast carries an action id and label; the function
 * lives here until the toast is pressed or replaced. One toast at a time (toastSlice), so one
 * action at a time: registering a new one forgets the last.
 */
let current: { id: string; run: () => void } | null = null;

export function registerToastAction(run: () => void): string {
  const id = `ta-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
  current = { id, run };
  return id;
}

/** Run the action the toast named, once. */
export function runToastAction(id: string): void {
  if (!current || current.id !== id) return;
  const { run } = current;
  current = null;
  run();
}
