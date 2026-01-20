export const extractNumericValue = (value: unknown): number | null => {
  if (value === null || value === undefined) {
    return null;
  }

  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  if (typeof value === "string") {
    const parsed = Number(value.replace(/,/g, ""));
    return Number.isFinite(parsed) ? parsed : null;
  }

  if (Array.isArray(value)) {
    for (const entry of value) {
      const numeric = extractNumericValue(entry);
      if (numeric !== null) {
        return numeric;
      }
    }
    return null;
  }

  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    for (const nested of Object.values(record)) {
      const numeric = extractNumericValue(nested);
      if (numeric !== null) {
        return numeric;
      }
    }
  }

  return null;
};

export const coerceNumber = (value: unknown, fallback = 0): number => {
  const numeric = extractNumericValue(value);
  return numeric !== null ? numeric : fallback;
};

export const formatQuantity = (value: unknown): string => {
  const numeric = coerceNumber(value);
  return Number.isInteger(numeric) ? `${numeric}` : numeric.toFixed(2);
};

export const formatCurrency = (value: unknown): string => coerceNumber(value).toFixed(2);

export const coerceFormValue = (value: unknown): string | number | boolean | null | undefined => {
  if (value === null || value === undefined) {
    return value;
  }

  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return value;
  }

  if (typeof value === "object") {
    const record = value as Record<string, unknown>;

    if ("value" in record) {
      const direct = record.value;
      if (typeof direct === "string" || typeof direct === "number" || typeof direct === "boolean") {
        return direct;
      }
      const numeric = extractNumericValue(direct);
      if (numeric !== null) {
        return numeric;
      }
    }

    if ("label" in record) {
      const label = record.label;
      if (typeof label === "string") {
        return label;
      }
    }

    const numeric = extractNumericValue(record);
    if (numeric !== null) {
      return numeric;
    }

    const primitiveChild = Object.values(record).find(
      (entry) => typeof entry === "string" || typeof entry === "number"
    );
    if (primitiveChild !== undefined) {
      return primitiveChild as string | number;
    }

    return JSON.stringify(record);
  }

  return undefined;
};

export const normalizeLineItem = (line: any) => {
  const safeLine = { ...(line || {}) };
  const quantity = coerceNumber(safeLine.quantity);
  const extendedPrice = coerceNumber(safeLine.extended_price);
  const discountAmount = coerceNumber(safeLine.discount_amount);

  const priceSource =
    safeLine.price && typeof safeLine.price === "object" && !Array.isArray(safeLine.price)
      ? { ...safeLine.price }
      : {};

  return {
    ...safeLine,
    quantity,
    extended_price: extendedPrice,
    discount_amount: discountAmount,
    price: {
      ...priceSource,
      sell: coerceNumber(priceSource.sell ?? safeLine.sell_price ?? safeLine.price_sell),
      cost: coerceNumber(priceSource.cost ?? safeLine.cost_price ?? safeLine.price_cost),
    },
  };
};

export const normalizeLineItems = (lines: unknown[]): any[] =>
  Array.isArray(lines) ? lines.map((line) => normalizeLineItem(line)) : [];

export const sanitizeRecord = (record: any, numericKeys: string[] = []) => {
  if (!record || typeof record !== "object" || Array.isArray(record)) {
    return record;
  }

  const numericSet = new Set(numericKeys);
  const sanitizedEntries: Record<string, unknown> = {};

  Object.entries(record).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      sanitizedEntries[key] = value;
      return;
    }

    if (numericSet.has(key)) {
      const numeric = extractNumericValue(value);
      if (numeric !== null) {
        sanitizedEntries[key] = numeric;
        return;
      }
    }

    const primitive = coerceFormValue(value);
    if (primitive === undefined) {
      sanitizedEntries[key] = value;
      return;
    }

    sanitizedEntries[key] = primitive === null ? "" : primitive;
  });

  return { ...record, ...sanitizedEntries };
};

export const formatDateTimeValue = (value: unknown): string => {
  if (value === null || value === undefined || value === "") {
    return "";
  }

  const numeric = extractNumericValue(value);
  if (numeric !== null) {
    const milliseconds = numeric > 1e12 ? numeric : numeric * 1000;
    const date = new Date(milliseconds);
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleString();
  }

  if (typeof value === "string") {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
  }

  return String(value);
};
