/**
 * ProposalDetail - Refactored to use TransactionDetailBase
 * Extends base with proposal-specific fields and functionality
 */
import React, { useCallback } from "react";
import { useDispatch } from "react-redux";
import {
  FaFileAlt,
  FaUser,
  FaBuilding,
  FaExchangeAlt,
  FaFilePdf,
} from "react-icons/fa";

// Import base component and shared types
import TransactionDetailBase from "../../../components/TransactionDetailBase";
import FieldLabel from "../../../components/FieldLabel";
import { CustomerSelector } from "../../../components/PartySelector";
import {
  TransactionItemSearch,
  resolveItemCode,
  resolveItemDescription,
  resolveUnitPrice,
  resolveUnitCost,
  type ItemSearchResult,
} from "../../../components/TransactionItemSearch";
import { showToast } from "../../../../../store/slices/toastSlice";
import {
  convertProposalToOrder,
  generateProposalPdf,
} from "../services/proposalApi";

// Import types
import type {
  Transaction,
  TransactionLine,
} from "../../../types/transactionTypes";

// Proposal specific fields that extend base Transaction
interface Proposal extends Transaction {
  ida?: string;
  proposal_no?: string;
  dt?: string;
  terms?: string;
  due_date?: string;
  valid_until?: string;
  priority?: string;
  price_level?: string;
  company?: string;
  attention?: string;
  address1?: string;
  address2?: string;
  city?: string;
  state?: string;
  zip?: string;
  email?: string;
  phone?: string;
  phoneCell?: string;
  comment?: string;
  contractDetail?: string;
  // Computed totals
  subtotal?: number;
  tax?: number;
  total?: number;
}

// Status Badge Component
const StatusBadge: React.FC<{ status?: string }> = ({ status }) => {
  const statusStyles: Record<string, string> = {
    planned:
      "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
    sent: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    accepted:
      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    rejected: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    cancelled:
      "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400",
  };

  return (
    <span
      className={`px-2 py-1 text-xs font-medium rounded-full ${
        statusStyles[status ?? "planned"] ?? statusStyles.planned
      }`}
    >
      {status ?? "planned"}
    </span>
  );
};

// Utility functions
const formatCurrency = (value?: number | null): string => {
  if (value === undefined || value === null) return "--";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
};

// Custom Proposal Header Component
const ProposalHeader: React.FC<{
  data: Proposal;
  isEditing: boolean;
  onChange?: (field: keyof Proposal, value: unknown) => void;
}> = ({ data, isEditing, onChange }) => {
  // Extract customer info from refs.links
  const customerInfo = data.refs?.links?.customer?.[0];

  return (
    <div className="space-y-6">
      {/* Proposal Header Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Proposal Details */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaFileAlt className="text-blue-500" />
            Proposal Details
          </h3>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Proposal No"
                mandatory
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono font-medium text-slate-900 dark:text-white">
                {data.ida ?? data.proposal_no ?? "--"}
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
                <input
                  type="date"
                  value={
                    data.dt ? new Date(data.dt).toISOString().split("T")[0] : ""
                  }
                  onChange={(e) => onChange("dt", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.dt ? new Date(data.dt).toLocaleDateString() : "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Valid Until"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <input
                  type="date"
                  value={
                    data.valid_until
                      ? new Date(data.valid_until).toISOString().split("T")[0]
                      : ""
                  }
                  onChange={(e) => onChange("valid_until", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.valid_until
                    ? new Date(data.valid_until).toLocaleDateString()
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
                <input
                  type="text"
                  value={data.terms ?? ""}
                  onChange={(e) => onChange("terms", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.terms ?? "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Priority"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <select
                  value={data.priority ?? "normal"}
                  onChange={(e) => onChange("priority", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                >
                  <option value="low">Low</option>
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
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
                <input
                  type="text"
                  value={data.price_level ?? ""}
                  onChange={(e) => onChange("price_level", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
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
          </dl>
        </div>

        {/* Middle: Customer Info */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaUser className="text-green-500" />
            Customer Information
          </h3>
          {isEditing && onChange ? (
            <div className="space-y-4">
              <CustomerSelector
                value={data.customer_id ?? null}
                onChange={(party) => onChange("customer_id", party?.id ?? null)}
                label="Customer"
                required
                size="sm"
              />
              <div className="flex justify-between items-center">
                <FieldLabel
                  label="Attention"
                  className="text-slate-500 dark:text-slate-400"
                />
                <input
                  type="text"
                  value={data.attention ?? ""}
                  onChange={(e) => onChange("attention", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              </div>
              <div className="flex justify-between items-center">
                <FieldLabel
                  label="Email"
                  className="text-slate-500 dark:text-slate-400"
                />
                <input
                  type="email"
                  value={data.email ?? ""}
                  onChange={(e) => onChange("email", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              </div>
              <div className="flex justify-between items-center">
                <FieldLabel
                  label="Phone"
                  className="text-slate-500 dark:text-slate-400"
                />
                <input
                  type="text"
                  value={data.phone ?? ""}
                  onChange={(e) => onChange("phone", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              </div>
            </div>
          ) : customerInfo ? (
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between">
                <FieldLabel
                  label="Customer"
                  className="text-slate-500 dark:text-slate-400"
                />
                <dd className="text-slate-900 dark:text-white font-medium">
                  {customerInfo.name ?? "--"}
                </dd>
              </div>
              {customerInfo.contact && (
                <div className="flex justify-between">
                  <FieldLabel
                    label="Contact"
                    className="text-slate-500 dark:text-slate-400"
                  />
                  <dd className="text-slate-900 dark:text-white">
                    {customerInfo.contact}
                  </dd>
                </div>
              )}
              {customerInfo.email && (
                <div className="flex justify-between">
                  <FieldLabel
                    label="Email"
                    className="text-slate-500 dark:text-slate-400"
                  />
                  <dd className="text-slate-900 dark:text-white">
                    {customerInfo.email}
                  </dd>
                </div>
              )}
              {customerInfo.phone && (
                <div className="flex justify-between">
                  <FieldLabel
                    label="Phone"
                    className="text-slate-500 dark:text-slate-400"
                  />
                  <dd className="text-slate-900 dark:text-white">
                    {customerInfo.phone}
                  </dd>
                </div>
              )}
            </dl>
          ) : data.company ? (
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between items-center">
                <FieldLabel
                  label="Company"
                  className="text-slate-500 dark:text-slate-400"
                />
                <dd className="text-slate-900 dark:text-white font-medium">
                  {data.company}
                </dd>
              </div>
              {data.attention && (
                <div className="flex justify-between items-center">
                  <FieldLabel
                    label="Attention"
                    className="text-slate-500 dark:text-slate-400"
                  />
                  <dd className="text-slate-900 dark:text-white">
                    {data.attention}
                  </dd>
                </div>
              )}
              {data.email && (
                <div className="flex justify-between items-center">
                  <FieldLabel
                    label="Email"
                    className="text-slate-500 dark:text-slate-400"
                  />
                  <dd className="text-slate-900 dark:text-white">
                    {data.email}
                  </dd>
                </div>
              )}
              {data.phone && (
                <div className="flex justify-between items-center">
                  <FieldLabel
                    label="Phone"
                    className="text-slate-500 dark:text-slate-400"
                  />
                  <dd className="text-slate-900 dark:text-white">
                    {data.phone}
                  </dd>
                </div>
              )}
            </dl>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400 italic">
              No customer assigned
            </p>
          )}
        </div>

        {/* Right: Address */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaBuilding className="text-purple-500" />
            Address
          </h3>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Address 1"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <input
                  type="text"
                  value={data.address1 ?? ""}
                  onChange={(e) => onChange("address1", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.address1 ?? "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Address 2"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <input
                  type="text"
                  value={data.address2 ?? ""}
                  onChange={(e) => onChange("address2", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.address2 ?? "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="City"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <input
                  type="text"
                  value={data.city ?? ""}
                  onChange={(e) => onChange("city", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.city ?? "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="State"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <input
                  type="text"
                  value={data.state ?? ""}
                  onChange={(e) => onChange("state", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white w-20"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.state ?? "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="ZIP"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <input
                  type="text"
                  value={data.zip ?? ""}
                  onChange={(e) => onChange("zip", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white w-24"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.zip ?? "--"}
                </dd>
              )}
            </div>
          </dl>
        </div>
      </div>

      {/* Totals Summary */}
      <div className="bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-800/50 dark:to-slate-700/50 rounded-lg p-6 border border-slate-200 dark:border-slate-700">
        <div className="grid grid-cols-3 gap-8 text-center">
          <div>
            <dt className="text-sm text-slate-500 dark:text-slate-400 mb-1">
              Subtotal
            </dt>
            <dd className="text-2xl font-bold text-slate-900 dark:text-white">
              {formatCurrency(data.subtotal)}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-slate-500 dark:text-slate-400 mb-1">
              Tax
            </dt>
            <dd className="text-2xl font-bold text-slate-900 dark:text-white">
              {formatCurrency(data.tax)}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-slate-500 dark:text-slate-400 mb-1">
              Total
            </dt>
            <dd className="text-3xl font-bold text-green-600 dark:text-green-400">
              {formatCurrency(data.total)}
            </dd>
          </div>
        </div>
      </div>
    </div>
  );
};

// Proposal Lines Tab Content
const ProposalLinesContent: React.FC<{
  data: Proposal;
  lines: TransactionLine[];  // Use lines prop directly from renderLines
  isEditing: boolean;
  onLinesChange?: (lines: TransactionLine[]) => void;
}> = ({ data, lines, isEditing, onLinesChange }) => {
  // Handler for adding items from search
  const handleAddItem = useCallback(
    (item: ItemSearchResult, quantity: number) => {
      if (!onLinesChange) return;

      const idaItem = resolveItemCode(item);
      const description = resolveItemDescription(item);
      const unitPrice = resolveUnitPrice(item);
      const unitCost = resolveUnitCost(item);
      const itemId = item.id ?? item.item_id ?? item.itemId ?? null;
      const unitMeasure = String(
        item.unit_of_measure ?? item.unitOfMeasure ?? item.unit_measure ?? "EA",
      );

      const newLine: TransactionLine = {
        _dirty: true,
        item: {
          item_id: itemId as number | null,
          ida_item: idaItem,
          description: description,
          unit_measure: unitMeasure,
        },
        quantity: {
          ordered: quantity,
        },
        price: {
          unit: unitPrice,
          extended: unitPrice * quantity,
        },
        cost: {
          unit: unitCost,
        },
      } as unknown as TransactionLine;

      onLinesChange([...lines, newLine]);
    },
    [lines, onLinesChange],
  );

  return (
    <div className="space-y-6">
      {/* Item Search Panel - only in edit mode */}
      {/* {isEditing && onLinesChange && (
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-2">Add Items</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
            Search the catalog and add items to this proposal.
          </p>
          <TransactionItemSearch onAddItem={handleAddItem} useCost={false} defaultQuantity={1} />
        </div>
      )} */}

      {/* Lines Table */}
      {!lines.length ? (
        <div className="text-center py-12 text-slate-500 dark:text-slate-400">
          <FaFileAlt className="mx-auto text-4xl mb-4 opacity-50" />
          <p>No line items</p>
          {isEditing && (
            <p className="mt-2 text-sm">
              Use the search above to find and add products
            </p>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700">
                <th className="text-left p-3 text-slate-600 dark:text-slate-300">
                  Item
                </th>
                <th className="text-left p-3 text-slate-600 dark:text-slate-300">
                  Description
                </th>
                <th className="text-right p-3 text-slate-600 dark:text-slate-300">
                  Qty
                </th>
                <th className="text-right p-3 text-slate-600 dark:text-slate-300">
                  Price
                </th>
                <th className="text-right p-3 text-slate-600 dark:text-slate-300">
                  Amount
                </th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line: any, index: number) => (
                <tr
                  key={line.id || index}
                  className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50"
                >
                  <td className="p-3 font-mono text-slate-900 dark:text-white">
                    {line.item?.ida_item ??
                      line.item_no ??
                      line.sku ??
                      line.item_name ??
                      "--"}
                  </td>
                  <td className="p-3 text-slate-700 dark:text-slate-300">
                    {line.item?.description ?? line.description ?? "--"}
                  </td>
                  <td className="p-3 text-right text-slate-900 dark:text-white">
                    {line.quantity?.ordered ?? line.quantity ?? "--"}
                  </td>
                  <td className="p-3 text-right text-slate-900 dark:text-white">
                    {formatCurrency(
                      line.price?.unit ??
                        line.price?.sell ??
                        line.unit_price ??
                        line.price,
                    )}
                  </td>
                  <td className="p-3 text-right font-medium text-slate-900 dark:text-white">
                    {formatCurrency(
                      line.price?.extended ?? line.amount ?? line.line_total,
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// Props interface
interface ProposalDetailProps {
  modeProp?: "view" | "edit" | "add";
  dataProp?: Proposal;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
  isAdmin?: boolean;
}

// Main Component
const ProposalDetail: React.FC<ProposalDetailProps> = (props) => {
  const dispatch = useDispatch();

  // Custom action handlers for proposal-specific actions
  const handleConvertToOrder = useCallback(
    async (data: Proposal) => {
      if (!data?.id) return;
      try {
        const res = await convertProposalToOrder(data.id);
        if (res.status === 200) {
          dispatch(
            showToast({
              message: "Proposal converted to sales order successfully",
              type: "success",
            }),
          );
          if (props.onSaved) {
            props.onSaved();
          }
        }
      } catch (error: any) {
        dispatch(
          showToast({
            message: error.message || "Failed to convert proposal",
            type: "error",
          }),
        );
      }
    },
    [dispatch, props.onSaved],
  );

  const handleGeneratePdf = useCallback(
    async (data: Proposal) => {
      if (!data?.id) return;
      try {
        await generateProposalPdf(data.id);
        dispatch(
          showToast({
            message: "PDF generated successfully",
            type: "success",
          }),
        );
      } catch (error: any) {
        dispatch(
          showToast({
            message: error.message || "Failed to generate PDF",
            type: "error",
          }),
        );
      }
    },
    [dispatch],
  );

  // Custom toolbar actions
  const customToolbarActions = [
    {
      id: "convert-to-order",
      label: "Convert to Order",
      icon: <FaExchangeAlt size={14} />,
      onClick: handleConvertToOrder,
      showInView: true,
      showInEdit: false,
    },
    {
      id: "generate-pdf",
      label: "Generate PDF",
      icon: <FaFilePdf size={14} />,
      onClick: handleGeneratePdf,
      showInView: true,
      showInEdit: false,
    },
  ];

  return (
    <TransactionDetailBase
      transactionType="proposal"
      typeLabel="Proposal"
      modelName="proposal"
      renderHeader={(data, isEditing, onChange) => (
        <ProposalHeader
          data={data as Proposal}
          isEditing={isEditing}
          onChange={onChange as any}
        />
      )}
      renderLines={(lines, isEditing, data, onLinesChange) => (
        <ProposalLinesContent
          data={data as Proposal}
          lines={lines}
          isEditing={isEditing}
          onLinesChange={onLinesChange}
        />
      )}
      inline={props.inline}
      modeProp={props.modeProp}
      dataProp={props.dataProp}
      onSaved={props.onSaved}
      onCancelInline={props.onCancelInline}
      isAdmin={props.isAdmin}
    />
  );
};

export default ProposalDetail;
