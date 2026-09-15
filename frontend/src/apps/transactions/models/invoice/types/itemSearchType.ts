/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
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
  price?: number | string;
  priceA?: number | string;
  price_a?: number | string;
  unit_price?: number | string;
  unit_cost?: number | string;
  cost?: number | string;
  costA?: number | string;
  qty_on_hand?: number | string;
  qtyOnHand?: number | string;
  unit_of_measure?: string;
  unitOfMeasure?: string;
  unit_measure?: string;
  imagePath?: string;
  image_url?: string;
  photo_url?: string;
  [key: string]: unknown;
}
