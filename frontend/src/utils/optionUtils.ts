/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface Option {
  value: string;
  label: string;
}

export function mapStaticListToOptions(list?: unknown[]): Option[] {
  if (!Array.isArray(list)) {
    return [];
  }

  return list
    .map((entry) => {
      if (Array.isArray(entry)) {
        const rawValue = entry[0];
        const rawLabel = entry[1];
        const value = rawValue != null ? String(rawValue) : "";
        const label = rawLabel != null ? String(rawLabel) : value;
        return { value, label };
      }
      if (entry == null) {
        return { value: "", label: "" };
      }
      const value = String(entry);
      return { value, label: value };
    })
    .filter((option) => option.value !== "");
}

export function firstAvailableValue(record: Record<string, unknown> | null | undefined, keys: string[]): string {
  if (!record) {
    return "";
  }
  for (const key of keys) {
    const value = record[key];
    if (value !== undefined && value !== null && value !== "") {
      return String(value);
    }
  }
  return "";
}
