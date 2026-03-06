/**
 * ProposalDetail - Refactored to use TransactionDetailBase with SummaryCard
 * Standardized to match OrderDetail.tsx pattern
 */
import React, { useCallback } from "react";
import { useDispatch } from "react-redux";
import {
  FaExchangeAlt,
  FaFilePdf,
  FaTasks,
} from "react-icons/fa";

// Import base component and shared types
import TransactionDetailBase, { TransactionTab } from "../../../components/TransactionDetailBase";
import SummaryCard from "../../../components/SummaryCard";
import LinesCard from "../../../components/LinesCard";
import { lineKey, getNextLineNumber } from "../../../utils/lineHelpers";
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
import { withDevIdentifier } from '@/components/common/DevIdentifier';

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

// Price level options
const PRICE_LEVELS = [
  { value: "A", label: "A - Retail" },
  { value: "B", label: "B - Wholesale" },
  { value: "C", label: "C - Distributor" },
  { value: "D", label: "D - Volume" },
  { value: "E", label: "E - Special" },
];

// Dynamic tabs generator with badges based on data (like OrderDetail)
const getProposalTabsAfter = (_data: Transaction): TransactionTab[] => {
  // No additional tabs - actions are now in base
  return [];
};

// Custom Proposal Header Component using SummaryCard
const ProposalHeader: React.FC<{
  data: Proposal;
  isEditing: boolean;
  onChange?: (field: keyof Proposal, value: unknown) => void;
}> = ({ data, isEditing, onChange }) => {
  // Extract customer info from refs.links
  const customerInfo = data.refs?.links?.customer?.[0];
  const billingContact = data.refs?.links?.contact?.find(
    (c) => c.purpose === "billto",
  );
  const shippingContact = data.refs?.links?.contact?.find(
    (c) => c.purpose === "shipto",
  );

  return (
    <SummaryCard
      data={data}
      isEditing={isEditing}
      onChange={onChange}
      priceLable={PRICE_LEVELS}
      customerInfo={customerInfo}
      billingContact={billingContact}
      shippingContact={shippingContact}
      transactionLabel="Proposal"
      documentNoLabel="Proposal No"
      dueDateLabel="Valid Until"
      showShipping={false}
      showCostMargin={false}
    />
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

  // Custom header renderer (uses SummaryCard pattern)
  const renderHeader = useCallback(
    (
      data: Transaction,
      isEditing: boolean,
      onChange?: (field: string, value: unknown) => void,
    ) => (
      <ProposalHeader
        data={data as Proposal}
        isEditing={isEditing}
        onChange={onChange as ((field: keyof Proposal, value: unknown) => void) | undefined}
      />
    ),
    [],
  );

  // Custom lines renderer using LinesCard
  const renderLines = useCallback(
    (
      lines: TransactionLine[],
      isEditing: boolean,
      data?: Transaction,
      onLinesChange?: (lines: TransactionLine[]) => void,
    ) => {
      const proposalData = data as Proposal | undefined;
      const priceLevel = proposalData?.price_level || "base";

      return (
        <LinesCard
          lines={lines}
          isEditing={isEditing}
          isLocked={data?.is_locked}
          priceLevel={priceLevel}
          onDeleteLine={(lineId) => {
            if (onLinesChange) {
              onLinesChange(lines.filter((l, i) => lineKey(l, i) !== lineId));
            }
          }}
          onUpdateLine={(lineId, field, value) => {
            if (onLinesChange) {
              onLinesChange(
                lines.map((l, i) => {
                  if (lineKey(l, i) !== lineId) return l;
                  const baseUpdate = { ...l, _dirty: true };
                  switch (field) {
                    case "qty":
                      return {
                        ...baseUpdate,
                        quantity: { ...l.quantity, placed: Number(value) },
                      };
                    case "description":
                      return {
                        ...baseUpdate,
                        item: { ...l.item, description: String(value) },
                      };
                    case "unit_price":
                      const newPrice = Number(value);
                      const qty = l.quantity?.staged ?? quantity?.placed ?? 0;
                      return {
                        ...baseUpdate,
                        price: {
                          ...l.price,
                          unit: newPrice,
                          extended: newPrice * qty,
                        },
                      };
                    default:
                      return { ...baseUpdate, [field]: value };
                  }
                }),
              );
            }
          }}
          onDuplicateLine={(lineId) => {
            if (onLinesChange) {
              const lineToDup = lines.find((l, i) => lineKey(l, i) === lineId);
              if (lineToDup) {
                const { id, ...rest } = lineToDup;
                const newLine: TransactionLine = {
                  ...rest,
                  id: Date.now(),
                  line_number: getNextLineNumber(lines),
                };
                onLinesChange([...lines, newLine]);
              }
            }
          }}
          onLinesChange={onLinesChange}
        />
      );
    },
    [],
  );

  // Custom tab content renderer for actions
  const renderCustomTab = useCallback(
    (
      tabId: string,
      data: Transaction,
      isEditing: boolean,
      _onFieldChange?: (field: string, value: unknown) => void,
    ) => {
      const proposalData = data as Proposal;

      switch (tabId) {
        case "actions":
          // Simple placeholder for actions - can be expanded like OrderDetail
          const actions = proposalData.actions?.items ?? [];
          return (
            <div className="p-4">
              {actions.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <FaTasks size={32} className="mx-auto mb-3 opacity-50" />
                  <p>No actions on this proposal</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {actions.map((action, idx) => (
                    <div
                      key={action.id ?? idx}
                      className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700"
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-medium text-slate-900 dark:text-white">
                          {typeof action.action === "object"
                            ? action.action?.en
                            : action.action ?? action.what ?? "--"}
                        </span>
                        <span
                          className={`px-2 py-1 text-xs rounded-full ${
                            action.status === "done"
                              ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                              : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                          }`}
                        >
                          {action.status ?? "pending"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        default:
          return null;
      }
    },
    [],
  );

  // Check if proposal can be edited
  const canEdit = useCallback((data: Transaction) => {
    const status = data.status?.toLowerCase();
    return status !== "accepted" && status !== "cancelled" && status !== "rejected";
  }, []);

  return (
    <TransactionDetailBase
      transactionType="proposal"
      typeLabel="Proposal"
      modelName="proposal"
      getCustomTabsAfter={getProposalTabsAfter}
      renderCustomTab={renderCustomTab}
      renderHeader={renderHeader}
      renderLines={renderLines}
      isAdmin={props.isAdmin}
      canEdit={canEdit}
      inline={props.inline}
      modeProp={props.modeProp}
      dataProp={props.dataProp}
      onCancelInline={props.onCancelInline}
      onSaved={props.onSaved}
    />
  );
};

export default withDevIdentifier(ProposalDetail, 'ProposalDetail');