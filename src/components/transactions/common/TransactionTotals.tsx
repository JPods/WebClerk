/**
 * TransactionTotals — Display component for the three-envelope totals shape
 * returned by computeHeaderTotals / useRealTimeCalculations.
 *
 * Aligned with the WC3 backend sell/cost/totals JSON structure.
 *
 * @see webClerk3/readmes/topics/transactions/transactions-totals.md §3
 */
import React from 'react';
import type {
  TransactionTotals as TotalsType,
  HeaderCost,
  HeaderSell,
} from '../../../apps/transactions/types/transactionTypes';
import {
  formatCurrency,
  formatPercent,
} from '../../../apps/transactions/services/calculationUtils';

export interface TransactionTotalsProps {
  sell?: HeaderSell;
  cost?: HeaderCost;
  totals: TotalsType;
  currency?: string;
  showBalance?: boolean;
  /** Show sell breakdown (sales-side only) */
  showSell?: boolean;
}

export const TransactionTotals: React.FC<TransactionTotalsProps> = ({
  sell,
  cost,
  totals,
  currency = 'USD',
  showBalance = false,
  showSell = true,
}) => {
  return (
    <div className="transaction-totals bg-gray-50 p-6 rounded-lg border">
      <h3 className="text-lg font-semibold mb-4 text-gray-800">Transaction Totals</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Revenue Section */}
        <div className="bg-white p-4 rounded border">
          <h4 className="text-sm font-medium text-gray-600 mb-2">Revenue</h4>
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Subtotal:</span>
              <span className="font-medium">{formatCurrency(totals.subtotal)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Discount:</span>
              <span className="font-medium text-red-600">-{formatCurrency(totals.discount)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Taxable:</span>
              <span className="font-medium">{formatCurrency(totals.taxable)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Tax:</span>
              <span className="font-medium">{formatCurrency(totals.tax)}</span>
            </div>
          </div>
        </div>

        {/* Additional Charges */}
        <div className="bg-white p-4 rounded border">
          <h4 className="text-sm font-medium text-gray-600 mb-2">Additional</h4>
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Shipping:</span>
              <span className="font-medium">{formatCurrency(totals.shipping)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Other:</span>
              <span className="font-medium">{formatCurrency(totals.other)}</span>
            </div>
            <div className="flex justify-between border-t pt-1 mt-2">
              <span className="text-sm font-medium text-gray-800">Total:</span>
              <span className="font-bold text-lg text-green-600">{formatCurrency(totals.total)}</span>
            </div>
          </div>
        </div>

        {/* Cost & Margin */}
        <div className="bg-white p-4 rounded border">
          <h4 className="text-sm font-medium text-gray-600 mb-2">Cost & Margin</h4>
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Total Cost:</span>
              <span className="font-medium">{formatCurrency(totals.cost)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Margin:</span>
              <span className={`font-medium ${totals.margin >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatCurrency(totals.margin)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Margin %:</span>
              <span className={`font-medium ${totals.margin_pc >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatPercent(totals.margin_pc)}
              </span>
            </div>
          </div>
        </div>

        {/* Payment Status */}
        {showBalance && (
          <div className="bg-white p-4 rounded border">
            <h4 className="text-sm font-medium text-gray-600 mb-2">Payment Status</h4>
            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Received:</span>
                <span className="font-medium text-green-600">{formatCurrency(totals.received || 0)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Balance:</span>
                <span className={`font-medium ${(totals.balance || 0) <= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(totals.balance || 0)}
                </span>
              </div>
              <div className="flex justify-between border-t pt-1 mt-2">
                <span className="text-sm font-medium text-gray-800">Status:</span>
                <span className={`font-bold ${(totals.balance || 0) <= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {(totals.balance || 0) <= 0 ? 'Paid' : 'Outstanding'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Summary Bar */}
      <div className="mt-6 bg-blue-50 p-4 rounded-lg border border-blue-200">
        <div className="flex justify-between items-center">
          <div className="text-sm text-blue-800">
            <span className="font-medium">Grand Total: </span>
            <span className="text-xl font-bold text-blue-900">{formatCurrency(totals.total)}</span>
          </div>
          {totals.margin_pc !== undefined && (
            <div className="text-sm text-blue-800">
              <span className="font-medium">Profit Margin: </span>
              <span className={`text-xl font-bold ${totals.margin_pc >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatPercent(totals.margin_pc)}
              </span>
            </div>
          )}
          {showBalance && totals.balance !== undefined && (
            <div className="text-sm text-blue-800">
              <span className="font-medium">Balance Due: </span>
              <span className={`text-xl font-bold ${(totals.balance || 0) <= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatCurrency(totals.balance || 0)}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};