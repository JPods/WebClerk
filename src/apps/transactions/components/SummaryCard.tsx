/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React from "react";
import { useAppSelector } from '@/store/hooks';
import FieldLabel from "../components/FieldLabel";
import { Input } from "../../../components/wrapper";
import Select from "@/components/form/Select";
import CustomerSalesPanel, { type CustomerSelectionData, type OrgLinkSnapshot } from "./CustomerSalesPanel";
import InternationalPhoneInput from "@/components/form/input/InternationalPhoneInput";

// Inline StatusBadge (copied from OrderDetail)
const StatusBadge: React.FC<{ status?: string }> = ({ status }) => {
  const statusStyles: Record<string, string> = {
    planned:
      "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
    released:
      "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    in_progress:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    hold: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
    complete:
      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    canceled: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  };
  return (
    <span
      className={`px-2 py-1 text-xs font-medium rounded-full ${
        statusStyles[status ?? "planned"] ?? statusStyles.planned
      }`}
    >
      {status?.replace("_", " ") ?? "planned"}
    </span>
  );
};
import { FaLock, FaShoppingCart, FaMoneyBillWave, FaUser } from "react-icons/fa";
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { formatDt } from '@/utils/fieldFormatters';

interface SummaryCardProps {
  data: any;
  isEditing: boolean;
  onChange?: (field: any, value: unknown) => void;
  priceLable?: Array<{ label: string; value: string }>;
  customerInfo: any;
  billingContact: any;
  shippingContact: any;
  /** Transaction type label (e.g., "Order", "Proposal", "Invoice") */
  transactionLabel?: string;
  /** Field label for the main document number (e.g., "Order No", "Proposal No") */
  documentNoLabel?: string;
  /** Field label for due/expiry date (e.g., "Due Date", "Valid Until") */
  dueDateLabel?: string;
  /** Whether to show shipping section */
  showShipping?: boolean;
  /** Whether to show cost/margin in totals */
  showCostMargin?: boolean;
  /** Label for the org section — "Customer", "Vendor", etc. Default: "Customer" */
  orgLabel?: string;
  /** Field name for the org ID — "customer_id", "vendor_id", etc. Default: "customer_id" */
  orgIdField?: string;
  /** Whether to show payments section (received/balance) */
  showPayments?: boolean;
  /** Callback when Add Payment button is clicked */
  onAddPayment?: () => void;
  /** Whether to use the enhanced CustomerSalesPanel (default: true) */
  useCustomerSalesPanel?: boolean;
  /** Callback when customer is selected via CustomerSalesPanel - transfers terms/price_level */
  onCustomerSelect?: (data: CustomerSelectionData | null) => void;
  /** Denormalized org snapshots from refs.links */
  orgLinks?: { customer?: OrgLinkSnapshot | null; vendor?: OrgLinkSnapshot | null; manufacturer?: OrgLinkSnapshot | null };
}
// Utility functions
const formatCurrency = (value?: number | null): string => {
  if (value === undefined || value === null) return "--";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
};

const formatNumber = (value?: number | null): string => {
  if (value === undefined || value === null) return "--";
  return value.toLocaleString();
};

const SummaryCard: React.FC<SummaryCardProps> = ({
  data,
  isEditing,
  onChange,
  priceLable = [],
  customerInfo,
  billingContact,
  shippingContact,
  transactionLabel = "Order",
  documentNoLabel = "Order No",
  dueDateLabel = "Due Date",
  showShipping = true,
  showCostMargin = true,
  orgLabel = 'Customer',
  orgIdField = 'customer_id',
  showPayments = false,
  onAddPayment,
  useCustomerSalesPanel = true,
  onCustomerSelect,
  orgLinks,
}) => {
  const authUser = useAppSelector((s) => s.auth.user);
  const isStaff = authUser?.is_staff || authUser?.is_superuser || false;
  const statusOptions = [
    { value: "planned", label: "planned" },
    { value: "released", label: "released" },
    { value: "in_progress", label: "in_progress" },
    { value: "hold", label: "hold" },
    { value: "complete", label: "complete" },
    { value: "canceled", label: "canceled" },
  ];

  // Handle customer selection from CustomerSalesPanel
  const handleCustomerSelect = (selectionData: CustomerSelectionData | null) => {
    if (onCustomerSelect) {
      onCustomerSelect(selectionData);
    }
    // Also update individual fields via onChange if provided
    if (onChange && selectionData) {
      onChange("customer_id", selectionData.customer.id);
      // Transfer terms and price_level if customer provides them and they're not already set
      if (selectionData.terms && !data.terms) {
        onChange("terms", selectionData.terms);
      }
      if (selectionData.price_level && !data.price_level) {
        onChange("price_level", selectionData.price_level);
      }
    } else if (onChange && !selectionData) {
      onChange("customer_id", null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Sales Order Header Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Order Details */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaShoppingCart className="text-blue-500" />
            {transactionLabel}
          </h3>
          <dl className="space-y-3 text-xs">
            <div className="flex justify-between items-center">
              <FieldLabel
                model={transactionLabel.toLowerCase()}
                label="ida"
                mandatory
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono font-medium text-slate-900 dark:text-white">
                {data.ida ?? "--"}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                model={transactionLabel.toLowerCase()}
                label="id"
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-slate-600 dark:text-slate-300">
                {data.id ?? "--"}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                model={transactionLabel.toLowerCase()}
                label="dt_created"
                mandatory
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <Input
                  type="date"
                  value={
                    data.dt ? new Date(data.dt).toISOString().split("T")[0] : ""
                  }
                  onChange={(e) => onChange("dt", e.target.value)}
                  className="px-2 py-1 rounded text-xs bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.dt ? formatDt(data.dt, 'date', 'dt') : "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                model={transactionLabel.toLowerCase()}
                label="due_date"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <Input
                  type="date"
                  value={
                    data.due_date
                      ? new Date(data.due_date).toISOString().split("T")[0]
                      : ""
                  }
                  onChange={(e) => onChange("due_date", e.target.value)}
                  className="px-2 py-1 rounded text-xs bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.due_date
                    ? formatDt(data.due_date, 'date', 'due_date')
                    : "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                model={transactionLabel.toLowerCase()}
                label="terms"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <Input
                  type="text"
                  value={data.terms ?? ""}
                  onChange={(e) => onChange("terms", e.target.value)}
                  className="px-2 py-1  rounded text-xs bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.terms ?? "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                model={transactionLabel.toLowerCase()}
                label="po_number"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <Input
                  type="text"
                  value={data.po_number ?? data.reference ?? ""}
                  onChange={(e) => onChange("po_number", e.target.value)}
                  className="px-2 py-1 rounded text-xs bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.po_number ?? data.reference ?? "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                model={transactionLabel.toLowerCase()}
                label="priority"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <Input
                  type="text"
                  value={data.priority ?? ""}
                  onChange={(e) => onChange("priority", e.target.value)}
                  className="px-2 py-1 rounded text-xs bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.priority ?? "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                model={transactionLabel.toLowerCase()}
                label="price_level"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <Select
                  options={priceLable}
                  placeholder="Select Price Level"
                  value={data.price_level ?? ""}
                  onChange={(value: string) => onChange("price_level", value)}
                  className="dark:bg-dark-900"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.price_level ?? "--"}
                </dd>
              )}
            </div>
            {/* Denormalized contact fields */}
            {data.attention && (
              <div className="flex justify-between items-center">
                <FieldLabel
                  label="attention"
                  className="text-slate-500 dark:text-slate-400"
                />
                {isEditing && onChange ? (
                  <Input
                    type="text"
                    value={data.attention ?? ""}
                    onChange={(e) => onChange("attention", e.target.value)}
                    className="px-2 py-1 rounded text-xs bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                  />
                ) : (
                  <dd className="text-slate-900 dark:text-white">
                    {data.attention ?? "--"}
                  </dd>
                )}
              </div>
            )}
            {data.email && (
              <div className="flex justify-between items-center">
                <FieldLabel
                  label="email"
                  className="text-slate-500 dark:text-slate-400"
                />
                {isEditing && onChange ? (
                  <Input
                    type="email"
                    value={data.email ?? ""}
                    onChange={(e) => onChange("email", e.target.value)}
                    className="px-2 py-1 rounded text-xs bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                  />
                ) : (
                  <dd className="text-slate-900 dark:text-white">
                    {data.email ?? "--"}
                  </dd>
                )}
              </div>
            )}
            {data.phone && (
              <div className="flex justify-between items-center">
                <FieldLabel
                  label="phone"
                  className="text-slate-500 dark:text-slate-400"
                />
                {isEditing && onChange ? (
                  <InternationalPhoneInput
                    value={data.phone ?? ""}
                    onChange={(value) => onChange("phone", value)}
                    className="w-45"
                  />
                ) : (
                  <dd className="text-slate-900 dark:text-white">
                    {data.phone ?? "--"}
                  </dd>
                )}
              </div>
            )}
            {data.address_full && (
              <div className="flex justify-between items-center">
                <FieldLabel
                  label="address_full"
                  className="text-slate-500 dark:text-slate-400"
                />
                {isEditing && onChange ? (
                  <Input
                    type="text"
                    value={data.address_full ?? ""}
                    onChange={(e) => onChange("address_full", e.target.value)}
                    className="px-2 py-1 rounded text-xs bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                  />
                ) : (
                  <dd className="text-slate-900 dark:text-white truncate max-w-[200px]" title={data.address_full}>
                    {data.address_full ?? "--"}
                  </dd>
                )}
              </div>
            )}
            <div className="flex justify-between items-center">
              <FieldLabel
                model={transactionLabel.toLowerCase()}
                label="status"
                mandatory
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <Select
                  options={statusOptions}
                  placeholder="Select Status"
                  value={data.status ?? "planned"}
                  onChange={(value: string) => onChange("status", value)}
                  className="dark:bg-dark-900"
                />
              ) : (
                <dd>
                  <StatusBadge status={data.status} />
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                model={transactionLabel.toLowerCase()}
                label="customer_ida"
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-slate-600 dark:text-slate-300">
                {data.customer_ida ?? data.refs?.links?.customer?.[0]?.ida ?? "--"}
              </dd>
            </div>
            {data.is_locked && (
              <div className="flex justify-between items-center pt-2 mt-2 border-t border-slate-200 dark:border-slate-700">
                <FieldLabel
                  label="is_locked"
                  locked
                  className="text-slate-500 dark:text-slate-400"
                />
                <dd className="flex items-center gap-1 text-amber-600 dark:text-amber-400 font-medium">
                  <FaLock size={12} />
                  <span>Yes</span>
                </dd>
              </div>
            )}
          </dl>
        </div>

        {/* Center: Customer Info - uses CustomerSalesPanel for enhanced search/display */}
        {useCustomerSalesPanel ? (
          <CustomerSalesPanel
            value={(data as any)[orgIdField] ?? data.customer_id ?? customerInfo?.id ?? null}
            onSelect={handleCustomerSelect}
            isEditing={isEditing}
            showFinancials={true}
            title={orgLabel}
            className="h-full"
            initialData={orgIdField === 'vendor_id' ? (orgLinks?.vendor ?? customerInfo ?? null) : (orgLinks?.customer ?? null)}
          />
        ) : (
          <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
            <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <FaUser className="text-blue-500" />
              {orgLabel}
            </h3>
            {/* Legacy customer display */}
            {customerInfo ? (
              <dl className="space-y-3 text-xs">
                <div className="flex justify-between items-center">
                  <FieldLabel
                    label="customer_id"
                    locked
                    className="text-slate-500 dark:text-slate-400"
                  />
                  <dd className="font-mono text-slate-600 dark:text-slate-300">
                    {data.customer_id ?? "--"}
                  </dd>
                </div>
                <div className="flex justify-between items-center">
                  <FieldLabel
                    label="display_name"
                    className="text-slate-500 dark:text-slate-400"
                  />
                  <dd className="text-slate-900 dark:text-white">
                    {customerInfo.display_name ?? "--"}
                  </dd>
                </div>
                <div className="flex justify-between items-center">
                  <FieldLabel
                    label="ida"
                    className="text-slate-500 dark:text-slate-400"
                  />
                  <dd className="font-mono text-slate-600 dark:text-slate-300">
                    {customerInfo.ida ?? "--"}
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="text-slate-400 text-xs">No customer linked</p>
            )}

            {billingContact && (
              <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
                <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                  Bill To
                </h4>
                <p className="text-xs text-slate-900 dark:text-white">
                  {billingContact.display_name}
                </p>
                {billingContact.email && (
                  <p className="text-xs text-slate-600 dark:text-slate-300">
                    {Array.isArray(billingContact.email)
                      ? billingContact.email
                          .map((e: any) =>
                            typeof e === "string" ? e : e?.full || e?.value || "",
                          )
                          .filter(Boolean)
                          .join(", ")
                      : typeof billingContact.email === "object" &&
                        billingContact.email !== null
                      ? billingContact.email.full ||
                        billingContact.email.value ||
                        ""
                      : billingContact.email}
                  </p>
                )}
                {billingContact.phone && (
                  <p className="text-xs text-slate-600 dark:text-slate-300">
                    {Array.isArray(billingContact.phone)
                      ? billingContact.phone
                          .map((p: any) =>
                            typeof p === "string" ? p : p?.full || p?.value || "",
                          )
                          .filter(Boolean)
                          .join(", ")
                      : typeof billingContact.phone === "object" &&
                        billingContact.phone !== null
                      ? billingContact.phone.full ||
                        billingContact.phone.value ||
                        ""
                      : billingContact.phone}
                  </p>
                )}
              </div>
            )}

            {shippingContact && (
              <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
                <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                  Ship To
                </h4>
                <p className="text-xs text-slate-900 dark:text-white">
                  {shippingContact.display_name}
                </p>
                {shippingContact.email && (
                  <p className="text-xs text-slate-600 dark:text-slate-300">
                    {Array.isArray(shippingContact.email)
                      ? shippingContact.email
                          .map((e: any) =>
                            typeof e === "string" ? e : e?.full || e?.value || "",
                          )
                          .filter(Boolean)
                          .join(", ")
                      : typeof shippingContact.email === "object" &&
                        shippingContact.email !== null
                      ? shippingContact.email.full ||
                        shippingContact.email.value ||
                        ""
                      : shippingContact.email}
                  </p>
                )}
                {shippingContact.phone && (
                  <p className="text-xs text-slate-600 dark:text-slate-300">
                    {Array.isArray(shippingContact.phone)
                      ? shippingContact.phone
                          .map((p: any) =>
                            typeof p === "string" ? p : p?.full || p?.value || "",
                          )
                          .filter(Boolean)
                          .join(", ")
                      : typeof shippingContact.phone === "object" &&
                        shippingContact.phone !== null
                      ? shippingContact.phone.full ||
                        shippingContact.phone.value ||
                        ""
                      : shippingContact.phone}
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Right: Totals */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
            {transactionLabel} Totals
          </h3>
          <dl className="space-y-3 text-xs">
            {/* --- sell envelope --- */}
            <div className="flex justify-between items-center">
              <FieldLabel
                model={transactionLabel.toLowerCase()}
                label="sell.line_sum_goods"
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-slate-900 dark:text-white">
                {formatCurrency(data.sell?.line_sum_goods ?? data.totals?.subtotal)}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                model={transactionLabel.toLowerCase()}
                label="sell.discount"
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-red-600 dark:text-red-400">
                {(data.sell?.discount ?? data.totals?.discount)
                  ? `-${formatCurrency(data.sell?.discount ?? data.totals?.discount)}`
                  : "--"}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                model={transactionLabel.toLowerCase()}
                label="sell.total"
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-slate-900 dark:text-white">
                {formatCurrency(data.sell?.total ?? data.totals?.subtotal)}
              </dd>
            </div>

            {/* --- totals envelope --- */}
            <div className="flex justify-between items-center pt-2 border-t border-slate-200 dark:border-slate-700">
              <FieldLabel
                model={transactionLabel.toLowerCase()}
                label="totals.taxable"
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.taxable)}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                model={transactionLabel.toLowerCase()}
                label="totals.tax"
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.tax ?? data.tax)}
              </dd>
            </div>
            {showShipping && (
              <div className="flex justify-between items-center">
                <FieldLabel
                  label="totals.shipping"
                  className="text-slate-500 dark:text-slate-400"
                />
                <dd className="font-mono text-slate-900 dark:text-white">
                  {formatCurrency(data.totals?.shipping)}
                </dd>
              </div>
            )}
            <div className="flex justify-between items-center">
              <FieldLabel
                model={transactionLabel.toLowerCase()}
                label="totals.other"
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.other)}
              </dd>
            </div>
            <div className="flex justify-between items-center pt-2 border-t-2 border-slate-300 dark:border-slate-600">
              <FieldLabel
                model={transactionLabel.toLowerCase()}
                label="totals.total"
                mandatory
                locked
                className="text-slate-700 dark:text-slate-200 text-base"
              />
              <dd className="text-lg font-bold text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.total)}
              </dd>
            </div>

            {/* --- cost envelope --- */}
            {showCostMargin && (
              <>
                <div className="flex justify-between items-center pt-2 border-t border-slate-200 dark:border-slate-700">
                  <FieldLabel
                    label="cost.line_sum_goods"
                    locked
                    className="text-slate-500 dark:text-slate-400"
                  />
                  <dd className="font-mono text-slate-600 dark:text-slate-400">
                    {formatCurrency(data.cost?.line_sum_goods)}
                  </dd>
                </div>
                <div className="flex justify-between items-center">
                  <FieldLabel
                    label="cost.freight"
                    locked
                    className="text-slate-500 dark:text-slate-400"
                  />
                  <dd className="font-mono text-slate-600 dark:text-slate-400">
                    {formatCurrency(data.cost?.freight)}
                  </dd>
                </div>
                {isStaff && (
                <div className="flex justify-between items-center">
                  <FieldLabel
                    label="cost.commissions"
                    locked
                    className="text-slate-500 dark:text-slate-400"
                  />
                  <dd className="font-mono text-slate-600 dark:text-slate-400">
                    {formatCurrency(data.cost?.commissions)}
                  </dd>
                </div>
                )}
                <div className="flex justify-between items-center">
                  <FieldLabel
                    label="cost.total"
                    locked
                    className="text-slate-500 dark:text-slate-400"
                  />
                  <dd className="font-mono text-slate-600 dark:text-slate-400">
                    {formatCurrency(data.cost?.total ?? data.totals?.cost)}
                  </dd>
                </div>

                {/* --- margin --- */}
                <div className="flex justify-between items-center pt-2 border-t border-slate-200 dark:border-slate-700">
                  <FieldLabel
                    label="totals.margin"
                    locked
                    className="text-slate-500 dark:text-slate-400"
                  />
                  <dd
                    className={`font-mono ${
                      (data.totals?.margin ?? 0) >= 0
                        ? "text-green-600 dark:text-green-400"
                        : "text-red-600 dark:text-red-400"
                    }`}
                  >
                    {formatCurrency(data.totals?.margin)}
                    {data.totals?.margin_pc != null && (
                      <span className="ml-1 text-xs">
                        ({data.totals.margin_pc.toFixed(1)}%)
                      </span>
                    )}
                  </dd>
                </div>
              </>
            )}

            {/* --- payments --- */}
            {showPayments && (
              <>
                <div className="flex justify-between items-center pt-2 border-t border-slate-200 dark:border-slate-700">
                  <FieldLabel
                    label="totals.received"
                    locked
                    className="text-slate-500 dark:text-slate-400"
                  />
                  <dd className="font-mono text-green-600 dark:text-green-400">
                    {formatCurrency(data.totals?.received)}
                  </dd>
                </div>
                <div className="flex justify-between items-center">
                  <FieldLabel
                    label="totals.balance"
                    locked
                    className="text-slate-700 dark:text-slate-200 font-semibold"
                  />
                  <dd className={`font-mono font-bold ${
                    (data.totals?.balance ?? 0) > 0
                      ? "text-red-600 dark:text-red-400"
                      : "text-green-600 dark:text-green-400"
                  }`}>
                    {formatCurrency(data.totals?.balance)}
                  </dd>
                </div>
                {onAddPayment && (
                  <div className="pt-3">
                    <button
                      onClick={onAddPayment}
                      className="w-full px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600 rounded-lg transition-colors flex items-center justify-center gap-2"
                    >
                      <FaMoneyBillWave size={14} />
                      Add Payment
                    </button>
                  </div>
                )}
              </>
            )}
          </dl>
        </div>
      </div>
    </div>
  );
};

export default withDevIdentifier(SummaryCard, 'SummaryCard', 'amber', 'apps/transactions/components/SummaryCard.tsx');