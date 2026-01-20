export function validate_snake_case(obj: any, path: string = "root"): void {
  if (obj === null || typeof obj !== "object") return;
  for (const key of Object.keys(obj)) {
    if (!/^[a-z0-9_]+$/.test(key)) {
      throw new Error(`Non-snake_case key detected at ${path}: ${key}`);
    }
    validate_snake_case(obj[key], `${path}.${key}`);
  }
}

export function assert_snake_case(obj: any): void {
  validate_snake_case(obj);
}
