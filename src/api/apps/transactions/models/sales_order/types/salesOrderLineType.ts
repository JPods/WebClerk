export interface SalesOrderLine {
  id?: number;
  parent?: number; // sales_order id
  item_id?: number;
  item_name?: string;
  description: string;
  quantity: number;
  price: {
    sell: number;
    cost: number;
  };
  discount_amount: number;
  extended_price?: number;
  unit_cost?: number;
  line_margin?: number;
  dt_created?: string | number;
  dt_modified?: string | number;
}

export interface CreateSalesOrderLineRequest {
  parent: number;
  item_id?: number;
  item_name?: string;
  description: string;
  quantity: number;
  price: {
    sell: number;
    cost: number;
  };
  discount_amount?: number;
}

export interface UpdateSalesOrderLineRequest {
  id: number;
  parent: number;
  item_id?: number;
  item_name?: string;
  description: string;
  quantity: number;
  price: {
    sell: number;
    cost: number;
  };
  discount_amount?: number;
}
