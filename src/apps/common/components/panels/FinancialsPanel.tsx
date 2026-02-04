/**
 * FinancialsPanel - Display financial summary for transactions
 * 
 * Role-based access:
 * - View: All roles (default)
 * - Edit: Manager+ roles (default)
 */
import React, { useState } from 'react';
import { 
  FaDollarSign, FaChevronDown, FaChevronUp, FaPercent, FaCalculator,
  FaCreditCard, FaFileInvoice, FaMoneyCheckAlt
} from 'react-icons/fa';
import { usePermissions } from './usePermissions';
import type { BasePanelProps, FinancialSummary } from './types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FinancialsPanelProps extends Omit<BasePanelProps<FinancialSummary>, 'data'> {
  /** Financial summary data */
  data?: FinancialSummary;
  /** Currency code (default: USD) */
  currency?: string;
  /** Show detailed breakdown */
  showBreakdown?: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const formatCurrency = (value: number | undefined, currency: string = 'USD'): string => {
  if (value === undefined || value === null) return '--';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

const formatPercent = (value: number | undefined): string => {
  if (value === undefined || value === null) return '--';
  return `${value.toFixed(2)}%`;
};

// ---------------------------------------------------------------------------
// Line Item Component
// ---------------------------------------------------------------------------

interface LineItemProps {
  label: string;
  value: string;
  icon?: React.ReactNode;
  isTotal?: boolean;
  isSubtotal?: boolean;
  isNegative?: boolean;
  indent?: boolean;
}

const LineItem: React.FC<LineItemProps> = ({ 
  label, 
  value, 
  icon, 
  isTotal = false, 
  isSubtotal = false,
  isNegative = false,
  indent = false,
}) => (
  <div className={`flex items-center justify-between py-1.5 ${
    isTotal ? 'border-t-2 border-slate-300 dark:border-slate-600 mt-2 pt-2' :
    isSubtotal ? 'border-t border-slate-200 dark:border-slate-700 mt-1 pt-1' : ''
  } ${indent ? 'pl-4' : ''}`}>
    <div className="flex items-center gap-2 text-sm">
      {icon && <span className="text-slate-400">{icon}</span>}
      <span className={`${isTotal ? 'font-semibold text-slate-700 dark:text-slate-200' : 'text-slate-600 dark:text-slate-400'}`}>
        {label}
      </span>
    </div>
    <span className={`text-sm font-mono ${
      isTotal ? 'font-bold text-slate-800 dark:text-slate-100' :
      isNegative ? 'text-red-600' :
      'text-slate-700 dark:text-slate-300'
    }`}>
      {isNegative && value !== '--' ? `(${value})` : value}
    </span>
  </div>
);

// ---------------------------------------------------------------------------
// Payment Summary Component
// ---------------------------------------------------------------------------

interface PaymentSummaryProps {
  financials: FinancialSummary;
  currency: string;
}

const PaymentSummary: React.FC<PaymentSummaryProps> = ({ financials, currency }) => {
  const payments = financials.payments || [];
  const totalPaid = payments.reduce((sum, p) => sum + (p.amount || 0), 0);
  const balance = (financials.total || 0) - totalPaid;

  if (payments.length === 0 && !financials.balance_due) return null;

  return (
    <div className="mt-4 pt-3 border-t border-slate-200 dark:border-slate-700">
      <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1">
        <FaCreditCard size={10} />
        Payments
      </h4>
      
      {payments.map((payment, idx) => (
        <div key={idx} className="flex justify-between text-xs py-1 text-slate-600 dark:text-slate-400">
          <span className="flex items-center gap-1">
            {payment.method || 'Payment'} 
            {payment.date && <span className="text-slate-400">({new Date(payment.date).toLocaleDateString()})</span>}
          </span>
          <span className="text-green-600">{formatCurrency(payment.amount, currency)}</span>
        </div>
      ))}

      <div className="flex justify-between text-sm pt-1 mt-1 border-t border-dashed border-slate-200 dark:border-slate-700">
        <span className="font-medium text-slate-700 dark:text-slate-300">Balance Due</span>
        <span className={`font-mono font-semibold ${balance > 0 ? 'text-amber-600' : 'text-green-600'}`}>
          {formatCurrency(financials.balance_due ?? balance, currency)}
        </span>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main FinancialsPanel Component
// ---------------------------------------------------------------------------

const FinancialsPanel: React.FC<FinancialsPanelProps> = ({
  entityType: _entityType,
  entityId: _entityId,
  data,
  onChange: _onChange,
  readOnly: _readOnly = false,
  viewRoles,
  editRoles,
  className = '',
  compact = false,
  title = 'Financial Summary',
  defaultCollapsed = false,
  currency = 'USD',
  showBreakdown = true,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [showDetails, setShowDetails] = useState(!compact);

  // Check permissions
  const { canView } = usePermissions({
    panelType: 'financials',
    viewRoles,
    editRoles,
    forceReadOnly: true, // Financials are typically display-only at panel level
  });

  if (!canView) return null;

  // Default empty state
  const financials = data || {};
  const hasData = financials.total !== undefined || financials.subtotal !== undefined;

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-lg border border-green-200 dark:border-green-800 ${className}`}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-green-50 dark:bg-green-900/20 border-b border-green-200 dark:border-green-800 cursor-pointer rounded-t-lg"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaDollarSign className="text-green-500" size={14} />
          <h3 className="text-sm font-semibold text-green-700 dark:text-green-300">{title}</h3>
          {!isCollapsed && hasData && (
            <span className="px-2 py-0.5 text-xs bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded font-mono">
              {formatCurrency(financials.total, currency)}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
        </div>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className={compact ? 'p-2' : 'p-4'}>
          {!hasData ? (
            <div className="text-center py-4 text-slate-400 text-sm">
              <FaCalculator size={24} className="mx-auto mb-2 opacity-50" />
              <p>No financial data</p>
            </div>
          ) : (
            <>
              {/* Quick summary */}
              {!showDetails && (
                <div className="flex justify-between items-center">
                  <span className="text-lg font-semibold text-slate-700 dark:text-slate-200">
                    Total
                  </span>
                  <span className="text-xl font-mono font-bold text-green-600">
                    {formatCurrency(financials.total, currency)}
                  </span>
                </div>
              )}

              {/* Detailed breakdown */}
              {showDetails && showBreakdown && (
                <div className="space-y-0.5">
                  {/* Line items / Subtotal */}
                  <LineItem 
                    label="Subtotal" 
                    value={formatCurrency(financials.subtotal, currency)}
                    icon={<FaFileInvoice size={12} />}
                  />

                  {/* Discounts */}
                  {(financials.discount_amount || financials.discount_percent) && (
                    <LineItem 
                      label={`Discount ${financials.discount_percent ? `(${formatPercent(financials.discount_percent)})` : ''}`}
                      value={formatCurrency(financials.discount_amount, currency)}
                      icon={<FaPercent size={12} />}
                      isNegative
                      indent
                    />
                  )}

                  {/* Tax */}
                  {(financials.tax_amount || financials.tax_percent) && (
                    <LineItem 
                      label={`Tax ${financials.tax_percent ? `(${formatPercent(financials.tax_percent)})` : ''}`}
                      value={formatCurrency(financials.tax_amount, currency)}
                      indent
                    />
                  )}

                  {/* Shipping */}
                  {financials.shipping_amount !== undefined && (
                    <LineItem 
                      label="Shipping"
                      value={formatCurrency(financials.shipping_amount, currency)}
                      indent
                    />
                  )}

                  {/* Handling */}
                  {financials.handling_amount !== undefined && (
                    <LineItem 
                      label="Handling"
                      value={formatCurrency(financials.handling_amount, currency)}
                      indent
                    />
                  )}

                  {/* Total */}
                  <LineItem 
                    label="Total" 
                    value={formatCurrency(financials.total, currency)}
                    icon={<FaMoneyCheckAlt size={12} />}
                    isTotal
                  />

                  {/* Currency note if not USD */}
                  {currency !== 'USD' && (
                    <div className="text-xs text-slate-400 text-right mt-1">
                      Currency: {currency}
                    </div>
                  )}
                </div>
              )}

              {/* Minimal view (no breakdown) */}
              {showDetails && !showBreakdown && (
                <LineItem 
                  label="Total" 
                  value={formatCurrency(financials.total, currency)}
                  icon={<FaMoneyCheckAlt size={12} />}
                  isTotal
                />
              )}

              {/* Payment info */}
              <PaymentSummary financials={financials} currency={currency} />

              {/* Toggle details */}
              {!compact && showBreakdown && (
                <button
                  onClick={() => setShowDetails(!showDetails)}
                  className="w-full text-center text-xs text-blue-600 hover:underline mt-3"
                >
                  {showDetails ? 'Show less' : 'Show breakdown'}
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default FinancialsPanel;
