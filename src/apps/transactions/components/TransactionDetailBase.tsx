import QATab from "./QATab";
import DocumentsTab from "./DocumentsTab";
/**
 * TransactionDetail - Base component for all transaction detail pages
 * Provides common tabbed layout with standard sections
 * Extended by InvoiceDetail, OrderDetail, etc.
 */
import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import {
  FaArrowLeft,
  FaEdit,
  FaAddressCard,
  FaComments,
  FaDollarSign,
  FaLink,
  FaCog,
  FaHistory,
  FaEllipsisH,
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
import RefsLinksContactPanel from "./RefsLinksContactPanel";
import ContactLinksTable from "./ContactLinksTable";
import CommentsPanel from "./CommentsPanel";
import MetadataPanel from "./MetadataPanel";
import FinancialsCard from "./FinancialsCard";

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

  /** Callback for cancel action in inline mode */
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
}) => {
  // Default no-op for handleAddItem to avoid reference error
  const handleAddItem = () => {};
  const { id: urlId } = useParams<{ id: string }>();
  // Use dataProp ID if provided, otherwise fall back to URL param
  const id = dataProp?.id?.toString() ?? urlId;
  const navigate = useNavigate();
  const dispatch = useDispatch();

  // State
  const [data, setData] = useState<Transaction | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Start in edit mode if modeProp is 'add' or 'edit'
  const [isEditing, setIsEditing] = useState(
    modeProp === "add" || modeProp === "edit",
  );
  const [editData, setEditData] = useState<Transaction | null>(null);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("summary");
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Debug log the props
  console.log("[TransactionDetailBase] Props:", {
    modeProp,
    inline,
    hasDataProp: !!dataProp,
  });

  // Handle "add" mode - create empty record
  useEffect(() => {
    if (modeProp === "add") {
      const emptyRecord: Transaction = {
        id: 0, // id should be a number
        customer_id: 0,
        vendor_id: 0,
        manufacturer_id: 0,
        status: "planned",
        lines: [],
        refs: { links: {} },
        metadata: {},
        comments: { notes: [] },
        totals: {},
        finance: {},
      };
      setData(emptyRecord);
      setEditData(emptyRecord);
      setIsEditing(true);
      setLoading(false);
    }
  }, [modeProp]);

  // Update isEditing when modeProp changes (for inline usage)
  useEffect(() => {
    if (modeProp === "edit") {
      setIsEditing(true);
    } else if (modeProp === "view") {
      setIsEditing(false);
    }
  }, [modeProp]);

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
  useEffect(() => {
    // Skip fetch for "add" mode - handled by the add mode effect
    if (modeProp === "add") {
      return;
    }

    // If dataProp is provided, use it directly instead of fetching
    if (dataProp) {
      setData(dataProp);
      setEditData(dataProp);
      setLoading(false);
      return;
    }

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

        setData(result);
        setEditData(result);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [id, modelName, typeLabel, fetchData, dataProp, modeProp]);

  // Build tabs list - use stable reference for badge count
  const contactCount = data?.refs?.links?.contact?.length ?? 0;
  const lineCount = (data as unknown as Record<string, unknown>)?.lines
    ? ((data as unknown as Record<string, unknown>).lines as unknown[]).length
    : 0;
  const commentCount = data?.comments?.notes?.length ?? 0;

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
        id: "contacts",
        label: "Contacts",
        icon: <FaAddressCard size={14} />,
        badge: contactCount || undefined,
      },
      {
        id: "comments",
        label: "Comments",
        icon: <FaComments size={14} />,
        badge: commentCount || undefined,
      },
      {
        id: "financials",
        label: "Financials",
        icon: <FaDollarSign size={14} />,
      },
      { id: "documents", label: "Documents", icon: <FaLink size={14} /> },
      { id: "qa", label: "QA", icon: <FaComments size={14} /> },
      // { id: "flow", label: "Flow", icon: <FaLink size={14} /> },
    ];

    if (isAdmin) {
      defaultTabs.push(
        {
          id: "metadata",
          label: "Metadata",
          icon: <FaCog size={14} />,
          adminOnly: true,
        },
        {
          id: "refs",
          label: "Refs",
          icon: <FaHistory size={14} />,
          adminOnly: true,
        },
        {
          id: "raw",
          label: "Raw JSON",
          icon: <FaEllipsisH size={14} />,
          adminOnly: true,
        },
      );
    }

    return [...customTabsBefore, ...defaultTabs, ...dynamicCustomTabsAfter];
  }, [
    customTabsBefore,
    dynamicCustomTabsAfter,
    contactCount,
    lineCount,
    commentCount,
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

  const handleSave = useCallback(async () => {
    if (!editData) return;

    setSaving(true);
    dispatch(showToast({ message: "Saving...", type: "info" }));
    try {
      let result: Transaction;

      if (saveData) {
        result = await saveData(editData);
      } else {
        // Use transaction-specific save if data has lines, otherwise standard save
        const hasLines =
          Array.isArray(editData.lines) && editData.lines.length > 0;
        // console.log(
        //   "[TransactionDetailBase.handleSave] hasLines:",
        //   hasLines,
        //   "lineCount:",
        //   editData.lines?.length,
        // );
        const apiResult = hasLines
          ? await saveTransactionWithLines(modelName, editData)
          : await saveRecord(modelName, editData);
        result = apiResult.record ?? apiResult;
      }

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
  }, [editData, saveData, modelName, onSaved, dispatch, typeLabel]);

  // Toolbar handlers
  const handleSaveAndClose = useCallback(async () => {
    if (!editData) return;

    setSaving(true);
    dispatch(showToast({ message: "Saving...", type: "info" }));
    try {
      let result: Transaction;

      if (saveData) {
        result = await saveData(editData);
      } else {
        // Use transaction-specific save if data has lines, otherwise standard save
        const hasLines =
          Array.isArray(editData.lines) && editData.lines.length > 0;

        const apiResult = hasLines
          ? await saveTransactionWithLines(modelName, {
              ...editData,
              id: data?.id,
            })
          : await saveRecord(modelName, {
              ...editData,
              id: data?.id,
            });

        result = apiResult.record ?? apiResult;
      }

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
  }, [editData, saveData, modelName, navigate, onSaved, dispatch, typeLabel]);

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
    return JSON.stringify(data) !== JSON.stringify(editData);
  }, [data, editData]);

  // Handle field changes during edit
  const handleFieldChange = (field: string, value: unknown) => {
    console.log("[TransactionDetailBase] handleFieldChange", {
      field,
      value,
      hasEditData: !!editData,
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
      case "contacts":
        return (
          <RefsLinksContactPanel
            contacts={(currentData.refs?.links?.contact ?? []).map(
              (c: any) => ({
                contact_id: c.contact_id ?? c.id,
                purpose: c.purpose,
                attention: c.attention,
                email: c.email,
                phone: c.phone,
                full: c.full,
                domain: c.domain,
                address_id: c.address_id,
                email_id: c.email_id,
                phone_id: c.phone_id,
                domain_id: c.domain_id,
              }),
            )}
            isEditing={isEditing}
          />
        );

      case "comments":
        // Always use editData.comments if editing, otherwise data.comments
        const commentsSource =
          isEditing && editData ? editData.comments : data?.comments;
        return (
          <CommentsPanel
            comments={commentsSource ?? {}}
            isEditing={isEditing}
            onChange={(val) => handleFieldChange("comments", val)}
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
        return <DocumentsTab />;

      case "qa":
        return <QATab />;

      case "metadata":
        return isAdmin ? (
          <MetadataPanel
            metadata={currentData.metadata}
            isEditing={isEditing}
            onChange={(val) => handleFieldChange("metadata", val)}
          />
        ) : null;

      case "refs":
        return isAdmin ? (
          <div className="space-y-6">
            {/* Contact Links Table - draggable columns, click ID/name to edit */}
            <ContactLinksTable
              refs={currentData.refs as Record<string, unknown> | null}
              title="refs.links.contact"
              showEmptyState={true}
              enableNavigation={true}
            />

            {/* Full refs JSON Editor */}
            <JsonFieldEditor
              label="refs"
              value={currentData.refs ?? {}}
              readonly={!isEditing}
              onChange={(val) => handleFieldChange("refs", val)}
            />
          </div>
        ) : null;

      case "raw":
        return isAdmin ? (
          <JsonFieldEditor
            label="Full Transaction JSON"
            value={currentData}
            readonly
            defaultExpanded
            maxHeight="600px"
          />
        ) : null;

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
          />
        </div>
      )}
      {/* QQQ Summary and Lines item  */}
      <div className="flex items-center justify-between mb-0">
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
