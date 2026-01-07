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
  return (
    parseNumeric(item.price) ||
    parseNumeric(item.priceA) ||
    parseNumeric(item.price_a) ||
    parseNumeric(item.unit_price)
  );
}

export function resolveUnitCost(item: ItemSearchResult): number {
  return (
    parseNumeric(item.cost) ||
    parseNumeric(item.costA) ||
    parseNumeric(item.unit_cost)
  );
}

export function resolveQtyOnHand(item: ItemSearchResult): number {
  return parseNumeric(item.qty_on_hand ?? item.qtyOnHand);
}
