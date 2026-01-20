import { useState, useEffect, useMemo } from 'react';

export interface TransactionLine {
  id?: number;
  quantity: number;
  price: number;
  discount_amount?: number;
  extended_price?: number;
  item_name?: string;
  unit_cost?: number;
  line_margin?: number;
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

const defaultTotals: TransactionTotals = {
  subtotal: 0,
  discount: 0,
  taxable: 0,
  tax: 0,
  shipping: 0,
  other: 0,
  total: 0,
  cost: 0,
  margin: 0,
  margin_pc: 0,
  received: 0,
  balance: 0,
};

export const useRealTimeCalculations = (
  lines: TransactionLine[],
  taxRate: number = 0,
  shipping: number = 0,
  other: number = 0,
  received: number = 0
) => {
  const [totals, setTotals] = useState<TransactionTotals>(defaultTotals);

  const calculatedTotals = useMemo(() => {
    // Calculate line totals
    const lineSubtotal = lines.reduce((sum, line) => {
      const extended = line.quantity * line.price;
      const discount = line.discount_amount || 0;
      return sum + (extended - discount);
    }, 0);

    const lineDiscount = lines.reduce((sum, line) => sum + (line.discount_amount || 0), 0);

    // Calculate costs for margin computation
    const totalCost = lines.reduce((sum, line) => {
      return sum + ((line.unit_cost || 0) * line.quantity);
    }, 0);

    // Taxable amount (subtotal - header discount)
    const taxable = lineSubtotal;

    // Tax calculation
    const tax = taxable * taxRate;

    // Grand total
    const total = taxable + tax + shipping + other;

    // Margin calculations
    const margin = total - totalCost;
    const margin_pc = total > 0 ? (margin / total) * 100 : 0;

    // Balance for invoices/payments
    const balance = total - received;

    return {
      subtotal: lineSubtotal,
      discount: lineDiscount,
      taxable,
      tax,
      shipping,
      other,
      total,
      cost: totalCost,
      margin,
      margin_pc,
      received,
      balance,
    };
  }, [lines, taxRate, shipping, other, received]);

  useEffect(() => {
    setTotals(calculatedTotals);
  }, [calculatedTotals]);

  return totals;
};