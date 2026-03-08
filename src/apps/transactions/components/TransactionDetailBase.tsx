import QATab from "./QATab";
import { normalizeRefsLinksContact } from "./ContactPanel";
/**
 * TransactionDetail - Base component for all transaction detail pages
 * Provides common tabbed layout with standard sections
 * Extended by InvoiceDetail, OrderDetail, etc.
 */
import React, { useState, useEffect, useMemo, useCallback } from "react";
import PrintPreviewModal from "./PrintPreviewModal";
import useUnsavedChangesGuard from "@/hooks/useUnsavedChangesGuard";
import UnsavedChangesDialog from "@/components/common/UnsavedChangesDialog";
import {
  OrderPrintDocument,
  InvoicePrintDocument,
  ProposalPrintDocument,
  PurchasePrintDocument,
  WorkorderPrintDocument,
  ReceiptPrintDocument,
  AdjustmentPrintDocument,
} from "./print";
import { useRealTimeCalculations } from "@/hooks/useRealTimeCalculations";
import {
  useTransactionDefaults,
  computeDueDate,
} from "@/hooks/useTransactionDefaults";
import { useParams, useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import { useAppSelector } from "../../../store/hooks";
import { useWindowPath } from "@/context/WindowPathContext";
import { useWindowManager } from "@/context/WindowManagerContext";
import {
  FaArrowLeft,
  FaEdit,
  FaPrint,
  FaAddressCard,
  FaComments,
  FaDollarSign,
  FaLink,
  FaEllipsisH,
  FaTasks,
  FaQuestionCircle,
} from "react-icons/fa";
import { showToast } from "../../../store/slices/toastSlice";
import {
  ScalarCard,
  JsonCard,
  BaseModelCards,
} from "@/apps/common/components/detail";

// Import API functions
import {
  getRecord,
  saveRecord,
  saveTransactionWithLines,
  deleteRecord,
} from "../../../api/wcapi";

// Import toolbar
import TransactionToolbar, { type TransactionType } from "./TransactionToolbar";
import OrgSearchDialog, {
  type SearchableOrgType,
  type OrgSearchResult,
} from "@/apps/common/components/OrgSearchDialog";

// Import shared components
import ContactPanel from "./ContactPanel";

import CommentsPanel from "./CommentsPanel";
import FinancialsCard from "./FinancialsCard";
import { DocumentsPanel } from "@/apps/common/components/panels";

import JsonFieldEditor from "./JsonFieldEditor";
import RelatedTransactions from "@/components/common/RelatedTransactions";

// Import types
import type {
  Transaction as TransactionBase,
  TransactionLine,
} from "../types/transactionTypes";
import SummaryCard from "./SummaryCard";
import LinesCard from "./LinesCard";
import { lineKey, getNextLineNumber } from "../utils/lineHelpers";
import { DevBadge } from "@/components/common/DevBadge";
import { withDevIdentifier } from "@/components/common/DevIdentifier";
import { useFormCoach } from "@/hooks/useFormCoach";
import type { TransactionModelType } from "@/hooks/useFormCoach";
import FormCoachAlert from "@/apps/common/components/FormCoachAlert";

/** Map transactionType → print form source file (for FormCoach "Open in VS Code") */
const FORM_SOURCE_PATHS: Record<string, string> = {
  order:      'src/apps/transactions/components/print/OrderPrintDocument.tsx',
  invoice:    'src/apps/transactions/components/print/InvoicePrintDocument.tsx',
  proposal:   'src/apps/transactions/components/print/ProposalPrintDocument.tsx',
  purchase:   'src/apps/transactions/components/print/PurchasePrintDocument.tsx',
  workorder:  'src/apps/transactions/components/print/WorkorderPrintDocument.tsx',
  receipt:    'src/apps/transactions/components/print/ReceiptPrintDocument.tsx',
  adjustment: 'src/apps/transactions/components/print/AdjustmentPrintDocument.tsx',
};

// Extend Transaction type locally to ensure 'lines' exists
type Transaction = TransactionBase & {
  lines?: TransactionLine[];
  currency?: string; // Add currency property
  number?: string | number; // Add number property to fix compile error
  dt?: string; // Transaction date
  due_date?: string; // Due date
};

function getDisplayErrorMessage(error: unknown, fallback: string): string {
  const anyError = error as any;
  const responseData = anyError?.response?.data;

  if (responseData) {
    if (typeof responseData === "string") {
      if (responseData.trim() && responseData !== "[object Object]") {
        return responseData;
      }
    }

    const detail = responseData?.detail;
    const backendError = responseData?.error;
    const message = responseData?.message;

    if (typeof backendError === "string" && backendError.trim()) {
      return backendError;
    }
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (typeof message === "string" && message.trim()) {
      return message;
    }
  }

  if (
    error instanceof Error &&
    typeof error.message === "string" &&
    error.message.trim() &&
    error.message !== "[object Object]"
  ) {
    return error.message;
  }

  if (
    typeof anyError?.message === "string" &&
    anyError.message.trim() &&
    anyError.message !== "[object Object]"
  ) {
    return anyError.message;
  }

  return fallback;
}

function normalizeFkId(value: unknown): number | null {
  if (value == null) return null;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (
    typeof value === "string" &&
    value.trim() &&
    !Number.isNaN(Number(value))
  ) {
    return Number(value);
  }
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const nested = obj.id;
    if (typeof nested === "number" && Number.isFinite(nested)) return nested;
    if (
      typeof nested === "string" &&
      nested.trim() &&
      !Number.isNaN(Number(nested))
    ) {
      return Number(nested);
    }
  }
  return null;
}

function normalizeTransactionFkFields<T extends Record<string, any>>(
  input: T,
): T {
  if (!input || typeof input !== "object") return input;
  const out: T = { ...(input as any) };

  const setIfMissing = (targetField: string, ...candidates: unknown[]) => {
    const existing = normalizeFkId((out as any)[targetField]);
    if (existing && existing > 0) return;
    for (const candidate of candidates) {
      const normalized = normalizeFkId(candidate);
      if (normalized && normalized > 0) {
        (out as any)[targetField] = normalized;
        return;
      }
    }
  };

  // WCAPI may return FK fields without the _id suffix (e.g. "customer")
  // or legacy fields (e.g. "id_customer"). Normalize to *_id so UI + save path agree.
  setIfMissing("customer_id", out.customer_id, out.customer, out.id_customer);
  setIfMissing("vendor_id", out.vendor_id, out.vendor, out.id_vendor);
  setIfMissing(
    "manufacturer_id",
    out.manufacturer_id,
    out.manufacturer,
    out.id_manufacturer,
  );
  setIfMissing("contact_id", out.contact_id, out.contact, out.id_contact);
  setIfMissing("terms_id", out.terms_id, out.terms_fk, out.terms);

  return out;
}

function stripTransactionFkAliases<T extends Record<string, any>>(input: T): T {
  const out: T = { ...(input as any) };
  // Remove ambiguous alias fields so we don't send both "customer" and "customer_id".
  // Keep *_ida and other scalar fields.
  delete (out as any).customer;
  delete (out as any).vendor;
  delete (out as any).manufacturer;
  delete (out as any).contact;
  delete (out as any).terms_fk;
  return out;
}

// Tab definition
export interface TransactionTab {
  id: string;
  label: string;
  icon: React.ReactNode;
  badge?: string | number;
  adminOnly?: boolean;
}

// Props for the base component
interface TransactionDetailBaseProps {
  /** Transaction type (invoice, order, etc.) */
  transactionType: string;

  /** Display label for the transaction type */
  typeLabel: string;

  /** API model name for fetching */
  modelName: string;

  /** Custom tabs to add before standard tabs */
  customTabsBefore?: TransactionTab[];

  /** Custom tabs to add after standard tabs */
  customTabsAfter?: TransactionTab[];

  /** Function to generate custom tabs with dynamic badges based on data */
  getCustomTabsAfter?: (data: Transaction) => TransactionTab[];

  /** Render function for custom tab content */
  renderCustomTab?: (
    tabId: string,
    data: Transaction,
    isEditing: boolean,
    onFieldChange?: (field: string, value: unknown) => void,
  ) => React.ReactNode;

  /** Render function for the header section */
  renderHeader?: (
    data: Transaction,
    isEditing: boolean,
    onChange?: (field: string, value: unknown) => void,
  ) => React.ReactNode;

  /** Render function for lines section (if not using default) */
  renderLines?: (
    lines: TransactionLine[],
    isEditing: boolean,
    data?: Transaction,
    onLinesChange?: (lines: TransactionLine[]) => void,
  ) => React.ReactNode;

  /** Whether user is admin (affects visible tabs/fields) */
  isAdmin?: boolean;

  /** Whether the transaction is editable in current state */
  canEdit?: (data: Transaction) => boolean;

  /** Whether clone action is allowed */
  canClone?: boolean;

  /** Whether transfer action is allowed */
  canTransfer?: boolean;

  /** Whether delete action is allowed */
  canDelete?: boolean;

  /** Custom fetch function if not using standard API */
  fetchData?: (id: string) => Promise<Transaction>;

  /** Custom save function if not using standard API */
  saveData?: (data: Transaction) => Promise<Transaction>;

  /** Callback after successful save */
  onSaved?: (data: Transaction) => void;

  /** Callback for print action */
  onPrint?: (data: Transaction) => void;

  /** Callback for email action */
  onEmail?: (data: Transaction) => void;

  /** When true, render inline without full page layout (for use in split-view list) */
  inline?: boolean;

  /** External mode control when used inline */
  modeProp?: "view" | "edit" | "add" | null;

  /** Pre-loaded data when used inline (skips fetch) */
  dataProp?: Transaction | null;

  /** Direct ID prop (for use with /wcapi/get/?id=X routes) */
  idProp?: number | string;

  /** Callback for cancel/close action in inline mode */
  onCancelInline?: () => void;

  /** Callback for Add Task action */
  onAddTask?: () => void;
  /** Whether to show Add Task button */
  showTaskButton?: boolean;
  /** Number of pending tasks (for badge) */
  taskCount?: number;
}

/**
 * Extract a renderable string from comments.public which may be
 * either a plain string or an array of comment objects ({mgs, time, user, user_id}).
 */
const extractPublicComment = (publicField: unknown): string | undefined => {
  if (!publicField) return undefined;
  if (typeof publicField === "string") return publicField;
  if (Array.isArray(publicField)) {
    return publicField
      .map((c: any) => (typeof c === "string" ? c : c?.mgs))
      .filter(Boolean)
      .join("\n");
  }
  return String(publicField);
};

const TransactionDetailBase: React.FC<TransactionDetailBaseProps> = ({
  transactionType,
  typeLabel,
  modelName,
  customTabsBefore = [],
  customTabsAfter = [],
  getCustomTabsAfter,
  renderCustomTab,
  // ...existing props
  renderHeader,
  renderLines,
  isAdmin = false,
  canEdit = () => true,
  canClone = true,
  canTransfer = true,
  canDelete = true,
  fetchData,
  saveData,
  onSaved,
  onPrint,
  onEmail,
  inline = false,
  modeProp,
  dataProp,
  idProp,
  onCancelInline,
  onAddTask,
  showTaskButton = false,
  taskCount,
}) => {
  const getTransactionRouteSegment = useCallback((t: string) => {
    // Routes use a hyphenated segment for work orders, but the model key is `workorder`.
    // Keep the model key for API calls; only the URL segment needs special-casing.
    return t === "workorder" ? "work-order" : t;
  }, []);

  // Default no-op for handleAddItem to avoid reference error
  const handleAddItem = () => {};
  const { id: urlId } = useParams<{ id: string }>();
  // Use idProp first, then dataProp ID, then URL param
  const id = idProp?.toString() ?? dataProp?.id?.toString() ?? urlId;
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { ensureWindow, closeWindow } = useWindowManager();
  const { user } = useAppSelector((state) => state.auth);
  const displayName = user ? `${user.name_first}${user.name_last}` : "You";

  const emitModelChanged = useCallback((detail: Record<string, unknown>) => {
    try {
      window.dispatchEvent(new CustomEvent("wcapi:modelChanged", { detail }));
    } catch {
      // ignore (SSR/older env)
    }
  }, []);

  // Parse query params from the floating window path (if available)
  const windowPath = useWindowPath();
  const windowSearchParams = useMemo(() => {
    if (!windowPath) return null;
    try {
      return new URL(windowPath, "http://x").searchParams;
    } catch {
      return null;
    }
  }, [windowPath]);

  // If this window was opened via the toolbar Transfer dropdown,
  // these params identify the source transaction we transferred from.
  const transferSource = useMemo(() => {
    const t = windowSearchParams?.get("transfer_from_type")?.trim() || "";
    const idRaw = windowSearchParams?.get("transfer_from_id")?.trim() || "";
    const idNum = Number(idRaw);
    if (!t || !Number.isFinite(idNum) || idNum <= 0) return null;
    return { type: t, id: idNum };
  }, [windowSearchParams]);

  // Determine effective mode: if no ID is available and modeProp isn't set,
  // treat as "add" mode (e.g. opened from Create Transaction dropdown).
  // Detail pages always open in edit mode — switch to read-only only when needed.
  const effectiveMode = useMemo(() => {
    if (modeProp) return modeProp;
    if (!id) return "add" as const;
    return "edit" as const;
  }, [modeProp, id]);

  // Fetch singleton transaction defaults from the settings table
  const { defaults: txDefaults } = useTransactionDefaults();

  // State
  const [data, setData] = useState<Transaction | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Always start in edit mode — existing records open editable
  const [isEditing, setIsEditing] = useState(
    effectiveMode === "add" || effectiveMode === "edit",
  );
  const [editData, setEditData] = useState<Transaction | null>(null);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("summary");
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0); // Trigger refetch when incremented

  // Refresh function to reload data
  const refreshData = () => {
    setRefreshKey((prev) => prev + 1);
  };

  // Handle "add" mode - create empty record or pre-populate from transfer source
  useEffect(() => {
    if (effectiveMode !== "add") return;

    // Check for transfer source params
    const transferFromType = windowSearchParams?.get("transfer_from_type");
    const transferFromId = windowSearchParams?.get("transfer_from_id");

    // Get today's date at midnight (zero time)
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayIso = today.toISOString();

    // If transferring from another transaction, fetch the source and pre-populate
    if (transferFromType && transferFromId) {
      setLoading(true);
      getRecord(transferFromType, Number(transferFromId))
        .then((apiResult) => {
          const source = apiResult?.record ?? apiResult;
          if (!source) {
            dispatch(
              showToast({
                message: `Could not load source ${transferFromType} #${transferFromId}`,
                type: "error",
              }),
            );
            setLoading(false);
            return;
          }
          // Copy lines from source, resetting IDs so they create as new.
          // Stamp each line's refs.source with the source line ID so the
          // backend can update the source line's quantity.active after save.
          const srcType = transferFromType as string;
          const srcId = Number(transferFromId);
          let nextLn = 10; // line_number counter for transferred lines
          const transferredLines = (source.lines || []).map(
            (line: Record<string, unknown>) => {
              // Remap quantity for the target transaction:
              // staged = source remaining (qty being transferred)
              // active = transfer_qty (the user input)
              // remaining = staged (full qty available for further transfers)
              // Matches wc3 transfer.py _convert_quantity / _clone_quantity
              const srcQty = (line.quantity as Record<string, unknown>) || {};
              const transferQty = Number(
                srcQty.remaining ?? srcQty.staged ?? 0,
              );
              const ln = nextLn;
              nextLn += 10;
              return {
                ...line,
                id: undefined,
                line_id: undefined,
                line_number: ln,
                quantity: {
                  staged: transferQty,
                  active: transferQty,
                  remaining: transferQty,
                  precision: srcQty.precision ?? 2,
                  is_fixed: srcQty.is_fixed ?? false,
                  is_blanket: srcQty.is_blanket ?? false,
                  increment: srcQty.increment ?? 0,
                },
                refs: {
                  ...((line.refs as Record<string, unknown>) || {}),
                  source: {
                    [`${srcType}_line_id`]: (line as any).id,
                    [`${srcType}_id`]: srcId,
                    converted_from: srcType,
                  },
                },
              };
            },
          );
          // wcapi GET returns FK fields without _id suffix (e.g. "customer"),
          // but our Transaction type and save serializers use _id suffix.
          const customerId = source.customer_id ?? source.customer ?? null;
          const vendorId = source.vendor_id ?? source.vendor ?? null;
          const manufacturerId =
            source.manufacturer_id ?? source.manufacturer ?? null;
          const contactId = source.contact_id ?? source.contact ?? null;
          const record: Transaction = {
            id: undefined as unknown as number,
            customer_id: customerId,
            vendor_id: vendorId,
            manufacturer_id: manufacturerId,
            status: "planned",
            lines: transferredLines,
            // Lineage: parent_id / parent_model tell the backend this is
            // a transferred transaction.  The Pending inventory creator
            // uses parent_id to release on_so and deduct on_hand.
            parent_id: srcId,
            parent_model: srcType as TransactionType,
            refs: {
              source: {
                [`${srcType}_id`]: srcId,
                converted_from: srcType,
              },
            } as any,
            metadata: {} as any,
            comments: { notes: [] },
            totals: {},
            finance: {},
            dt: todayIso,
            due_date: computeDueDate(todayIso, txDefaults.due_date_period),
            // Apply setting defaults first, then override from source
            terms: txDefaults.terms,
            price_level: txDefaults.price_level,
            priority: txDefaults.priority,
            // Copy common header fields (source overrides defaults)
            ...(source.terms ? { terms: source.terms } : {}),
            ...(source.terms_id ?? source.terms_fk
              ? { terms_id: source.terms_id ?? source.terms_fk }
              : {}),
            ...(source.price_level ? { price_level: source.price_level } : {}),
            ...(source.attention ? { attention: source.attention } : {}),
            ...(source.phone ? { phone: source.phone } : {}),
            ...(source.email ? { email: source.email } : {}),
            ...(source.address_full
              ? { address_full: source.address_full }
              : {}),
            ...(contactId ? { contact_id: contactId } : {}),
            // Legacy transfer_from (kept for backwards compat)
            // transfer_from is not a valid property on Transaction, so remove or handle appropriately
          };
          setData(record);
          setEditData(record);
          setIsEditing(true);
          setLoading(false);
        })
        .catch((err) => {
          console.warn(
            "[TransactionDetailBase] Transfer source fetch failed:",
            err,
          );
          dispatch(
            showToast({
              message: `Failed to load source ${transferFromType}`,
              type: "error",
            }),
          );
          setLoading(false);
        });
      return;
    }

    // Pre-populate from query params if available
    const qsCustomerId = windowSearchParams?.get("customer_id");
    const qsCustomerName = windowSearchParams?.get("customer_name");
    const qsPriceLevel = windowSearchParams?.get("price_level");
    const qsAttention = windowSearchParams?.get("attention");
    const qsPhone = windowSearchParams?.get("phone");
    const qsEmail = windowSearchParams?.get("email");
    const qsTerms = windowSearchParams?.get("terms");
    const qsTermsId = windowSearchParams?.get("terms_id");
    const qsContactId = windowSearchParams?.get("contact_id");
    const qsAddressFull = windowSearchParams?.get("address_full");

    // Build refs.links with customer defaults transferred from query params
    const links: Record<string, unknown> = {};
    if (qsCustomerId) {
      links.customer = [
        {
          id: Number(qsCustomerId),
          display_name: qsCustomerName || "",
        },
      ];
    }
    if (qsContactId) {
      links.contact = [
        {
          id: Number(qsContactId),
          purpose: "billto",
          display_name: qsAttention || "",
          email: qsEmail || "",
          phone: qsPhone || "",
        },
      ];
    } else if (qsAttention || qsEmail || qsPhone) {
      links.contact = [
        {
          id: 0,
          purpose: "billto",
          display_name: qsAttention || "",
          email: qsEmail || "",
          phone: qsPhone || "",
        },
      ];
    }

    const emptyRecord: Transaction = {
      id: undefined as unknown as number,
      customer_id: qsCustomerId ? Number(qsCustomerId) : 0,
      vendor_id: 0,
      manufacturer_id: 0,
      status: "planned",
      // Apply setting defaults first
      terms: txDefaults.terms,
      price_level: txDefaults.price_level,
      priority: txDefaults.priority,
      // Query-param overrides (take precedence over defaults)
      ...(qsPriceLevel ? { price_level: qsPriceLevel } : {}),
      ...(qsTerms ? { terms: qsTerms } : {}),
      ...(qsTermsId ? { terms_id: Number(qsTermsId) } : {}),
      ...(qsContactId ? { contact_id: Number(qsContactId) } : {}),
      ...(qsAttention ? { attention: qsAttention } : {}),
      ...(qsPhone ? { phone: qsPhone } : {}),
      ...(qsEmail ? { email: qsEmail } : {}),
      ...(qsAddressFull ? { address_full: qsAddressFull } : {}),
      lines: [],
      refs: { links } as any,
      metadata: {} as any,
      comments: { notes: [] },
      totals: {},
      finance: {},
      // Initialize dt to today; due_date = today + due_date_period
      dt: todayIso,
      due_date: computeDueDate(todayIso, txDefaults.due_date_period),
    };
    setData(emptyRecord);
    setEditData(emptyRecord);
    setIsEditing(true);
    setLoading(false);
  }, [effectiveMode, windowSearchParams, txDefaults]);

  // Update isEditing when modeProp changes (for inline usage)
  useEffect(() => {
    if (effectiveMode === "edit") {
      setIsEditing(true);
    } else if (effectiveMode === "view") {
      setIsEditing(false);
    }
  }, [effectiveMode]);

  // Track unsaved changes
  useEffect(() => {
    if (isEditing && data && editData) {
      const changed = JSON.stringify(data) !== JSON.stringify(editData);
      setHasUnsavedChanges(changed);
    } else {
      setHasUnsavedChanges(false);
    }
  }, [isEditing, data, editData]);

  // Unsaved changes guard - provides action guards and beforeunload protection
  const {
    guardAction,
    isActionPending,
    pendingAction,
    confirmAction,
    cancelAction,
  } = useUnsavedChangesGuard(hasUnsavedChanges);

  // Fetch data - skip if dataProp is provided (inline mode with pre-loaded data)
  // Also skip if modeProp is 'add' (handled by separate effect above)
  // Track if we've done initial load with dataProp
  const [initialDataPropUsed, setInitialDataPropUsed] = useState(false);

  useEffect(() => {
    // Skip fetch for "add" mode - handled by the add mode effect
    if (effectiveMode === "add") {
      return;
    }

    // If dataProp is provided AND we haven't used it yet AND refreshKey is 0 (initial load)
    // use dataProp directly instead of fetching
    if (dataProp && !initialDataPropUsed && refreshKey === 0) {
      const normalized = normalizeTransactionFkFields(dataProp as any);
      setData(normalized);
      setEditData(normalized);
      setLoading(false);
      setInitialDataPropUsed(true);
      return;
    }

    // For refreshKey > 0 (after save), always fetch fresh data from API
    const loadData = async () => {
      if (!id) return;

      setLoading(true);
      setError(null);

      try {
        let result: Transaction;

        if (fetchData) {
          result = await fetchData(id);
        } else {
          // Use wcapi getRecord which includes auth headers and proper error handling
          const apiResult = await getRecord(modelName, Number(id));
          result = apiResult.record ?? apiResult;
        }

        const normalized = normalizeTransactionFkFields(result as any);
        console.log("Loaded invoice data:", {
          result,
          normalized,
          lines: normalized.lines,
        });
        setData(normalized);
        setEditData(normalized);
      } catch (e) {
        setError(getDisplayErrorMessage(e, `Failed to load ${typeLabel}`));
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [
    id,
    modelName,
    typeLabel,
    fetchData,
    dataProp,
    effectiveMode,
    refreshKey,
    initialDataPropUsed,
  ]);

  // Build tabs list - use stable reference for badge count
  const contactCount = data?.refs?.links?.contact?.length ?? 0;
  const lineCount = (data as unknown as Record<string, unknown>)?.lines
    ? ((data as unknown as Record<string, unknown>).lines as unknown[]).length
    : 0;
  // Count comments from all categories (public, process, partner, notes)
  const commentCount = useMemo(() => {
    if (!data?.comments) return 0;
    const c = data.comments as Record<string, unknown>;
    const publicLen = Array.isArray(c.public) ? c.public.length : 0;
    const processLen = Array.isArray(c.process) ? c.process.length : 0;
    const partnerLen = Array.isArray(c.partner) ? c.partner.length : 0;
    const notesLen = Array.isArray(c.notes) ? c.notes.length : 0;
    return publicLen + processLen + partnerLen + notesLen;
  }, [data?.comments]);

  // Count pending actions
  const actionCount = useMemo(() => {
    const actions = data?.actions?.items as
      | Array<{ status?: string }>
      | undefined;
    if (!Array.isArray(actions)) return 0;
    return actions.filter((a) => a.status === "pending").length;
  }, [data?.actions]);

  // Get dynamic custom tabs if function provided
  const dynamicCustomTabsAfter = useMemo(() => {
    if (getCustomTabsAfter && data) {
      return getCustomTabsAfter(data);
    }
    return customTabsAfter;
  }, [getCustomTabsAfter, data, customTabsAfter]);

  const tabs = useMemo(() => {
    const defaultTabs: TransactionTab[] = [
      {
        id: "actions",
        label: "Actions",
        icon: <FaTasks size={14} />,
        badge: actionCount || undefined,
      },
      {
        id: "comments",
        label: "Comments",
        icon: <FaComments size={14} />,
        badge: commentCount || undefined,
      },
      {
        id: "contacts",
        label: "Contacts",
        icon: <FaAddressCard size={14} />,
        badge: contactCount || undefined,
      },
      { id: "documents", label: "Documents", icon: <FaLink size={14} /> },
      {
        id: "financials",
        label: "Financials",
        icon: <FaDollarSign size={14} />,
      },
      { id: "qa", label: "Q&A", icon: <FaQuestionCircle size={14} /> },
      {
        id: "raw",
        label: "Raw",
        icon: <FaEllipsisH size={14} />,
      },
      // { id: "flow", label: "Flow", icon: <FaLink size={14} /> },
    ];

    return [...customTabsBefore, ...defaultTabs, ...dynamicCustomTabsAfter];
  }, [
    customTabsBefore,
    dynamicCustomTabsAfter,
    contactCount,
    lineCount,
    commentCount,
    actionCount,
    isAdmin,
  ]);

  // Handle edit mode
  const handleEdit = () => {
    if (data && canEdit(data)) {
      // Always initialize editData with the latest data (including comments)
      setEditData(normalizeTransactionFkFields({ ...(data as any) }));
      setIsEditing(true);
    }
  };

  const handleCancel = useCallback(() => {
    setEditData(data);
    setIsEditing(false);
  }, [data]);

  // Single save path for all save operations
  const performSave = useCallback(async (): Promise<Transaction | null> => {
    if (!editData) return null;

    if (saveData) {
      // Use custom save function if provided
      const rawId = data?.id;
      const saved = await saveData(editData);
      if (saved) {
        emitModelChanged({
          model: modelName,
          id: (saved as any)?.id ?? null,
          action: rawId ? "updated" : "created",
        });
      }
      return saved;
    }

    // Ensure id is included in payload for updates (omit falsy ids for new records)
    const rawId = data?.id;
    const payloadWithId = {
      ...stripTransactionFkAliases(
        normalizeTransactionFkFields(editData as any),
      ),
      ...(rawId ? { id: rawId } : { id: undefined }),
    };

    // Use transaction-specific save if data has lines, otherwise standard save
    const hasLines = Array.isArray(editData.lines) && editData.lines.length > 0;

    const apiResult = hasLines
      ? await saveTransactionWithLines(modelName, payloadWithId)
      : await saveRecord(modelName, payloadWithId);

    const normalized = normalizeTransactionFkFields(
      (apiResult.record ?? apiResult) as any,
    );

    emitModelChanged({
      model: modelName,
      id: (normalized as any)?.id ?? null,
      action: rawId ? "updated" : "created",
    });

    // If this was a Transfer-created record (new target created from a source),
    // deactivate the source record only when every source line is fully transferred.
    if (!rawId && transferSource) {
      try {
        const sourceResult = await getRecord(
          transferSource.type,
          transferSource.id,
        );
        const sourceRecord = (sourceResult?.record ?? sourceResult) as any;
        const sourceLines = Array.isArray(sourceRecord?.lines)
          ? sourceRecord.lines
          : [];

        const isFullyTransferred =
          sourceLines.length > 0 &&
          sourceLines.every((line: any) => {
            const qty = line?.quantity || {};
            const staged = Number(qty.staged ?? 0);
            const active = Number(qty.active ?? 0);
            const rawRemaining = qty.remaining;
            const remaining = Number(
              rawRemaining ?? (Number.isFinite(active) ? active : 0),
            );
            return Number.isFinite(remaining) ? remaining <= 0 : false;
          });

        if (isFullyTransferred) {
          await saveRecord(transferSource.type, {
            id: transferSource.id,
            is_active: false,
          });

          emitModelChanged({
            model: transferSource.type,
            id: transferSource.id,
            action: "deactivated",
          });
        }
      } catch (e) {
        console.warn(
          "[TransactionDetailBase] Failed to deactivate transfer source:",
          transferSource,
          e,
        );
        dispatch(
          showToast({
            message: `Saved, but could not remove source ${transferSource.type} #${transferSource.id}`,
            type: "info",
          }),
        );
      }
    }

    return normalized;
  }, [
    editData,
    saveData,
    modelName,
    data?.id,
    transferSource,
    dispatch,
    emitModelChanged,
  ]);

  const handleSave = useCallback(async () => {
    if (!editData) return;

    setSaving(true);
    dispatch(showToast({ message: "Saving...", type: "info" }));
    try {
      const result = await performSave();
      if (!result) return;

      const normalized = normalizeTransactionFkFields(result as any);
      setData(normalized); // Update view state
      setEditData(normalized); // Update edit state
      setIsEditing(false);
      setHasUnsavedChanges(false);
      dispatch(
        showToast({
          message: `${typeLabel} saved successfully`,
          type: "success",
        }),
      );
      onSaved?.(result);
    } catch (e) {
      const errorMsg = getDisplayErrorMessage(e, "Failed to save");
      setError(errorMsg);
      dispatch(showToast({ message: errorMsg, type: "error" }));
    } finally {
      setSaving(false);
    }
  }, [editData, performSave, onSaved, dispatch, typeLabel]);

  // Toolbar handlers
  // --- OrgSearchDialog state ---
  const [showOrgDialog, setShowOrgDialog] = useState(false);
  const [orgDialogType, setOrgDialogType] =
    useState<SearchableOrgType>("customer");

  // Determine which org type to assign for this transaction
  // (could be customer, vendor, manufacturer, etc. based on transactionType)
  const getOrgFieldForType = (
    type: string,
  ): { field: string; orgType: SearchableOrgType } => {
    if (["order", "invoice", "proposal", "workorder"].includes(type))
      return { field: "customer_id", orgType: "customer" };
    if (["purchase"].includes(type))
      return { field: "vendor_id", orgType: "vendor" };
    // Extend as needed for other types
    return { field: "customer_id", orgType: "customer" };
  };

  // Handler for Assign Org button
  const handleAssignOrgClick = () => {
    const { orgType } = getOrgFieldForType(transactionType);
    setOrgDialogType(orgType);
    setShowOrgDialog(true);
  };

  // Handler for org selection
  const handleOrgSelected = (org: OrgSearchResult) => {
    const { field } = getOrgFieldForType(transactionType);
    handleFieldChange(field, org.id);
    setShowOrgDialog(false);
  };
  const handleSaveAndClose = useCallback(async () => {
    if (!editData) return;

    setSaving(true);
    dispatch(showToast({ message: "Saving...", type: "info" }));
    try {
      const result = await performSave();
      if (!result) return;

      dispatch(
        showToast({
          message: `${typeLabel} saved successfully`,
          type: "success",
        }),
      );
      onSaved?.(result);

      if (inline) {
        // Inline split-view detail (in a list page)
        // Let the parent list decide how to close.
        // (Some list pages pass onCancelInline, some don't.)
        onCancelInline?.();
        return;
      }

      // Floating window: close it (better UX than navigate(-1)).
      if (windowPath) {
        closeWindow(windowPath);
        return;
      }

      // Fallback for non-window navigation
      navigate(-1);
    } catch (e) {
      const errorMsg = getDisplayErrorMessage(e, "Failed to save");
      setError(errorMsg);
      dispatch(showToast({ message: errorMsg, type: "error" }));
    } finally {
      setSaving(false);
    }
  }, [
    editData,
    performSave,
    navigate,
    onSaved,
    dispatch,
    typeLabel,
    inline,
    onCancelInline,
    windowPath,
    closeWindow,
  ]);

  const handleClone = useCallback(async () => {
    if (!data) return;
    dispatch(showToast({ message: `Cloning ${typeLabel}...`, type: "info" }));
    // Navigate to new page with cloned data (without id/ida)
    const clonedData = { ...data };
    delete (clonedData as Record<string, unknown>).id;
    delete (clonedData as Record<string, unknown>).ida;
    const seg = getTransactionRouteSegment(transactionType);
    navigate(`/transactions/${seg}/detail`, {
      state: { clone: clonedData, mode: "add" },
    });
  }, [
    data,
    transactionType,
    navigate,
    dispatch,
    typeLabel,
    getTransactionRouteSegment,
  ]);

  const handleTransfer = useCallback(
    async (targetType: TransactionType) => {
      if (!data) return;
      dispatch(
        showToast({
          message: `Transferring to ${targetType}...`,
          type: "info",
        }),
      );
      // Build query params to pass transfer source info through the window path
      const params = new URLSearchParams();
      params.set("transfer_from_type", transactionType);
      params.set("transfer_from_id", String(data.id));
      if (data.customer_id) params.set("customer_id", String(data.customer_id));
      const seg = getTransactionRouteSegment(targetType);
      const path = `/transactions/${seg}/detail?${params.toString()}`;
      const label = targetType.charAt(0).toUpperCase() + targetType.slice(1);
      ensureWindow(path, `New ${label} (from ${typeLabel})`, {
        maximized: false,
      });
    },
    [
      data,
      transactionType,
      ensureWindow,
      dispatch,
      typeLabel,
      getTransactionRouteSegment,
    ],
  );

  const [showPrintPreview, setShowPrintPreview] = useState(false);

  // FormCoach — validates data completeness before print
  const formCoach = useFormCoach(
    data as Record<string, unknown> | null,
    transactionType as TransactionModelType,
  );

  // Internal print handler (called after unsaved changes guard)
  const executePrint = useCallback(() => {
    if (onPrint && data) {
      onPrint(data);
    } else {
      // Run the form coach check before showing print preview
      formCoach.runCheck();
      setShowPrintPreview(true);
    }
  }, [onPrint, data, formCoach]);

  // Guarded print handler - warns if there are unsaved changes
  const handlePrint = useMemo(
    () => guardAction(executePrint, "printing"),
    [guardAction, executePrint],
  );
  // ...existing code...

  // Print Preview Modal rendering
  // Uses appropriate print document based on transaction type
  const renderPrintPreview = () => {
    if (!showPrintPreview || !data) return null;

    // Try to get document number based on type
    const docNum =
      transactionType === "invoice"
        ? (data as any).invoice_no || (data as any).ida || data.id
        : transactionType === "order"
        ? (data as any).order_no || (data as any).ida || data.id
        : (data as any).ida || data.id;

    // Transform transaction data to print format based on type
    const printContent = (() => {
      switch (transactionType) {
        case "invoice":
          // Transform Transaction to InvoicePrintData
          const invoiceData = {
            id: data.id,
            ida: (data as any).ida || data.ida,
            invoiceNum:
              (data as any).invoice_no || (data as any).ida || data.ida,
            orderNum: (data as any).order_no,
            status: data.status,

            // Customer info from refs
            customerID: data.customer_id,
            firstName:
              data.refs?.links?.customer?.[0]?.name_first ||
              data.refs?.links?.contact?.find(
                (c: any) => c.purpose === "billto",
              )?.name_first,
            lastName:
              data.refs?.links?.customer?.[0]?.name_last ||
              data.refs?.links?.contact?.find(
                (c: any) => c.purpose === "billto",
              )?.name_last,
            company:
              data.refs?.links?.customer?.[0]?.company ||
              data.refs?.links?.customer?.[0]?.display_name,
            attention:
              data.attention ||
              data.refs?.links?.contact?.find(
                (c: any) => c.purpose === "billto",
              )?.display_name,
            address1: data.refs?.links?.customer?.[0]?.address_full,
            phone: data.phone || data.refs?.links?.customer?.[0]?.phone,
            phoneCell: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.phone,
            email: data.email || data.refs?.links?.customer?.[0]?.email,

            // Document details
            dateCreated: data.dt_created
              ? new Date(data.dt_created).toISOString().split("T")[0]
              : undefined,
            dateInvoiced: (data as any).dt
              ? new Date((data as any).dt).toISOString().split("T")[0]
              : undefined,
            dateShipped: (data as any).ship_date
              ? new Date((data as any).ship_date).toISOString().split("T")[0]
              : undefined,
            dateDue: (data as any).due_date
              ? new Date((data as any).due_date).toISOString().split("T")[0]
              : undefined,
            custPONum: (data as any).po_number,
            salesNameId: (data as any).sales_name_id,
            terms: (data as any).terms || data.terms,
            fob: (data as any).fob,
            shipVia: (data as any).ship_via,
            typeSale: data.price_level,
            taxJuris: (data as any).tax_jurisdiction,
            orderedBy: (data as any).ordered_by,
            packedBy: (data as any).packed_by,
            contractDetailTag: (data as any).contract_detail_tag,

            // Financials
            amount: data.totals?.subtotal,
            salesTax: data.totals?.tax,
            shipTotal: data.totals?.shipping,
            total: data.totals?.total,
            downPayment: (data as any).down_payment,
            amountPaid: (data as any).amount_paid || data.totals?.received,
            balanceDue: data.totals?.balance,
            invoices_BalanceDue: data.totals?.balance,

            // Comments
            comment: extractPublicComment(data.comments?.public),
            contractDetail:
              (data as any).contract_detail || data.conditions_description,
            pvTermState: (data as any).pv_term_state,
            shipInstruct: (data as any).ship_instruct,

            // Lines
            lines: (data.lines || []).map((line: any, idx: number) => ({
              id: line.id,
              lineNum: line.line_number || idx + 1,
              itemNum: line.item?.ida_item,
              description: line.item?.description,
              qty: line.quantity?.staged,
              qtyShipped: line.quantity?.active ?? quantity?.active,
              unitPrice: line.price?.unit,
              msrp: line.price?.unit,
              discount: line.price?.discount_amount,
              discountedPrice: line.price?.unit,
              extendedPrice: line.price?.extended,
            })),
          };

          console.log("Invoice data for print:", {
            invoiceData,
            lines: invoiceData.lines,
          });
          return (
            <InvoicePrintDocument
              data={invoiceData}
              lines={invoiceData.lines}
            />
          );

        case "order":
          // Transform Transaction to OrderPrintData with contact extraction
          const orderData = {
            id: data.id,
            ida: (data as any).ida || data.ida,
            orderNum: (data as any).order_no || data.ida,
            status: data.status,

            // Customer info from refs - handle both array and object formats
            customerID: data.customer_id,
            firstName: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.name_first,
            lastName: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.name_last,
            company: Array.isArray(data.refs?.links?.customer)
              ? data.refs?.links?.customer?.[0]?.company ||
                data.refs?.links?.customer?.[0]?.display_name
              : (data.refs?.links?.customer as any)?.company ||
                (data.refs?.links?.customer as any)?.display_name,
            attention:
              data.attention ||
              data.refs?.links?.contact?.find(
                (c: any) => c.purpose === "billto",
              )?.display_name,
            address1: Array.isArray(data.refs?.links?.customer)
              ? data.refs?.links?.customer?.[0]?.address_full
              : (data.refs?.links?.customer as any)?.address_full,
            address2: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.address_full,
            city: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.city,
            state: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.state,
            zip: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.zip,
            country: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.country,
            phone:
              data.phone ||
              (Array.isArray(data.refs?.links?.customer)
                ? data.refs?.links?.customer?.[0]?.phone
                : (data.refs?.links?.customer as any)?.phone),
            phoneCell: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.phone,
            email:
              data.email ||
              (Array.isArray(data.refs?.links?.customer)
                ? data.refs?.links?.customer?.[0]?.email
                : (data.refs?.links?.customer as any)?.email),

            // Shipping contact info
            shipAttention: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.display_name,
            shipAddress1: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.address_full,
            shipAddress2: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.address_full,
            shipCity: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.city,
            shipState: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.state,
            shipZip: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.zip,
            shipCountry: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.country,
            shipPhone: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.phone,

            // Document details
            dateCreated: (() => {
              try {
                return data.dt_created
                  ? new Date(data.dt_created).toISOString().split("T")[0]
                  : undefined;
              } catch {
                return undefined;
              }
            })(),
            dateOrdered: (() => {
              try {
                return (data as any).dt
                  ? new Date((data as any).dt).toISOString().split("T")[0]
                  : undefined;
              } catch {
                return undefined;
              }
            })(),
            dateShipped: (() => {
              try {
                return (data as any).ship_date
                  ? new Date((data as any).ship_date)
                      .toISOString()
                      .split("T")[0]
                  : undefined;
              } catch {
                return undefined;
              }
            })(),
            dateNeeded: (() => {
              try {
                return (data as any).due_date
                  ? new Date((data as any).due_date).toISOString().split("T")[0]
                  : undefined;
              } catch {
                return undefined;
              }
            })(),
            custPONum: (data as any).po_number,
            salesNameId: (data as any).sales_name_id,
            terms: (data as any).terms || data.terms,
            fob: (data as any).fob,
            shipVia: (data as any).ship_via,
            typeSale: data.price_level,
            taxJuris: (data as any).tax_jurisdiction,
            orderedBy: (data as any).ordered_by,
            actionBy: (data as any).action_by,
            contractDetailTag: (data as any).contract_detail_tag,

            // Financials
            amount: data.totals?.subtotal,
            salesTax: data.totals?.tax,
            shipTotal: data.totals?.shipping,
            total: data.totals?.total,
            balanceDueEstimated: data.totals?.balance,

            // Comments
            comment: extractPublicComment(data.comments?.public),
            contractDetail:
              (data as any).contract_detail || data.conditions_description,
            pvTermState: (data as any).pv_term_state,
            shipInstruct: (data as any).ship_instruct,

            // Lines
            lines: (data.lines || []).map((line: any, idx: number) => ({
              id: line.id,
              lineNum: line.line_number || idx + 1,
              itemNum: line.item?.ida_item,
              description: line.item?.description || "",
              qtyOrdered: line.quantity?.staged || 0,
              qtyShipped: line.quantity?.active || 0,
              unitPrice: line.price?.unit || 0,
              msrp: line.price?.unit || 0,
              discount: line.price?.discount_amount || 0,
              discountedPrice: line.price?.unit || 0,
              extendedPrice: line.price?.extended || 0,
            })),
          };

          console.log("Order data for print:", {
            orderData,
            lines: orderData.lines,
          });
          return (
            <OrderPrintDocument data={orderData} lines={orderData.lines} />
          );

        case "proposal":
          // Transform Transaction to ProposalPrintData with contact extraction
          const proposalData = {
            id: data.id,
            ida: (data as any).ida || data.ida,
            proposalNum:
              (data as any).proposal_no || (data as any).ida || data.ida,
            status: data.status,

            // Customer info from refs
            customerID: data.customer_id,
            firstName: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.name_first,
            lastName: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.name_last,
            company:
              data.refs?.links?.customer?.[0]?.company ||
              data.refs?.links?.customer?.[0]?.display_name,
            attention:
              data.attention ||
              data.refs?.links?.contact?.find(
                (c: any) => c.purpose === "billto",
              )?.display_name,
            address1: data.refs?.links?.customer?.[0]?.address_full,
            address2: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.address_full,
            city: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.city,
            state: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.state,
            zip: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.zip,
            country: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.country,
            phone: data.phone || data.refs?.links?.customer?.[0]?.phone,
            phoneCell: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.phone,
            email: data.email || data.refs?.links?.customer?.[0]?.email,

            // Shipping contact info
            shipAttention: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.display_name,
            shipAddress1: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.address_full,
            shipAddress2: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.address_full,
            shipCity: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.city,
            shipState: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.state,
            shipZip: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.zip,
            shipCountry: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.country,
            shipPhone: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.phone,

            // Document details
            dateCreated: data.dt_created
              ? new Date(data.dt_created).toISOString().split("T")[0]
              : undefined,
            dateOrdered: (data as any).dt
              ? new Date((data as any).dt).toISOString().split("T")[0]
              : undefined,
            dateShipped: (data as any).ship_date
              ? new Date((data as any).ship_date).toISOString().split("T")[0]
              : undefined,
            dateNeeded: (data as any).due_date
              ? new Date((data as any).due_date).toISOString().split("T")[0]
              : undefined,
            custPONum: (data as any).po_number,
            salesNameId: (data as any).sales_name_id,
            terms: (data as any).terms || data.terms,
            fob: (data as any).fob,
            shipVia: (data as any).ship_via,
            typeSale: data.price_level,
            taxJuris: (data as any).tax_jurisdiction,
            orderedBy: (data as any).ordered_by,
            actionBy: (data as any).action_by,
            contractDetailTag: (data as any).contract_detail_tag,

            // Financials
            amount: data.totals?.subtotal,
            salesTax: data.totals?.tax,
            shipTotal: data.totals?.shipping,
            total: data.totals?.total,
            balanceDueEstimated: data.totals?.balance,

            // Comments
            comment: extractPublicComment(data.comments?.public),
            contractDetail:
              (data as any).contract_detail || data.conditions_description,
            pvTermState: (data as any).pv_term_state,
            shipInstruct: (data as any).ship_instruct,

            // Lines
            lines: (data.lines || []).map((line: any, idx: number) => ({
              id: line.id,
              lineNum: line.line_number || idx + 1,
              itemNum: line.item?.ida_item,
              description: line.item?.description,
              qtyOrdered: line.quantity?.staged,
              qtyShipped: line.quantity?.active ?? quantity?.active,
              unitPrice: line.price?.unit,
              msrp: line.price?.unit,
              discount: line.price?.discount_amount,
              discountedPrice: line.price?.unit,
              extendedPrice: line.price?.extended,
            })),
          };

          console.log("Proposal data for print:", {
            proposalData,
            lines: proposalData.lines,
          });
          return (
            <ProposalPrintDocument
              data={proposalData}
              lines={proposalData.lines}
            />
          );

        case "purchase":
          // Transform Transaction to PurchasePrintData with contact extraction
          const purchaseData = {
            id: data.id,
            ida: (data as any).ida || data.ida,
            purchaseNum:
              (data as any).purchase_no || (data as any).ida || data.ida,
            status: data.status,

            // Vendor info from refs
            vendorID: data.vendor_id,
            firstName: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.name_first,
            lastName: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.name_last,
            company:
              data.refs?.links?.customer?.[0]?.company ||
              data.refs?.links?.customer?.[0]?.display_name,
            attention:
              data.attention ||
              data.refs?.links?.contact?.find(
                (c: any) => c.purpose === "billto",
              )?.display_name,
            address1: data.refs?.links?.customer?.[0]?.address_full,
            address2: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.address_full,
            city: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.city,
            state: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.state,
            zip: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.zip,
            country: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.country,
            phone: data.phone || data.refs?.links?.customer?.[0]?.phone,
            phoneCell: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.phone,
            email: data.email || data.refs?.links?.customer?.[0]?.email,

            // Shipping contact info
            shipAttention: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.display_name,
            shipAddress1: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.address_full,
            shipAddress2: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.address_full,
            shipCity: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.city,
            shipState: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.state,
            shipZip: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.zip,
            shipCountry: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.country,
            shipPhone: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.phone,

            // Document details
            dateCreated: data.dt_created
              ? new Date(data.dt_created).toISOString().split("T")[0]
              : undefined,
            dateOrdered: (data as any).dt
              ? new Date((data as any).dt).toISOString().split("T")[0]
              : undefined,
            dateShipped: (data as any).ship_date
              ? new Date((data as any).ship_date).toISOString().split("T")[0]
              : undefined,
            dateNeeded: (data as any).due_date
              ? new Date((data as any).due_date).toISOString().split("T")[0]
              : undefined,
            custPONum: (data as any).po_number,
            salesNameId: (data as any).sales_name_id,
            terms: (data as any).terms || data.terms,
            fob: (data as any).fob,
            shipVia: (data as any).ship_via,
            typeSale: data.price_level,
            taxJuris: (data as any).tax_jurisdiction,
            orderedBy: (data as any).ordered_by,
            actionBy: (data as any).action_by,
            contractDetailTag: (data as any).contract_detail_tag,

            // Financials
            amount: data.totals?.subtotal,
            salesTax: data.totals?.tax,
            shipTotal: data.totals?.shipping,
            total: data.totals?.total,
            balanceDueEstimated: data.totals?.balance,

            // Comments
            comment: extractPublicComment(data.comments?.public),
            contractDetail:
              (data as any).contract_detail || data.conditions_description,
            pvTermState: (data as any).pv_term_state,
            shipInstruct: (data as any).ship_instruct,

            // Lines
            lines: (data.lines || []).map((line: any, idx: number) => ({
              id: line.id,
              lineNum: line.line_number || idx + 1,
              itemNum: line.item?.ida_item,
              description: line.item?.description,
              qtyOrdered: line.quantity?.staged,
              qtyShipped: line.quantity?.active ?? quantity?.active,
              unitPrice: line.price?.unit,
              msrp: line.price?.unit,
              discount: line.price?.discount_amount,
              discountedPrice: line.price?.unit,
              extendedPrice: line.price?.extended,
            })),
          };

          console.log("Purchase data for print:", {
            purchaseData,
            lines: purchaseData.lines,
          });
          return (
            <PurchasePrintDocument
              data={purchaseData}
              lines={purchaseData.lines}
            />
          );

        case "workorder":
          // Transform Transaction to WorkorderPrintData with contact extraction
          const workorderData = {
            id: data.id,
            ida: (data as any).ida || data.ida,
            workorderNum:
              (data as any).workorder_no || (data as any).ida || data.ida,
            status: data.status,

            // Customer info from refs
            customerID: data.customer_id,
            firstName: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.name_first,
            lastName: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.name_last,
            company:
              data.refs?.links?.customer?.[0]?.company ||
              data.refs?.links?.customer?.[0]?.display_name,
            attention:
              data.attention ||
              data.refs?.links?.contact?.find(
                (c: any) => c.purpose === "billto",
              )?.display_name,
            address1: data.refs?.links?.customer?.[0]?.address_full,
            address2: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.address_full,
            city: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.city,
            state: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.state,
            zip: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.zip,
            country: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.country,
            phone: data.phone || data.refs?.links?.customer?.[0]?.phone,
            phoneCell: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.phone,
            email: data.email || data.refs?.links?.customer?.[0]?.email,

            // Shipping contact info
            shipAttention: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.display_name,
            shipAddress1: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.address_full,
            shipAddress2: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.address_full,
            shipCity: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.city,
            shipState: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.state,
            shipZip: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.zip,
            shipCountry: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.country,
            shipPhone: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.phone,

            // Document details
            dateCreated: data.dt_created
              ? new Date(data.dt_created).toISOString().split("T")[0]
              : undefined,
            dateOrdered: (data as any).dt
              ? new Date((data as any).dt).toISOString().split("T")[0]
              : undefined,
            dateShipped: (data as any).ship_date
              ? new Date((data as any).ship_date).toISOString().split("T")[0]
              : undefined,
            dateNeeded: (data as any).due_date
              ? new Date((data as any).due_date).toISOString().split("T")[0]
              : undefined,
            custPONum: (data as any).po_number,
            salesNameId: (data as any).sales_name_id,
            terms: (data as any).terms || data.terms,
            fob: (data as any).fob,
            shipVia: (data as any).ship_via,
            typeSale: data.price_level,
            taxJuris: (data as any).tax_jurisdiction,
            orderedBy: (data as any).ordered_by,
            actionBy: (data as any).action_by,
            contractDetailTag: (data as any).contract_detail_tag,

            // Financials
            amount: data.totals?.subtotal,
            salesTax: data.totals?.tax,
            shipTotal: data.totals?.shipping,
            total: data.totals?.total,
            balanceDueEstimated: data.totals?.balance,

            // Comments
            comment: extractPublicComment(data.comments?.public),
            contractDetail:
              (data as any).contract_detail || data.conditions_description,
            pvTermState: (data as any).pv_term_state,
            shipInstruct: (data as any).ship_instruct,

            // Lines
            lines: (data.lines || []).map((line: any, idx: number) => ({
              id: line.id,
              lineNum: line.line_number || idx + 1,
              itemNum: line.item?.ida_item,
              description: line.item?.description,
              qtyOrdered: line.quantity?.staged,
              qtyShipped: line.quantity?.active ?? quantity?.active,
              unitPrice: line.price?.unit,
              msrp: line.price?.unit,
              discount: line.price?.discount_amount,
              discountedPrice: line.price?.unit,
              extendedPrice: line.price?.extended,
            })),
          };

          console.log("Workorder data for print:", {
            workorderData,
            lines: workorderData.lines,
          });
          return (
            <WorkorderPrintDocument
              data={workorderData}
              lines={workorderData.lines}
            />
          );

        case "receipt":
          // Transform Transaction to ReceiptPrintData with contact extraction
          const receiptData = {
            id: data.id,
            ida: (data as any).ida || data.ida,
            receiptNum:
              (data as any).receipt_no || (data as any).ida || data.ida,
            status: data.status,

            // Vendor info from refs
            vendorID: data.vendor_id,
            firstName: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.name_first,
            lastName: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.name_last,
            company:
              data.refs?.links?.customer?.[0]?.company ||
              data.refs?.links?.customer?.[0]?.display_name,
            attention:
              data.attention ||
              data.refs?.links?.contact?.find(
                (c: any) => c.purpose === "billto",
              )?.display_name,
            address1: data.refs?.links?.customer?.[0]?.address_full,
            address2: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.address_full,
            city: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.city,
            state: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.state,
            zip: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.zip,
            country: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.country,
            phone: data.phone || data.refs?.links?.customer?.[0]?.phone,
            phoneCell: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.phone,
            email: data.email || data.refs?.links?.customer?.[0]?.email,

            // Shipping contact info
            shipAttention: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.display_name,
            shipAddress1: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.address_full,
            shipAddress2: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.address_full,
            shipCity: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.city,
            shipState: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.state,
            shipZip: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.zip,
            shipCountry: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.country,
            shipPhone: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.phone,

            // Document details
            dateCreated: data.dt_created
              ? new Date(data.dt_created).toISOString().split("T")[0]
              : undefined,
            dateOrdered: (data as any).dt
              ? new Date((data as any).dt).toISOString().split("T")[0]
              : undefined,
            dateShipped: (data as any).ship_date
              ? new Date((data as any).ship_date).toISOString().split("T")[0]
              : undefined,
            dateNeeded: (data as any).due_date
              ? new Date((data as any).due_date).toISOString().split("T")[0]
              : undefined,
            custPONum: (data as any).po_number,
            salesNameId: (data as any).sales_name_id,
            terms: (data as any).terms || data.terms,
            fob: (data as any).fob,
            shipVia: (data as any).ship_via,
            typeSale: data.price_level,
            taxJuris: (data as any).tax_jurisdiction,
            orderedBy: (data as any).ordered_by,
            actionBy: (data as any).action_by,
            contractDetailTag: (data as any).contract_detail_tag,

            // Financials
            amount: data.totals?.subtotal,
            salesTax: data.totals?.tax,
            shipTotal: data.totals?.shipping,
            total: data.totals?.total,
            balanceDueEstimated: data.totals?.balance,

            // Comments
            comment: extractPublicComment(data.comments?.public),
            contractDetail:
              (data as any).contract_detail || data.conditions_description,
            pvTermState: (data as any).pv_term_state,
            shipInstruct: (data as any).ship_instruct,

            // Lines
            lines: (data.lines || []).map((line: any, idx: number) => ({
              id: line.id,
              lineNum: line.line_number || idx + 1,
              itemNum: line.item?.ida_item,
              description: line.item?.description,
              qtyOrdered: line.quantity?.staged,
              qtyShipped: line.quantity?.active ?? quantity?.active,
              unitPrice: line.price?.unit,
              msrp: line.price?.unit,
              discount: line.price?.discount_amount,
              discountedPrice: line.price?.unit,
              extendedPrice: line.price?.extended,
            })),
          };

          console.log("Receipt data for print:", {
            receiptData,
            lines: receiptData.lines,
          });
          return (
            <ReceiptPrintDocument
              data={receiptData}
              lines={receiptData.lines}
            />
          );

        case "adjustment":
          // Transform Transaction to AdjustmentPrintData with contact extraction
          const adjustmentData = {
            id: data.id,
            ida: (data as any).ida || data.ida,
            adjustmentNum:
              (data as any).adjustment_no || (data as any).ida || data.ida,
            status: data.status,

            // Customer/Vendor info from refs
            customerID: data.customer_id,
            vendorID: data.vendor_id,
            firstName: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.name_first,
            lastName: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.name_last,
            company:
              data.refs?.links?.customer?.[0]?.company ||
              data.refs?.links?.customer?.[0]?.display_name,
            attention:
              data.attention ||
              data.refs?.links?.contact?.find(
                (c: any) => c.purpose === "billto",
              )?.display_name,
            address1: data.refs?.links?.customer?.[0]?.address_full,
            address2: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.address_full,
            city: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.city,
            state: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.state,
            zip: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.zip,
            country: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.country,
            phone: data.phone || data.refs?.links?.customer?.[0]?.phone,
            phoneCell: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "billto",
            )?.phone,
            email: data.email || data.refs?.links?.customer?.[0]?.email,

            // Shipping contact info
            shipAttention: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.display_name,
            shipAddress1: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.address_full,
            shipAddress2: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.address_full,
            shipCity: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.city,
            shipState: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.state,
            shipZip: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.zip,
            shipCountry: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.country,
            shipPhone: data.refs?.links?.contact?.find(
              (c: any) => c.purpose === "shipto",
            )?.phone,

            // Document details
            dateCreated: data.dt_created
              ? new Date(data.dt_created).toISOString().split("T")[0]
              : undefined,
            dateOrdered: (data as any).dt
              ? new Date((data as any).dt).toISOString().split("T")[0]
              : undefined,
            dateShipped: (data as any).ship_date
              ? new Date((data as any).ship_date).toISOString().split("T")[0]
              : undefined,
            dateNeeded: (data as any).due_date
              ? new Date((data as any).due_date).toISOString().split("T")[0]
              : undefined,
            custPONum: (data as any).po_number,
            salesNameId: (data as any).sales_name_id,
            terms: (data as any).terms || data.terms,
            fob: (data as any).fob,
            shipVia: (data as any).ship_via,
            typeSale: data.price_level,
            taxJuris: (data as any).tax_jurisdiction,
            orderedBy: (data as any).ordered_by,
            actionBy: (data as any).action_by,
            contractDetailTag: (data as any).contract_detail_tag,

            // Financials
            amount: data.totals?.subtotal,
            salesTax: data.totals?.tax,
            shipTotal: data.totals?.shipping,
            total: data.totals?.total,
            balanceDueEstimated: data.totals?.balance,

            // Comments
            comment: extractPublicComment(data.comments?.public),
            contractDetail:
              (data as any).contract_detail || data.conditions_description,
            pvTermState: (data as any).pv_term_state,
            shipInstruct: (data as any).ship_instruct,

            // Lines
            lines: (data.lines || []).map((line: any, idx: number) => ({
              id: line.id,
              lineNum: line.line_number || idx + 1,
              itemNum: line.item?.ida_item,
              description: line.item?.description,
              qtyOrdered: line.quantity?.staged,
              qtyShipped: line.quantity?.active ?? quantity?.active,
              unitPrice: line.price?.unit,
              msrp: line.price?.unit,
              discount: line.price?.discount_amount,
              discountedPrice: line.price?.unit,
              extendedPrice: line.price?.extended,
            })),
          };

          console.log("Adjustment data for print:", {
            adjustmentData,
            lines: adjustmentData.lines,
          });
          return (
            <AdjustmentPrintDocument
              data={adjustmentData}
              lines={adjustmentData.lines}
            />
          );

        default:
          // Fallback to order print for other types
          return <OrderPrintDocument data={data as any} />;
      }
    })();

    return (
      <PrintPreviewModal
        isOpen={showPrintPreview}
        onClose={() => setShowPrintPreview(false)}
        documentType={typeLabel}
        documentNumber={docNum}
      >
        {/* FormCoach warnings inside the print preview */}
        {formCoach.hasIssues && (
          <FormCoachAlert
            issues={formCoach.issues}
            compact
            className="mb-4 print:hidden"
          />
        )}
        {printContent}
      </PrintPreviewModal>
    );
  };

  const handleEmail = useCallback(() => {
    if (onEmail && data) {
      onEmail(data);
    } else {
      dispatch(
        showToast({ message: "Email functionality coming soon", type: "info" }),
      );
    }
  }, [onEmail, data, dispatch]);

  const handleDelete = useCallback(async () => {
    if (!data?.id) return;

    try {
      dispatch(
        showToast({ message: `Deleting ${typeLabel}...`, type: "info" }),
      );
      await deleteRecord(modelName, data.id);
      dispatch(
        showToast({
          message: `${typeLabel} deleted successfully`,
          type: "success",
        }),
      );
      navigate(`/transactions/${transactionType}s`);
    } catch (e) {
      const errorMsg = getDisplayErrorMessage(e, "Failed to delete");
      setError(errorMsg);
      dispatch(showToast({ message: errorMsg, type: "error" }));
    }
  }, [data, modelName, transactionType, navigate, dispatch, typeLabel]);

  // Check if form has changed
  const isDirty = useMemo(() => {
    if (!data || !editData) return false;
    return JSON.stringify(data) !== JSON.stringify(editData);
  }, [data, editData]);

  // currentData must be computed before hooks that depend on it,
  // and hooks must come before any early returns (Rules of Hooks).
  const currentData = isEditing && editData ? editData : data;

  // --- Real-time totals from lines ---
  // Recomputes sell/cost/totals whenever lines change during editing,
  // so SummaryCard and FinancialsCard always show up-to-date values.
  const liveCalc = useRealTimeCalculations(
    currentData?.lines ?? [],
    transactionType,
    currentData?.totals?.received ?? null,
  );

  // Merge live calculations with currentData's totals.
  // During editing the live values override stale server values;
  // in view mode the server values are authoritative.
  const liveTotals = useMemo(() => {
    if (!currentData) return undefined;
    const hasLines = (currentData.lines?.length ?? 0) > 0;
    if (!hasLines) return currentData.totals;
    return {
      ...currentData.totals,
      subtotal: liveCalc.sell.line_sum_goods,
      discount: liveCalc.sell.discount,
      taxable:
        (liveCalc.sell.line_sum_goods ?? 0) - (liveCalc.sell.discount ?? 0),
      tax: currentData.totals?.tax ?? 0,
      shipping: currentData.totals?.shipping ?? 0,
      other: currentData.totals?.other ?? 0,
      total: liveCalc.totals.total,
      cost: liveCalc.totals.cost,
      margin: liveCalc.totals.margin,
      margin_pc: liveCalc.totals.margin_pc,
      received: liveCalc.totals.received,
      balance: liveCalc.totals.balance,
    };
  }, [currentData, liveCalc]);
  const liveSell = useMemo(() => {
    if (!currentData) return undefined;
    const hasLines = (currentData.lines?.length ?? 0) > 0;
    return hasLines ? liveCalc.sell : currentData.sell;
  }, [currentData, liveCalc]);
  const liveCost = useMemo(() => {
    if (!currentData) return undefined;
    const hasLines = (currentData.lines?.length ?? 0) > 0;
    return hasLines ? liveCalc.cost : currentData.cost;
  }, [currentData, liveCalc]);

  // Build a currentData view that includes live totals for SummaryCard
  const currentDataWithTotals = useMemo(() => {
    if (!currentData) return currentData;
    return {
      ...currentData,
      totals: liveTotals,
      sell: liveSell,
      cost: liveCost,
    };
  }, [currentData, liveTotals, liveSell, liveCost]);

  // Handle field changes during edit
  const handleFieldChange = (field: string, value: unknown) => {
    if (editData) {
      // Deep merge for comments to persist tab messages
      let newData;
      if (field === "comments" && typeof value === "object" && value !== null) {
        newData = {
          ...editData,
          comments: {
            ...editData.comments,
            ...value,
          },
        };
      } else {
        newData = { ...editData, [field]: value } as Transaction;
      }
      setEditData(newData);
    } else {
      console.warn(
        "[TransactionDetailBase] handleFieldChange called but editData is null!",
      );
    }
  };

  // Render loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  // Render error state
  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-red-500">
        <p className="text-lg font-medium">Error loading {typeLabel}</p>
        <p className="text-sm">{error ?? "Not found"}</p>
        <button
          onClick={() => navigate(-1)}
          className="mt-4 px-4 py-2 text-sm text-blue-500 hover:underline"
        >
          Go Back
        </button>
      </div>
    );
  }

  // --- data is guaranteed non-null below this point ---
  const onLinesChange = (newLines: TransactionLine[]) => {
    if (isEditing && editData) {
      setEditData({ ...editData, lines: newLines });
      setHasUnsavedChanges(true);
    }
  };

  // Render tab content
  const renderTabContent = () => {
    // Check for custom tab first
    if (renderCustomTab && currentData) {
      const customContent = renderCustomTab(
        activeTab,
        currentData,
        isEditing,
        handleFieldChange,
      );
      if (customContent) return customContent;
    }

    switch (activeTab) {
      case "actions": {
        const actions = (currentData?.actions?.items ?? []) as Array<{
          id?: number;
          status?: string;
          action?: string | { en?: string };
          what?: string;
        }>;
        const getStatusClass = (status?: string) =>
          status === "done"
            ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
            : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";

        return (
          <div className="p-4">
            {actions.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <FaTasks size={32} className="mx-auto mb-3 opacity-50" />
                <p>No actions on this {typeLabel.toLowerCase()}</p>
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
                        className={`px-2 py-1 text-xs rounded-full ${getStatusClass(
                          action.status,
                        )}`}
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
      }

      case "contacts":
        // Use normalization helper to parse contacts from API
        return (
          <ContactPanel
            contacts={normalizeRefsLinksContact(
              currentData?.refs?.links?.contact ?? [],
            )}
            isEditing={isEditing}
            parent_model={modelName}
            parentId={currentData?.id}
            customer_id={
              currentData?.customer_id ||
              currentData?.refs?.links?.customer?.[0]?.id
            }
            customer_name={
              currentData?.refs?.links?.customer?.[0]?.display_name
            }
            onChange={(newContacts) => {
              // Update editData.refs.links.contact in edit mode
              if (isEditing && editData) {
                setEditData({
                  ...editData,
                  refs: {
                    ...editData.refs,
                    links: {
                      ...(editData.refs?.links || {}),
                      contact: newContacts as unknown as NonNullable<
                        NonNullable<typeof editData.refs>["links"]
                      >["contact"],
                    },
                  },
                });
                setHasUnsavedChanges(true);
              }
            }}
            onSaveSuccess={async () => {
              // Refresh data after successful contact save
              console.log(
                "[TransactionDetailBase] Contact saved, refreshing from API...",
              );
              // Force refetch from API - this will update both data and editData
              refreshData();
            }}
          />
        );

      case "comments":
        // Always use editData.comments if editing, otherwise data.comments
        const commentsSource =
          isEditing && editData ? editData.comments : data?.comments;

        // Transform CommentEntry[] to CommentMessage[] format for CommentsPanel
        const transformedComments = commentsSource
          ? {
              ...commentsSource,
              notes: (commentsSource.notes ?? []).map((entry) =>
                "user" in entry
                  ? (entry as Record<string, unknown>) // Already in correct format
                  : {
                      // Transform CommentEntry to CommentMessage
                      user:
                        ((entry as unknown as Record<string, unknown>)
                          .by as string) || "Unknown",
                      mgs:
                        ((entry as unknown as Record<string, unknown>)
                          .text as string) || "",
                      time:
                        ((entry as unknown as Record<string, unknown>)
                          .ts as string) || new Date().toISOString(),
                    },
              ),
            }
          : {};

        // Auto-save comments handler
        const handleCommentsSave = async (
          newComments: Parameters<
            NonNullable<React.ComponentProps<typeof CommentsPanel>["onSave"]>
          >[0],
        ) => {
          if (!editData) return;

          const payloadWithComments = {
            ...editData,
            comments: {
              ...editData.comments,
              ...newComments,
            },
            id: data?.id,
          };

          console.log(
            "[TransactionDetailBase] Auto-saving comments...",
            payloadWithComments.comments,
          );
          dispatch(showToast({ message: "Saving comment...", type: "info" }));

          try {
            const hasLines =
              Array.isArray(editData.lines) && editData.lines.length > 0;
            const apiResult = hasLines
              ? await saveTransactionWithLines(modelName, payloadWithComments)
              : await saveRecord(modelName, payloadWithComments);

            const result = apiResult.record ?? apiResult;
            console.log(
              "[TransactionDetailBase] Comments auto-save success!",
              result?.comments,
            );

            // Update local state with saved data
            setData(result);
            setEditData(result);
            dispatch(showToast({ message: "Comment saved!", type: "success" }));
          } catch (error) {
            console.error(
              "[TransactionDetailBase] Comments auto-save failed:",
              error,
            );
            dispatch(
              showToast({ message: "Failed to save comment", type: "error" }),
            );
            throw error;
          }
        };

        return currentData ? (
          <CommentsPanel
            entityType={modelName as any}
            entityId={Number(currentData?.id ?? 0)}
            comments={transformedComments as Record<string, unknown>}
            isEditing={isEditing}
            onChange={(val) => handleFieldChange("comments", val)}
            onSave={handleCommentsSave}
            currentUser={displayName}
            currentUserId={user?.id}
          />
        ) : null;

      case "financials":
        return currentData ? (
          <FinancialsCard
            totals={liveTotals}
            cost={liveCost}
            sell={liveSell}
            currency={currentData.currency}
            isEditing={isEditing}
          />
        ) : null;

      case "documents":
        return (
          <DocumentsPanel
            parent_model={modelName}
            parentId={currentData?.id}
            data={(currentData as any)?.refs?.links?.document ?? []}
            readOnly={!isEditing}
            onChange={
              isEditing
                ? (nextDocs) => {
                    const nextRefs = {
                      ...(currentData as any)?.refs,
                      links: {
                        ...(currentData as any)?.refs?.links,
                        document: nextDocs,
                      },
                    };
                    handleFieldChange("refs", nextRefs);
                  }
                : undefined
            }
          />
        );

      case "qa":
        return (
          <QATab
            transactionType={transactionType}
            transactionId={currentData?.id}
            canEdit={isEditing}
          />
        );

      case "raw":
        return (
          <JsonFieldEditor
            label="Full Transaction JSON"
            value={currentData}
            readonly
            defaultExpanded
            maxHeight="600px"
          />
        );

      default:
        return (
          <div className="text-slate-400 text-center py-8">
            Tab not found: {activeTab}
          </div>
        );
    }
  };
  const priceLable = [
    { value: "A", label: "A - Retail" },
    { value: "B", label: "B - Wholesale" },
    { value: "C", label: "C - Distributor" },
    { value: "D", label: "D - Volume" },
    { value: "E", label: "E - Special" },
  ];
  return (
    <div className="max-w-7xl mx-auto">
      {renderPrintPreview()}

      {/* FormCoach — Data-completeness warnings (shown after print check) */}
      {formCoach.hasChecked && formCoach.hasIssues && (
        <div className="mb-4">
          <FormCoachAlert
            issues={formCoach.issues}
            onDismiss={formCoach.clearIssues}
            formSourcePath={FORM_SOURCE_PATHS[transactionType]}
          />
        </div>
      )}

      <div className="flex items-center justify-between mb-0">
        {/* Edit Button (when not editing) */}
        {!isEditing && canEdit(data) && (
          <>
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate(-1)}
                className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              >
                <FaArrowLeft />
              </button>
            </div>
            <div className="flex items-center gap-2">
              {data?.id && (
                <button
                  onClick={handlePrint}
                  className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 border border-slate-300 dark:border-slate-600 hover:border-slate-400 dark:hover:border-slate-500 rounded-lg transition-colors flex items-center gap-2"
                  title="Print Preview"
                >
                  <FaPrint size={14} />
                  Print
                </button>
              )}
              <button
                onClick={handleEdit}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center gap-2"
              >
                <FaEdit size={14} />
                Edit
              </button>
            </div>
          </>
        )}

        {/* Unsaved Changes Indicator */}
        {hasUnsavedChanges && (
          <span className="px-3 py-1 text-xs font-medium text-amber-700 dark:text-amber-300 bg-amber-100 dark:bg-amber-900/30 rounded-full">
            Unsaved changes
          </span>
        )}
      </div>
      {/* Transaction Toolbar (when editing) - Sticky */}
      {isEditing && (
        <div className="sticky top-0 z-20 -mx-4 px-4 py-0 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm border-b border-slate-200 dark:border-slate-700 mb-6 flex items-center gap-2">
          <TransactionToolbar
            transactionType={transactionType as TransactionType}
            transactionId={data?.id}
            isDirty={isDirty}
            isSaving={saving}
            isEditing={isEditing}
            onSave={handleSave}
            onSaveAndClose={handleSaveAndClose}
            onClone={canClone ? handleClone : undefined}
            onTransfer={canTransfer ? handleTransfer : undefined}
            onPrint={handlePrint}
            onEmail={handleEmail}
            onDelete={canDelete ? handleDelete : undefined}
            onCancel={handleCancel}
            canDelete={canDelete}
            canClone={canClone}
            canTransfer={canTransfer}
            onAddTask={onAddTask}
            showTaskButton={showTaskButton}
            taskCount={taskCount}
          />
          {/* Assign Org Button */}
          <button
            type="button"
            className="ml-2 px-3 py-1 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
            onClick={handleAssignOrgClick}
            title="Assign Organization (Customer/Vendor)"
          >
            Assign Org
          </button>
          {/* OrgSearchDialog Modal */}
          <OrgSearchDialog
            open={showOrgDialog}
            orgType={orgDialogType}
            allowTypeSwitch={true}
            onSelect={handleOrgSelected}
            onClose={() => setShowOrgDialog(false)}
            title={`Assign ${
              orgDialogType.charAt(0).toUpperCase() + orgDialogType.slice(1)
            }`}
          />
        </div>
      )}
      {/* QQQ Summary and Lines item  */}
      <div className="flex items-center justify-between mb-0">
        <DevBadge
          label={`${transactionType}Detail`}
          className="absolute top-1 left-1 z-10"
        />
        {renderHeader ? (
          renderHeader(
            currentDataWithTotals as Transaction,
            isEditing,
            handleFieldChange,
          )
        ) : currentData ? (
          <SummaryCard
            data={currentDataWithTotals}
            isEditing={isEditing}
            onChange={handleFieldChange}
            priceLable={priceLable}
            customerInfo={currentData.refs?.links?.customer?.[0]}
            billingContact={currentData.refs?.links?.contact?.find(
              (c) => c.purpose === "billto",
            )}
            shippingContact={currentData.refs?.links?.contact?.find(
              (c) => c.purpose === "shipto",
            )}
            // orgLinks omitted due to type mismatch
          />
        ) : null}
      </div>

      {renderLines ? (
        renderLines(
          currentData?.lines ?? [],
          isEditing,
          currentData || undefined,
          onLinesChange,
        )
      ) : currentData ? (
        <LinesCard
          lines={currentData.lines ?? []}
          isEditing={isEditing}
          isLocked={data?.is_locked}
          transactionType={transactionType}
          onDeleteLine={(lineId) => {
            if (typeof onLinesChange === "function") {
              onLinesChange(
                (currentData.lines ?? []).filter(
                  (l, i) => lineKey(l, i) !== lineId,
                ),
              );
            }
          }}
          onUpdateLine={(lineId, field, value) => {
            if (typeof onLinesChange === "function") {
              onLinesChange(
                (currentData.lines ?? []).map((l, i) => {
                  if (lineKey(l, i) !== lineId) return l;
                  const baseUpdate = { ...l, _dirty: true };
                  const lineIsActive = l.item?.is_active !== false;
                  switch (field) {
                    case "qty": {
                      const newQty = Number(value);
                      if (!lineIsActive) {
                        // Inactive line: persist active but don't recalculate
                        return {
                          ...baseUpdate,
                          quantity: {
                            ...l.quantity,
                            active: newQty,
                            staged: newQty,
                          },
                        };
                      }
                      // User always edits active; staged mirrors for standalone
                      // All types: remaining = staged (standalone)
                      const unitPriceForCalc = l.price?.unit ?? 0;
                      return {
                        ...baseUpdate,
                        quantity: {
                          ...l.quantity,
                          active: newQty,
                          staged: newQty,
                          remaining: newQty,
                        },
                        price: {
                          ...l.price,
                          extended: unitPriceForCalc * newQty,
                        },
                      };
                    }
                    case "description":
                      return {
                        ...baseUpdate,
                        item: { ...l.item, description: String(value) },
                      };
                    case "unit_price": {
                      const newPrice = Number(value);
                      const qty = l.quantity?.staged ?? 0;
                      return {
                        ...baseUpdate,
                        price: {
                          ...l.price,
                          unit: newPrice,
                          extended: lineIsActive
                            ? newPrice * qty
                            : l.price?.extended ?? 0,
                        },
                      };
                    }
                    default:
                      return { ...baseUpdate, [field]: value };
                  }
                }),
              );
            }
          }}
          onDuplicateLine={(lineId) => {
            if (typeof onLinesChange === "function") {
              const lineToDup = (currentData.lines ?? []).find(
                (l, i) => lineKey(l, i) === lineId,
              );
              if (lineToDup) {
                const { id, ...rest } = lineToDup;
                const newLine: TransactionLine = {
                  ...rest,
                  id: Date.now(),
                  line_number: getNextLineNumber(currentData.lines ?? []),
                };
                onLinesChange([...(currentData.lines ?? []), newLine]);
              }
            }
          }}
          onLinesChange={onLinesChange}
          onAddItem={handleAddItem}
        />
      ) : null}
      {/* ── Scalar & JSONB cards (view mode) ───────────────────── */}
      {!isEditing && currentData && (
        <div className="space-y-4 px-4 py-2">
          <ScalarCard
            title="Transaction Details"
            fields={[
              { label: "status", value: currentData.status },
              { label: "priority", value: currentData.priority },
              { label: "price_level", value: currentData.price_level },
              { label: "terms", value: currentData.terms },
              { label: "total", value: currentData.total, format: "currency" },
              {
                label: "balance",
                value: currentData.balance,
                format: "currency",
              },
              { label: "line_increment", value: currentData.line_increment },
              { label: "customer_id", value: currentData.customer_id },
              { label: "vendor_id", value: currentData.vendor_id },
              { label: "manufacturer_id", value: currentData.manufacturer_id },
              { label: "contact_id", value: currentData.contact_id },
              { label: "parent_id", value: currentData.parent_id },
              { label: "parent_model", value: currentData.parent_model },
              { label: "attention", value: currentData.attention },
              { label: "address_full", value: currentData.address_full },
              { label: "email", value: currentData.email },
              { label: "phone", value: currentData.phone },
              { label: "conditions_id", value: currentData.conditions_id },
              {
                label: "conditions_description",
                value: currentData.conditions_description,
              },
            ]}
            columns={3}
          />
          <JsonCard
            title="Totals"
            fieldName="totals"
            data={currentData.totals as Record<string, unknown>}
            columns={3}
          />
          <JsonCard
            title="Cost"
            fieldName="cost"
            data={currentData.cost as Record<string, unknown>}
            columns={2}
          />
          <JsonCard
            title="Sell"
            fieldName="sell"
            data={currentData.sell as Record<string, unknown>}
            columns={2}
          />
          <JsonCard
            title="Finance"
            fieldName="finance"
            data={currentData.finance as Record<string, unknown>}
            columns={2}
          />
          <JsonCard
            title="Flow"
            fieldName="flow"
            data={currentData.flow as Record<string, unknown>}
            columns={2}
          />
          <JsonCard
            title="Source"
            fieldName="source"
            data={currentData.source as Record<string, unknown>}
            columns={2}
          />
          <JsonCard
            title="Actions"
            fieldName="actions"
            data={currentData.actions as Record<string, unknown>}
            columns={2}
          />
          <BaseModelCards data={currentData} />
        </div>
      )}
      {/* Tabs Navbar */}
      <div className="border-b border-slate-200 dark:border-slate-700 mb-2">
        <nav className="flex gap-1 overflow-x-auto">
          {tabs
            .filter((tab) => !tab.adminOnly || isAdmin)
            .map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-2 px-2 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
                  ${
                    activeTab === tab.id
                      ? "border-blue-500 text-blue-600 dark:text-blue-400"
                      : "border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 hover:border-slate-300 dark:hover:border-slate-600"
                  }
                `}
              >
                {tab.icon}
                {tab.label}
                {typeof tab.badge === "number" && tab.badge > 0 && (
                  <span className="px-1.5 py-0.5 text-xs bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-full">
                    {tab.badge}
                  </span>
                )}
              </button>
            ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="pb-8 overflow-y-scroll max-h-100">
        {renderTabContent()}
      </div>

      {/* RelatedTransactions - show only parent/child transactions linked to this record.
          Only render for saved records with parent_id or flow.children defined. */}
      {(() => {
        // Skip for new / unsaved records — no related transactions to show
        const recordId = currentData?.id;
        if (effectiveMode === "add" || !recordId) return null;

        // Only render if transaction has parent or children
        const hasParent = currentData?.parent_id && currentData?.parent_model;
        const hasChildren = currentData?.flow?.children?.some(
          (c: { type?: string; id?: number }) => c?.type && c?.id && c.id > 0,
        );
        if (!hasParent && !hasChildren) return null;

        return (
          <div className="mt-4">
            <RelatedTransactions
              transaction={{
                id: recordId,
                ida: currentData?.ida,
                name: currentData?.name,
                status: currentData?.status,
                total: currentData?.totals?.total,
                currency: currentData?.currency,
                dt_created: currentData?.dt_created,
                parent_id: currentData?.parent_id,
                parent_model: currentData?.parent_model,
                flow: currentData?.flow,
              }}
            />
          </div>
        );
      })()}

      {/* Unsaved Changes Dialog - Action blocking (print, etc.) */}
      <UnsavedChangesDialog
        isOpen={isActionPending}
        type="action"
        actionName={pendingAction?.name}
        onConfirm={confirmAction}
        onCancel={cancelAction}
        onSaveFirst={async () => {
          await handleSave();
        }}
        isSaving={saving}
      />
    </div>
  );
};

export default withDevIdentifier(
  TransactionDetailBase,
  "TransactionDetailBase",
);
