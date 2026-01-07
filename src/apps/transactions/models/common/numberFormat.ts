export function formatNumberValue(value: unknown, fractionDigits = 2): string {
  if (value === undefined || value === null || value === "") {
    return "";
  }
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric)) {
    return "";
  }
  const options: Intl.NumberFormatOptions = {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  };
  return numeric.toLocaleString(undefined, options);
}

export function formatQuantityValue(value: unknown): string {
  if (value === undefined || value === null || value === "") {
    return "";
  }
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric)) {
    return "";
  }
  if (Number.isInteger(numeric)) {
    return numeric.toLocaleString();
  }
  return numeric.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
