export interface InvoiceLine {
  id?: number;
  parent?: number; // invoice id
  item_id?: number;
  item_name?: string;
  description: string;
  quantity: number;
  price: {
    sell: number;
    cost: number;
    unit?: number;
    discount_amount?: number;
    discount_percent?: number;
    precision?: number;
    extended?: number;
  };
  discount_amount: number;
  extended_price?: number;
  unit_cost?: number;
  line_margin?: number;
  dt_created?: string | number;
  dt_modified?: string | number;
}

export interface CreateInvoiceLineRequest {
  parent: number;
  item_id?: number;
  item_name?: string;
  description: string;
  quantity: number;
  price: {
    sell: number;
    cost: number;
    unit?: number;
    discount_amount?: number;
    discount_percent?: number;
    precision?: number;
    extended?: number;
  };
  discount_amount?: number;
}

export interface UpdateInvoiceLineRequest {
  id: number;
  parent: number;
  item_id?: number;
  item_name?: string;
  description: string;
  quantity: number;
  price: {
    sell: number;
    cost: number;
    unit?: number;
    discount_amount?: number;
    discount_percent?: number;
    precision?: number;
    extended?: number;
  };
  discount_amount?: number;
}
