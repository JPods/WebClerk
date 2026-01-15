import type { ItemSearchResult } from "../types/itemSearchType";

export function parseNumeric(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const cleaned = value.replace(/[,$]/g, "");
    const parsed = Number.parseFloat(cleaned);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

export function resolveItemKey(item: ItemSearchResult): string {
  return (
    (item.id ?? item.item_id ?? item.itemId ?? item.item_num ?? item.itemNum ?? item.ida_item ?? item.sku ?? "")
      ?.toString()
      ?.trim() ?? ""
  );
}

export function resolveItemCode(item: ItemSearchResult): string {
  return (
    item.itemNum ??
    item.item_num ??
    item.ida_item ??
    item.sku ??
    (typeof item.id === "number" ? String(item.id) : "")
  );
}

export function resolveItemDescription(item: ItemSearchResult): string {
  return item.description ?? item.description_text ?? item.name ?? "";
}

export function resolveUnitPrice(item: ItemSearchResult): number {
  // Handle nested JSON structure: price.base, price.retail, etc.
  if (item.price && typeof item.price === "object") {
    const priceObj = item.price as Record<string, unknown>;
    return (
      parseNumeric(priceObj.base) ||
      parseNumeric(priceObj.retail) ||
      parseNumeric(priceObj.unit) ||
      parseNumeric(priceObj.sell) ||
      0
    );
  }
  // Fallback to flat properties
  return (
    parseNumeric(item.price) ||
    parseNumeric(item.priceA) ||
    parseNumeric(item.price_a) ||
    parseNumeric(item.unit_price)
  );
}

export function resolveUnitCost(item: ItemSearchResult): number {
  // Handle nested JSON structure: cost.avg, cost.last, etc.
  if (item.cost && typeof item.cost === "object") {
    const costObj = item.cost as Record<string, unknown>;
    return (
      parseNumeric(costObj.avg) ||
      parseNumeric(costObj.average) ||
      parseNumeric(costObj.last) ||
      parseNumeric(costObj.unit) ||
      0
    );
  }
  // Fallback to flat properties
  return (
    parseNumeric(item.cost) ||
    parseNumeric(item.costA) ||
    parseNumeric(item.unit_cost)
  );
}

export function resolveQtyOnHand(item: ItemSearchResult): number {
  // Handle nested JSON structure: quantity.on_hand
  if (item.quantity && typeof item.quantity === "object") {
    const qtyObj = item.quantity as Record<string, unknown>;
    return (
      parseNumeric(qtyObj.on_hand) ||
      parseNumeric(qtyObj.onHand) ||
      parseNumeric(qtyObj.available) ||
      0
    );
  }
  // Fallback to flat properties
  return parseNumeric(item.qty_on_hand ?? item.qtyOnHand);
}

export function resolveDefaultQuantity(item: ItemSearchResult): number {
  // Resolve a default quantity for adding items - defaults to 1 if none defined
  if (item.quantity && typeof item.quantity === "object") {
    const qtyObj = item.quantity as Record<string, unknown>;
    const resolved = 
      parseNumeric(qtyObj.default) ||
      parseNumeric(qtyObj.min) ||
      parseNumeric(qtyObj.increment) ||
      0;
    return resolved > 0 ? resolved : 1;
  }
  // Fallback to flat properties or default to 1
  const flatQty = parseNumeric(item.default_quantity ?? item.defaultQuantity ?? item.min_quantity);
  return flatQty > 0 ? flatQty : 1;
}
