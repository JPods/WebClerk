import { useMemo } from 'react';

export interface TransactionLine {
  id?: number;
  item_name: string;
  description: string;
  quantity: number;
  price: number;
  // Add other fields as needed
}

export interface TransactionTotals {
  subtotal: number;
  discount: number;
  taxable: number;
  tax: number;
  shipping: number;
  other: number;
  total: number;
  cost: number;
  margin: number;
  margin_pc: number;
  received?: number;
  balance?: number;
}

export function useRealTimeCalculations(
  lines: TransactionLine[],
  taxRate: number = 0.08,
  shipping: number = 0,
  other: number = 0
): TransactionTotals {
  return useMemo(() => {
    const subtotal = lines.reduce((sum, line) => sum + (line.quantity * line.price), 0);
    const discount = 0; // TODO: Implement discount logic
    const taxable = subtotal - discount;
    const tax = taxable * taxRate;
    const total = taxable + tax + shipping + other;
    const cost = 0; // TODO: Implement cost calculation
    const margin = total - cost;
    const margin_pc = cost > 0 ? (margin / cost) * 100 : 0;

    return {
      subtotal,
      discount,
      taxable,
      tax,
      shipping,
      other,
      total,
      cost,
      margin,
      margin_pc,
    };
  }, [lines, taxRate, shipping, other]);
}