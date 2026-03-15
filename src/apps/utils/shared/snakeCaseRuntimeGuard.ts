/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export function validate_snake_case_keys(obj: unknown): void {
  if (obj === null || typeof obj !== "object") return;

  const stack: unknown[] = [obj];

  const snakeCaseRegex = /^[a-z]+(_[a-z0-9]+)*$/;

  while (stack.length) {
    const current = stack.pop();
    if (current && typeof current === "object") {
      for (const key of Object.keys(current as Record<string, unknown>)) {
        if (!snakeCaseRegex.test(key)) {
          throw new Error(`Invalid key '${key}'. Keys must be snake_case.`);
        }
        const value = (current as Record<string, unknown>)[key];
        if (value && typeof value === "object") {
          stack.push(value);
        }
      }
    }
  }
}
