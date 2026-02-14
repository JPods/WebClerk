import QATab from "./QATab";
import { normalizeRefsLinksContact } from "./ContactPanel";
/**
 * TransactionDetail - Base component for all transaction detail pages
 * Provides common tabbed layout with standard sections
 * Extended by InvoiceDetail, OrderDetail, etc.
 */
import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import { useAppSelector } from "../../../store/hooks";
import { useWindowPath } from "@/context/WindowPathContext";
import {
  FaArrowLeft,
  FaEdit,
  FaAddressCard,
  FaComments,
  FaDollarSign,
  FaLink,
  FaEllipsisH,
  FaTasks,
  FaSlidersH,
  FaQuestionCircle,
  FaFileAlt,
} from "react-icons/fa";
import { showToast } from "../../../store/slices/toastSlice";

// Import API functions
import {
  getRecord,
  saveRecord,
  saveTransactionWithLines,
  deleteRecord,
} from "../../../api/wcapi";

// Import toolbar
import TransactionToolbar, { type TransactionType } from "./TransactionToolbar";

// Import shared components
import ContactPanel from "./ContactPanel";
import ContactLinksTable from "./ContactLinksTable";
import CommentsPanel from "./CommentsPanel";
import MetadataPanel from "./MetadataPanel";
import FinancialsCard from "./FinancialsCard";

import { DocumentsPanel, PrefsPanel } from "@/apps/common/components/panels";

import JsonFieldEditor from "./JsonFieldEditor";

// Import types
import type {
  Transaction as TransactionBase,
  TransactionLine,
} from "../types/transactionTypes";
import SummaryCard from "./SummaryCard";
import LinesCard from "./LinesCard";

// Extend Transaction type locally to ensure 'lines' exists
type Transaction = TransactionBase & {
  lines?: TransactionLine[];
  currency?: string; // Add currency property
  number?: string | number; // Add number property to fix compile error
  dt?: string; // Transaction date
  due_date?: string; // Due date
};

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

  /** Callback for cancel action in inline mode */

  /** Callback for Add Task action */
  onAddTask?: () => void;
  /** Whether to show Add Task button */
  showTaskButton?: boolean;
  /** Number of pending tasks (for badge) */
  taskCount?: number;
}

const TransactionDetailBase: React.FC<TransactionDetailBaseProps> = ({
  transactionType,
  typeLabel,
  modelName,
  customTabsBefore = [],
  customTabsAfter = [],
  getCustomTabsAfter,
  renderCustomTab,
  renderHeader,
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
  onAddTask,
  showTaskButton = false,
  taskCount,
}) => {
  // Default no-op for handleAddItem to avoid reference error
  const handleAddItem = () => {};
  const { id: urlId } = useParams<{ id: string }>();
  // Use idProp first, then dataProp ID, then URL param
  const id = idProp?.toString() ?? dataProp?.id?.toString() ?? urlId;
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { user } = useAppSelector((state) => state.auth);
  const displayName = user ? `${user.name_first}${user.name_last}` : "You";

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

  // Determine effective mode: if no ID is available and modeProp isn't set,
  // treat as "add" mode (e.g. opened from Create Transaction dropdown)
  const effectiveMode = useMemo(() => {
    if (modeProp) return modeProp;
    if (!id) return "add" as const;
    return null;
  }, [modeProp, id]);

  // State
  const [data, setData] = useState<Transaction | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Start in edit mode if modeProp is 'add' or 'edit'
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

  // Debug log the props
  console.log("[TransactionDetailBase] Props:", {
    modeProp,
    inline,
    hasDataProp: !!dataProp,
  });

  // Handle "add" mode - create empty record
  useEffect(() => {
    if (effectiveMode !== "add") return;
      // Get today's date at midnight (zero time)
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const todayIso = today.toISOString();

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
        links.customer = [{
          id: Number(qsCustomerId),
          display_name: qsCustomerName || "",
        }];
      }
      if (qsContactId) {
        links.contact = [{
          id: Number(qsContactId),
          purpose: "billto",
          display_name: qsAttention || "",
          email: qsEmail || "",
          phone: qsPhone || "",
        }];
      } else if (qsAttention || qsEmail || qsPhone) {
        links.contact = [{
          id: 0,
          purpose: "billto",
          display_name: qsAttention || "",
          email: qsEmail || "",
          phone: qsPhone || "",
        }];
      }

      const emptyRecord: Transaction = {
        id: 0,
        customer_id: qsCustomerId ? Number(qsCustomerId) : 0,
        vendor_id: 0,
        manufacturer_id: 0,
        status: "planned",
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
        // Initialize all date fields to today at midnight
        dt: todayIso,
        due_date: todayIso,
      };
      setData(emptyRecord);
      setEditData(emptyRecord);
      setIsEditing(true);
      setLoading(false);
  }, [effectiveMode, windowSearchParams]);

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

  // Warn before leaving with unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = "";
        return "";
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [hasUnsavedChanges]);

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
      setData(dataProp);
      setEditData(dataProp);
      setLoading(false);
      setInitialDataPropUsed(true);
      return;
    }

    // For refreshKey > 0 (after save), always fetch fresh data from API
    const loadData = async () => {
      if (!id) return;

      setLoading(true);
      setError(null);
      console.log(
        "[TransactionDetailBase] Fetching data from API, refreshKey:",
        refreshKey,
      );

      try {
        let result: Transaction;

        if (fetchData) {
          result = await fetchData(id);
        } else {
          // Use wcapi getRecord which includes auth headers and proper error handling
          const apiResult = await getRecord(modelName, Number(id));
          result = apiResult.record ?? apiResult;
        }

        console.log(
          "[TransactionDetailBase] Fresh data loaded:",
          result?.refs?.links?.contact,
        );
        setData(result);
        setEditData(result);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load data");
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
    const actions = data?.actions?.items as Array<{ status?: string }> | undefined;
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
    console.log("[TransactionDetailBase] handleEdit called", {
      data,
      canEditResult: data ? canEdit(data) : "no data",
    });
    if (data && canEdit(data)) {
      // Always initialize editData with the latest data (including comments)
      setEditData({ ...data });
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
      return await saveData(editData);
    }

    // Ensure id is included in payload for updates
    const payloadWithId = {
      ...editData,
      id: data?.id,
    };

    // Use transaction-specific save if data has lines, otherwise standard save
    const hasLines = Array.isArray(editData.lines) && editData.lines.length > 0;

    const apiResult = hasLines
      ? await saveTransactionWithLines(modelName, payloadWithId)
      : await saveRecord(modelName, payloadWithId);

    return apiResult.record ?? apiResult;
  }, [editData, saveData, modelName, data?.id]);

  const handleSave = useCallback(async () => {
    if (!editData) return;

    setSaving(true);
    dispatch(showToast({ message: "Saving...", type: "info" }));
    try {
      const result = await performSave();
      if (!result) return;

      setData(result); // Update view state
      setEditData(result); // Update edit state
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
      const errorMsg = e instanceof Error ? e.message : "Failed to save";
      setError(errorMsg);
      dispatch(showToast({ message: errorMsg, type: "error" }));
    } finally {
      setSaving(false);
    }
  }, [editData, performSave, onSaved, dispatch, typeLabel]);

  // Toolbar handlers
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
      navigate(-1);
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : "Failed to save";
      setError(errorMsg);
      dispatch(showToast({ message: errorMsg, type: "error" }));
    } finally {
      setSaving(false);
    }
  }, [editData, performSave, navigate, onSaved, dispatch, typeLabel]);

  const handleClone = useCallback(async () => {
    if (!data) return;
    dispatch(showToast({ message: `Cloning ${typeLabel}...`, type: "info" }));
    // Navigate to new page with cloned data (without id/ida)
    const clonedData = { ...data };
    delete (clonedData as Record<string, unknown>).id;
    delete (clonedData as Record<string, unknown>).ida;
    navigate(`/transactions/${transactionType}s/new`, {
      state: { clone: clonedData, mode: "add" },
    });
  }, [data, transactionType, navigate, dispatch, typeLabel]);

  const handleTransfer = useCallback(
    async (targetType: TransactionType) => {
      if (!data) return;
      dispatch(
        showToast({
          message: `Transferring to ${targetType}...`,
          type: "info",
        }),
      );
      // Navigate to new transaction of target type with lines from this one
      navigate(`/transactions/${targetType}s/new`, {
        state: {
          transferFrom: {
            type: transactionType,
            id: data.id,
            lines: (data as unknown as Record<string, unknown>).lines,
            customer_id: data.customer_id,
            refs: data.refs,
          },
          mode: "add",
        },
      });
    },
    [data, transactionType, navigate, dispatch],
  );

  const handlePrint = useCallback(() => {
    if (onPrint && data) {
      onPrint(data);
    } else {
      dispatch(showToast({ message: "Opening print dialog...", type: "info" }));
      window.print();
    }
  }, [onPrint, data, dispatch]);

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
      const errorMsg = e instanceof Error ? e.message : "Failed to delete";
      setError(errorMsg);
      dispatch(showToast({ message: errorMsg, type: "error" }));
    }
  }, [data, modelName, transactionType, navigate, dispatch, typeLabel]);

  // Check if form has changed
  const isDirty = useMemo(() => {
    if (!data || !editData) return false;
    const dirty = JSON.stringify(data) !== JSON.stringify(editData);
    console.log("[TransactionDetailBase] isDirty computed", {
      isDirty: dirty,
      dataId: data?.id,
      editDataId: editData?.id,
    });
    return dirty;
  }, [data, editData]);

  // Handle field changes during edit
  const handleFieldChange = (field: string, value: unknown) => {
    console.log("[TransactionDetailBase] handleFieldChange START", {
      field,
      value,
      hasEditData: !!editData,
      currentEditDataId: editData?.id,
    });
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
        console.log("[TransactionDetailBase] Comments field updated", {
          oldComments: editData.comments,
          newComments: newData.comments,
        });
      } else {
        newData = { ...editData, [field]: value } as Transaction;
      }
      console.log("[TransactionDetailBase] Setting new editData");
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

  const currentData = isEditing && editData ? editData : data;
  console.log("[TransactionDetailBase] render:", {
    isEditing,
    hasEditData: !!editData,
    hasData: !!data,
    usingEditData: isEditing && editData,
  });

  // Handler for updating lines array in editData
  const onLinesChange = (newLines: TransactionLine[]) => {
    if (isEditing && editData) {
      setEditData({ ...editData, lines: newLines });
      setHasUnsavedChanges(true);
    }
  };

  // Render tab content
  const renderTabContent = () => {
    // Check for custom tab first
    if (renderCustomTab) {
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
        const actions = (currentData.actions?.items ?? []) as Array<{
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
                        className={`px-2 py-1 text-xs rounded-full ${getStatusClass(action.status)}`}
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
        console.log("currentData", currentData);
        // Use normalization helper to parse contacts from API
        return (
          <ContactPanel
            contacts={normalizeRefsLinksContact(
              currentData.refs?.links?.contact ?? [],
            )}
            isEditing={isEditing}
            parent_model={modelName}
            parentId={currentData?.id}
            customer_id={currentData?.customer_id || currentData?.refs?.links?.customer?.[0]?.id}
            customer_name={currentData?.refs?.links?.customer?.[0]?.display_name}
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

        return (
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
        );

      case "financials":
        return (
          <FinancialsCard
            totals={currentData.totals}
            cost={currentData.cost}
            sell={currentData.sell}
            currency={currentData.currency}
            isEditing={isEditing}
          />
        );

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
            <button
              onClick={handleEdit}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center gap-2"
            >
              <FaEdit size={14} />
              Edit
            </button>
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
        <div className="sticky top-0 z-20 -mx-4 px-4 py-0 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm border-b border-slate-200 dark:border-slate-700 mb-6">
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
        </div>
      )}
      {/* QQQ Summary and Lines item  */}
      <div className="flex items-center justify-between mb-0">
        <span className="absolute top-1 left-1 z-10 px-1.5 py-0.5 text-[10px] font-mono font-normal tracking-wide uppercase bg-indigo-100 text-indigo-600 dark:bg-indigo-900/40 dark:text-indigo-300 rounded">{transactionType}Detail</span>
        {renderHeader ? (
          renderHeader(currentData, isEditing, handleFieldChange)
        ) : (
          <SummaryCard
            data={currentData}
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
          />
        )}
      </div>

      <LinesCard
        lines={currentData.lines ?? []}
        isEditing={isEditing}
        isLocked={data?.is_locked}
        onDeleteLine={(lineId) => {
          if (typeof onLinesChange === "function") {
            onLinesChange(
              (currentData.lines ?? []).filter((l) => l.id !== lineId),
            );
          }
        }}
        onUpdateLine={(lineId, field, value) => {
          if (typeof onLinesChange === "function") {
            onLinesChange(
              (currentData.lines ?? []).map((l) => {
                if (l.id !== lineId) return l;
                const baseUpdate = { ...l, _dirty: true };
                switch (field) {
                  case "qty":
                    return {
                      ...baseUpdate,
                      quantity: { ...l.quantity, ordered: Number(value) },
                    };
                  case "description":
                    return {
                      ...baseUpdate,
                      item: { ...l.item, description: String(value) },
                    };
                  case "unit_price":
                    const newPrice = Number(value);
                    const qty = l.quantity?.ordered ?? 0;
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
          if (typeof onLinesChange === "function") {
            const lineToDup = (currentData.lines ?? []).find(
              (l) => l.id === lineId,
            );
            if (lineToDup) {
              const { id, ...rest } = lineToDup;
              const newLine: TransactionLine = {
                ...rest,
                id: Date.now(),
              };
              onLinesChange([...(currentData.lines ?? []), newLine]);
            }
          }
        }}
        onLinesChange={onLinesChange}
        onAddItem={handleAddItem}
      />
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
      <div className="pb-8 overflow-y-scroll max-h-[400px]">
        {renderTabContent()}
      </div>
    </div>
  );
};

export default TransactionDetailBase;
