export interface ItemSearchResult {
  id?: number;
  item_id?: number;
  itemId?: number;
  item_num?: string;
  itemNum?: string;
  ida_item?: string;
  sku?: string;
  description?: string;
  description_text?: string;
  name?: string;
  // Price can be a flat value or a nested JSON object (price.base, price.retail, etc.)
  price?: number | string | Record<string, unknown>;
  priceA?: number | string;
  price_a?: number | string;
  unit_price?: number | string;
  unit_cost?: number | string;
  // Cost can be a flat value or a nested JSON object (cost.avg, cost.last, etc.)
  cost?: number | string | Record<string, unknown>;
  costA?: number | string;
  // Quantity can be a flat value or a nested JSON object (quantity.on_hand, etc.)
  quantity?: number | string | Record<string, unknown>;
  qty_on_hand?: number | string;
  qtyOnHand?: number | string;
  unit_of_measure?: string;
  unitOfMeasure?: string;
  unit_measure?: string;
  imagePath?: string;
  image_url?: string;
  photo_url?: string;
  key_tags?: string;
  keyTags?: string;
  [key: string]: unknown;
}
