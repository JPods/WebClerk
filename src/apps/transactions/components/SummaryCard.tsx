import React from "react";
import FieldLabel from "../components/FieldLabel";
import { Input, DropDown } from "@/components/wrapper";

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
import { FaLock, FaShoppingCart } from "react-icons/fa";
import { TransactionPartySelector } from "./PartySelector";

interface SummaryCardProps {
  data: any;
  isEditing: boolean;
  onChange?: (field: any, value: unknown) => void;
  priceLable?: Array<{ label: string; value: string }>;
  customerInfo: any;
  billingContact: any;
  shippingContact: any;
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
}) => {
  // Add logic to extract billingContact and shippingContact from customerInfo or data

  return (
    <div className="space-y-6">
      {/* Sales Order Header Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Order Details */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaShoppingCart className="text-blue-500" />
            Order
          </h3>
          <dl className="space-y-3 text-xs">
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Order No QQQ get action dotteed"
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
                label="ID"
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-slate-600 dark:text-slate-300">
                {data.id ?? "--"}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Date"
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
                  {data.dt ? new Date(data.dt).toLocaleDateString() : "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Due Date"
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
                    ? new Date(data.due_date).toLocaleDateString()
                    : "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Terms"
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
                label="PO Number"
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
                label="Priority"
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
                label="Price Level"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <DropDown
                  id="purpose"
                  options={priceLable}
                  placeholder="Select Price Level"
                  value={data.price_level ?? ""}
                  onChange={(value: string) => onChange("price_level", value)}
                  className="dark:bg-dark-900"
                  disabled={!isEditing}
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.price_level ?? "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Status"
                mandatory
                className="text-slate-500 dark:text-slate-400"
              />
              <dd>
                <StatusBadge status={data.status} />
              </dd>
            </div>
            {data.is_locked && (
              <div className="flex justify-between items-center pt-2 mt-2 border-t border-slate-200 dark:border-slate-700">
                <FieldLabel
                  label="Locked"
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

        {/* Center: Customer Info */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
            Customer
          </h3>
          {/* Customer selection or display */}
          {isEditing && !customerInfo ? (
            <div>
              <FieldLabel label="Customer" mandatory />
              <TransactionPartySelector
                transactionType="sales"
                value={data.customer_id ?? null}
                onChange={(party) =>
                  onChange && onChange("customer_id", party?.id ?? null)
                }
                className="text-sm"
              />
            </div>
          ) : customerInfo ? (
            <dl className="space-y-3 text-xs">
              <div className="flex justify-between items-center">
                <FieldLabel
                  label="Customer ID"
                  locked
                  className="text-slate-500 dark:text-slate-400"
                />
                <dd className="font-mono text-slate-600 dark:text-slate-300">
                  {data.customer_id ?? "--"}
                </dd>
              </div>
              <div className="flex justify-between items-center">
                <FieldLabel
                  label="Name"
                  className="text-slate-500 dark:text-slate-400"
                />
                <dd className="text-slate-900 dark:text-white">
                  {customerInfo.display_name ?? "--"}
                </dd>
              </div>
              <div className="flex justify-between items-center">
                <FieldLabel
                  label="IDA"
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

        {/* Right: Totals */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
            Order Totals
          </h3>
          <dl className="space-y-3 text-xs">
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Subtotal"
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.subtotal ?? data.subtotal)}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Discount"
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-red-600 dark:text-red-400">
                {data.totals?.discount
                  ? `-${formatCurrency(data.totals.discount)}`
                  : "--"}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Tax"
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.tax ?? data.tax)}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Shipping"
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.shipping)}
              </dd>
            </div>
            <div className="flex justify-between items-center pt-2 border-t border-slate-200 dark:border-slate-700">
              <FieldLabel
                label="Total"
                mandatory
                locked
                className="text-slate-700 dark:text-slate-200 text-base"
              />
              <dd className="text-lg font-bold text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.total ?? data.total)}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Cost"
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-slate-600 dark:text-slate-400">
                {formatCurrency(data.totals?.cost)}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Margin"
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
          </dl>
        </div>
      </div>
    </div>
  );
};

export default SummaryCard;
