import { useCallback, useEffect, useMemo, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import Label from "../../../../../components/form/Label";
import { Input, Select } from "../../../../../components/wrapper";

import {
  createCustomer,
  updateCustomer,
  fetchCustomers,
  deleteCustomer,
} from "../services/customerApi";
import {
  getRecord,
  getRecords,
  logRefsMismatch,
  getContactOptions,
  getProjectOptions,
} from "@/api/wcapi";
import { createContact } from "@/apps/core/models/contact/services/contactApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import {
  FaChevronLeft,
  FaChevronRight,
  FaEdit,
  FaTrash,
  FaDollarSign,
  FaAddressCard,
  FaQuestionCircle,
  FaTimes,
  FaProductHunt,
  FaComment,
  FaTruckLoading,
} from "react-icons/fa";
import { customerSchema } from "../utils/customerSchema";
import {
  ScalarCard,
  JsonCard,
  BaseModelCards,
} from "@/apps/common/components/detail";
import { CustomerAddProps } from "../types/customerType";
import Checkbox from "@/components/form/input/Checkbox";
import { DevBadge } from "@/components/common/DevBadge";

import TransactionToolbar from "@/apps/common/components/TransactionToolbar";
import JsonFieldEditor from "@/apps/common/components/JsonFieldEditor";
import {
  BasicInformationPanel,
  CommentsPanel,
  ActionsPanel,
  DocumentsPanel,
  MetadataPanel,
  RawDataPanel,
  ContactPanel,
  normalizeRefsLinksContact,
  QAPanel,
  RefsPanel,
  PrefsPanel,
} from "@/apps/common/components/panels";
import TransactionTabs from "@/components/common/TransactionTabs";
import ItemTabs from "@/components/common/ItemTabs";
import OrgFinancialsPanel from "@/apps/orgs/components/OrgFinancialsPanel";
import {
  DetailTabs,
  useDetailTabs,
  useColumnCount,
  ColumnSelector,
} from "@/components/common/DetailTabs";
import { useAppSelector } from "@/store/hooks";
import { useWindowManager } from "../../../../../context/WindowManagerContext";
import { PageRoutes } from "../../../../../routes/Routes";
import { dynamicData } from "../../../../../model/dynamicData";
import RippleLoader from "@/components/common/RippleLoader";
import { CreateContactRequest } from "../../../../core/models/contact/types/contactType";
import { withDevIdentifier } from "@/components/common/DevIdentifier";
import InternationalPhoneInput from "@/components/form/input/InternationalPhoneInput";

// Professional customer display component for right-side column
type CustomerFormValues = z.infer<typeof customerSchema> & {
  refs?: string;
};

interface Customer {
  id?: number;
  display_name?: string;
  status?: string;
  org_type?: string;
  version?: number;
  is_active?: boolean;
  // New scalar fields from wc3
  attention?: string | null;
  contact_id?: number | null;
  email?: string | null;
  phone?: string | null;
  price_level?: string | null;
  terms?: string | null;
  terms_id?: number | null;
  address_full?: string | null;
  // JSON aspect fields
  contacts?: any;
  addresses?: any;
  domains?: any;
  phones?: any;
  emails?: any;
  docs?: any;
  connections?: any;
  relations?: any;
  financial?: any;
  data?: any;
  metrics?: any;
  gl_accounts?: any;
  refs?: any; // <-- Add refs property
}

const JSON_DEFAULTS: Record<string, any> = {
  contacts: [],
  addresses: [],
  domains: [],
  phones: [],
  emails: [],
  docs: [],
  connections: {},
  relations: { parents: [], children: [], linked_ids: [] },
  financial: {
    credit: { limit: 0, used: 0 },
    balances: { open: 0, current: 0 },
    metrics: { ytd: { sales: 0 } },
  },
  data: {},
  metrics: { counts: {}, periods: {} },
  gl_accounts: {},
};

const STATUS_OPTIONS = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "pending", label: "Pending" },
  { value: "suspended", label: "Suspended" },
  { value: "archived", label: "Archived" },
];

const ORG_TYPE_OPTIONS = [
  { value: "customer", label: "Customer" },
  { value: "vendor", label: "Vendor" },
  { value: "partner", label: "Partner" },
  { value: "internal", label: "Internal" },
];

const TERMS_OPTIONS = [
  { value: "Net 30", label: "Net 30" },
  { value: "Net 60", label: "Net 60" },
  { value: "Net 90", label: "Net 90" },
  { value: "Due on Receipt", label: "Due on Receipt" },
  { value: "COD", label: "COD" },
  { value: "Prepaid", label: "Prepaid" },
  { value: "2/10 Net 30", label: "2/10 Net 30" },
];

const PRICE_LEVEL_OPTIONS = [
  { value: "A", label: "A - Retail" },
  { value: "B", label: "B - Wholesale" },
  { value: "C", label: "C - Distributor" },
  { value: "D", label: "D - Volume" },
  { value: "E", label: "E - Special" },
];

/* ----------------------------------
   Horizontal Field Row Component
   Label on left, input on right (Enterprise standard)
   Compact version for 2-column grid layout
---------------------------------- */
interface HorizontalFieldProps {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
  error?: string;
  required?: boolean;
}

function HorizontalField({
  label,
  htmlFor,
  children,
  error,
  required,
}: HorizontalFieldProps) {
  return (
    <div className="flex items-center gap-1.5 py-1">
      <Label
        htmlFor={htmlFor}
        className="w-25 shrink-0 text-left text-xs font-medium text-slate-600 dark:text-slate-400"
      >
        {label} :{required && <span className="text-red-500 ml-0.5">*</span>}
      </Label>
      <div className="flex-1 min-w-0">
        {children}
        {error && <p className="mt-0.5 text-[10px] text-red-500">{error}</p>}
      </div>
    </div>
  );
}

interface SingleWindowSectionProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

function SingleWindowSection({
  title,
  children,
  className = "",
}: SingleWindowSectionProps) {
  return (
    <section
      className={`rounded-sm border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 ${className}`}
    >
      <div className="px-2 py-1 text-[10px] font-semibold tracking-wide uppercase text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 border-b border-slate-300 dark:border-slate-700">
        {title}
      </div>
      <div className="p-2">{children}</div>
    </section>
  );
}

const VALID_TABS = [
  "actions",
  "comments",
  "contacts",
  "documents",
  "financial",
  "history",
  "metadata",
  "prefs",
  "qa",
  "raw",
  "refs",
];

export const CUSTOMER_STANDARD_TABS = [
  "actions",
  "comments",
  "documents",
  "raw",
];

export const CUSTOMER_ADDITIONAL_TABS = [
  { id: "contacts", label: "Contacts", icon: <FaAddressCard size={14} /> },
  { id: "qa", label: "Q&A", icon: <FaQuestionCircle size={14} /> },
];

export const FINANCE_STANDARD_TABS: string[] = ["transactions"];

export const FINANCE_ADDITIONAL_TABS = [
  {
    id: "transactions",
    label: "Transactions",
    icon: <FaDollarSign size={14} />,
  },
];

const VALID_FINANCE_TABS = ["transactions"];

export const ITEMS_STANDARD_TABS: string[] = [];

export const ITEMS_ADDITIONAL_TABS = [
  {
    id: "products",
    label: "Products",
    icon: <FaTruckLoading size={14} />,
  },
];

const VALID_ITEMS_TABS = ["products"];

export const buildCustomerTabBadges = (
  data: any,
  fkContacts: Array<unknown>,
): Record<string, number> => {
  const getCommentCount = () => {
    if (!data?.comments) return 0;
    const c = data.comments;
    return (
      (c.public?.length || 0) +
      (c.process?.length || 0) +
      (c.partner?.length || 0) +
      (c.notes?.length || 0)
    );
  };

  const getActionCount = () =>
    data?.actions?.items?.filter((a: any) => a.status === "pending").length ||
    0;

  const getDocumentCount = () => data?.refs?.links?.document?.length || 0;

  return {
    comments: getCommentCount(),
    actions: getActionCount(),
    documents: getDocumentCount(),
    contacts: fkContacts.length,
  };
};

function CustomerDetail({
  modeProp,
  dataProp,
  hideBreadcrumb: _hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
  onCancel: onCancelProp,
  onDelete: onDeleteProp,
}: CustomerAddProps) {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { ensureWindow, activateWindow, closeWindow } = useWindowManager();
  const currentUser = useAppSelector((state) => state.auth.user);
  //console.log("currentUser", currentUser);
  const { activeTab, setActiveTab: handleTabChange } = useDetailTabs(
    "customer",
    "actions",
    VALID_TABS,
  );
  const { activeTab: financeActiveTab, setActiveTab: handleFinanceTabChange } =
    useDetailTabs("customer-finance", "transactions", VALID_FINANCE_TABS);
  const { activeTab: itemsActiveTab, setActiveTab: handleItemsTabChange } =
    useDetailTabs("customer-items", "products", VALID_ITEMS_TABS);
  const { columnCount, setColumnCount: handleColumnChange } = useColumnCount(
    "customer",
    3,
  );
  const [isEditing, setIsEditing] = useState(false);

  // Data fetching state (used when no dataProp provided)
  const [fetchedRecord, setFetchedRecord] = useState<dynamicData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // FK-based contact loading (replaces refs.links.contact)
  const [fkContacts, setFkContacts] = useState<
    ReturnType<typeof normalizeRefsLinksContact>
  >([]);
  const [fkContactsLoading, setFkContactsLoading] = useState(false);
  const [fkRefreshTrigger, setFkRefreshTrigger] = useState(0);

  // Action dropdown options (assignees + projects)
  const [contactOptions, setContactOptions] = useState<
    Array<{ id: string; label: string }>
  >([]);
  const [projectOptions, setProjectOptions] = useState<
    Array<{ id: string; name?: string; intent?: string }>
  >([]);

  // Detect mode from route if modeProp not provided
  const routeMode = useMemo(() => {
    const path = location.pathname;
    if (path.includes("/customer/add")) return "add";
    if (path.includes("/customer/edit/")) return "edit";
    if (path.includes("/customer/detail/")) return "view";
    return "view";
  }, [location.pathname]);

  const customerId = Number(id);

  // Resolved customer ID — useParams may be empty in floating windows,
  // so fall back to the record's own id from dataProp or fetchedRecord.
  const resolvedCustomerId = useMemo(() => {
    if (Number.isFinite(customerId) && customerId > 0) return customerId;
    const fromData = dataProp?.id ?? fetchedRecord?.id;
    return fromData ? Number(fromData) : 0;
  }, [customerId, dataProp, fetchedRecord]);

  // Fetch data when in view/edit mode and no dataProp provided
  useEffect(() => {
    if (dataProp) return; // Skip if data provided via props
    // Respect explicit modeProp (inline add) as well as route-derived mode
    if (modeProp === "add" || routeMode === "add") return; // No fetch needed for add mode
    if (!Number.isFinite(customerId)) return;

    setLoading(true);
    setError(null);
    fetchCustomers(customerId)
      .then((res) => {
        const data = res?.data?.items || res?.data;
        setFetchedRecord(data || null);
      })
      .catch((err) => {
        setError(err?.message || "Failed to load customer.");
      })
      .finally(() => setLoading(false));
  }, [customerId, dataProp, routeMode, modeProp]);

  // Load assignee options (contacts)
  useEffect(() => {
    getContactOptions()
      .then((options) => setContactOptions(options as any))
      .catch(() => {});
  }, []);

  // Load project options
  useEffect(() => {
    getProjectOptions()
      .then((options) => setProjectOptions(options as any))
      .catch(() => {});
  }, []);

  /**
   * FK-based contact fetching:
   * Query contacts by customer_id FK instead of reading refs.links.contact.
   * Also compares FK result with refs.links and logs any mismatches.
   */
  const fetchFkContacts = useCallback(async (custId: number) => {
    if (!Number.isFinite(custId) || custId <= 0) {
      return;
    }

    setFkContactsLoading(true);
    try {
      const res = await getRecords("contact", { customer: custId });
      const results = res?.results ?? [];
      // Map raw contact records to RefContact shape
      const mapped = results.map((r: any) => ({
        contact_id: r.id,
        purpose: r.purpose || "",
        attention: r.attention || "",
        email: r.email || "",
        phone: r.phone || "",
        full: r.display_name || r.full || "",
      }));
      //console.log("[CustomerDetail.fetchFkContacts] mapped contacts:", mapped);
      setFkContacts(mapped);

      // --- Mismatch detection (FK vs refs.links.contact) ---
      // Use a snapshot; don't depend on fetchedRecord to avoid dep loops
      const fkIds = mapped.map((c: any) => c.contact_id).sort();
      logRefsMismatch({
        parent_model: "customer",
        parent_id: custId,
        related_model: "contact",
        fk_field: "customer_id",
        fk_ids: fkIds,
        refs_ids: [], // refs comparison deferred – avoids dep loop
        caller: "CustomerDetail.fetchFkContacts",
      });
    } catch (err) {
      console.error("[CustomerDetail] FK contact fetch failed:", err);
    } finally {
      setFkContactsLoading(false);
    }
  }, []); // no deps — stable function reference

  // Trigger FK contact fetch when customer id or refresh trigger changes
  useEffect(() => {
    // Skip when explicitly creating a new customer inline (modeProp) or via route
    if (modeProp === "add" || routeMode === "add") return;

    fetchFkContacts(resolvedCustomerId);
  }, [
    resolvedCustomerId,
    routeMode,
    fetchFkContacts,
    fkRefreshTrigger,
    modeProp,
  ]);

  // Window management - only when NOT rendered inline
  // Use a stable path derived from customer data rather than location.pathname
  // to avoid re-triggering when other windows change the browser URL.
  useEffect(() => {
    if (inline) return; // Skip window management for inline rendering
    const record = dataProp || fetchedRecord;
    if (!record && routeMode !== "add") return;
    const title =
      record?.display_name ||
      record?.name ||
      (routeMode === "add"
        ? "New Customer"
        : `Customer ${record?.id ?? customerId}`);
    const prefix = routeMode === "edit" ? "Edit " : "";
    const custId = record?.id ?? customerId;
    const stablePath =
      routeMode === "add"
        ? "/org/customer/add"
        : `/org/customer/detail/${custId}`;
    ensureWindow(stablePath, `${prefix}${title}`, { maximized: false });
  }, [inline, dataProp, fetchedRecord, ensureWindow, customerId, routeMode]);

  // ---------------------------------------------------------------------------
  // Nav Arrows (prev/next from list order)
  // ---------------------------------------------------------------------------
  const listOrder: number[] = useMemo(() => {
    try {
      const raw = localStorage.getItem("customer-list-order");
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }, []);

  const currentIndex = resolvedCustomerId
    ? listOrder.indexOf(resolvedCustomerId)
    : -1;
  const prevId = currentIndex > 0 ? listOrder[currentIndex - 1] : null;
  const nextId =
    currentIndex >= 0 && currentIndex < listOrder.length - 1
      ? listOrder[currentIndex + 1]
      : null;

  const openRecord = useCallback(
    (id: number) => {
      ensureWindow(`/org/customer/detail/${id}`, `Customer #${id}`, {
        maximized: false,
      });
    },
    [ensureWindow],
  );

  // Navigation handlers
  const handleClose = useCallback(() => {
    if (onCancelInline) {
      onCancelInline();
      return;
    }
    // Use stable path for closing window
    const record = dataProp || fetchedRecord;
    const custId = record?.id ?? customerId;
    const stablePath =
      routeMode === "add"
        ? "/org/customer/add"
        : `/org/customer/detail/${custId}`;
    closeWindow(stablePath);
  }, [
    onCancelInline,
    closeWindow,
    dataProp,
    fetchedRecord,
    customerId,
    routeMode,
  ]);

  // Removed duplicate openRecord. Using the new openRecord handler below.

  const handleDeleteClick = useCallback(async () => {
    const record = dataProp || fetchedRecord;
    if (onDeleteProp) {
      onDeleteProp();
      return;
    }
    if (!record?.id) return;
    if (
      !window.confirm(
        `Delete customer ${record.display_name || record.name || record.id}?`,
      )
    )
      return;
    try {
      await deleteCustomer(record.id);
      dispatch(
        showToast({
          message: "Customer deleted successfully",
          type: "success",
        }),
      );
      handleClose();
      navigate(PageRoutes.customerList);
    } catch (err: any) {
      dispatch(
        showToast({
          message: err?.message || "Failed to delete customer",
          type: "error",
        }),
      );
    }
  }, [onDeleteProp, dispatch, handleClose, navigate, dataProp, fetchedRecord]);

  // Resolved props - use provided or derived
  const onCancel = onCancelProp || handleClose;
  const onDelete = routeMode === "view" ? handleDeleteClick : undefined;

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors, isDirty, isSubmitting },
    reset,
    control,
    watch,
  } = useForm<CustomerFormValues>({
    resolver: zodResolver(customerSchema) as any,
    defaultValues: {
      is_active: false,
      version: 1,
      org_type: "customer",
      ...Object.fromEntries(
        Object.entries(JSON_DEFAULTS).map(([k, v]) => [k, JSON.stringify(v)]),
      ),
    },
  });

  const routeState = (location.state as any) || {};
  const baseMode: "add" | "edit" | "view" =
    modeProp ||
    routeMode ||
    (routeState.mode as "add" | "edit" | "view") ||
    "add";
  // Allow local edit override when in view mode
  const mode: "add" | "edit" | "view" =
    baseMode === "view" && isEditing ? "edit" : baseMode;
  const data = useMemo(() => {
    if (dataProp || fetchedRecord) {
      // Prefer live fetched changes over initial prop payload to ensure tabs render updates
      return { ...(dataProp || {}), ...(fetchedRecord || {}) } as any;
    }
    return routeState.data || null;
  }, [dataProp, fetchedRecord, routeState.data]);

  // Tab badges (memoized for reuse/generalization)
  const tabBadges = useMemo(
    () => buildCustomerTabBadges(data, fkContacts),
    [data, fkContacts],
  );

  useEffect(() => {
    if (mode === "add") {
      reset({
        is_active: false,
        version: 1,
        org_type: "customer",
        ...Object.fromEntries(
          Object.entries(JSON_DEFAULTS).map(([k, v]) => [k, JSON.stringify(v)]),
        ),
      });
      return;
    }
    if (data) {
      Object.keys(data).forEach((key: any) => {
        if (data[key] !== undefined) {
          if (key in JSON_DEFAULTS) {
            setValue(
              key,
              JSON.stringify(data[key] ?? JSON_DEFAULTS[key], null, 2),
            );
          } else {
            setValue(key, data[key]);
          }
        }
      });
      Object.keys(JSON_DEFAULTS).forEach((key) => {
        if (data[key] === undefined) {
          setValue(
            key as keyof CustomerFormValues,
            JSON.stringify(JSON_DEFAULTS[key]),
          );
        }
      });
    } else {
      reset({
        is_active: false,
        version: 1,
        org_type: "customer",
        ...Object.fromEntries(
          Object.entries(JSON_DEFAULTS).map(([k, v]) => [k, JSON.stringify(v)]),
        ),
      });
    }
  }, [data, reset, setValue, mode]);

  const parseJsonField = (label: string, raw?: string) => {
    if (!raw || raw.trim() === "") return undefined;
    try {
      return JSON.parse(raw);
    } catch {
      dispatch(
        showToast({ message: `${label} must be valid JSON`, type: "error" }),
      );
      throw new Error(`${label} JSON invalid`);
    }
  };

  const safeParseJson = (raw: string | undefined, fallback: unknown) => {
    if (!raw || raw.trim() === "") return fallback;
    try {
      return JSON.parse(raw);
    } catch {
      return raw;
    }
  };

  const resetToDefaults = () => {
    if (mode === "add") {
      reset({
        is_active: false,
        version: 1,
        org_type: "customer",
        ...Object.fromEntries(
          Object.entries(JSON_DEFAULTS).map(([k, v]) => [k, JSON.stringify(v)]),
        ),
      });
      return;
    }

    if (data) {
      const nextValues: Record<string, unknown> = {
        is_active: data.is_active ?? false,
        version: data.version ?? 1,
        org_type: data.org_type ?? "customer",
        display_name: data.display_name ?? "",
        status: data.status ?? "",
      };
      Object.keys(JSON_DEFAULTS).forEach((key) => {
        nextValues[key] = JSON.stringify(
          data[key] ?? JSON_DEFAULTS[key],
          null,
          2,
        );
      });
      reset(nextValues as CustomerFormValues);
      return;
    }

    reset({
      is_active: false,
      version: 1,
      org_type: "customer",
      ...Object.fromEntries(
        Object.entries(JSON_DEFAULTS).map(([k, v]) => [k, JSON.stringify(v)]),
      ),
    });
  };

  const handleCancel = () => {
    // If we're in local edit mode, just go back to view
    if (isEditing) {
      setIsEditing(false);
      resetToDefaults();
      return;
    }
    if (inline && onCancelInline) {
      onCancelInline();
      return;
    }
    if (onCancel) {
      onCancel();
      return;
    }
    resetToDefaults();
  };

  const saveCustomer = async (formData: CustomerFormValues) => {
    try {
      const jsonPayload: Record<string, any> = {};
      Object.keys(JSON_DEFAULTS).forEach((key) => {
        const parsed = parseJsonField(
          key,
          formData[key as keyof CustomerFormValues] as string | undefined,
        );
        if (parsed !== undefined) {
          jsonPayload[key] = parsed;
        }
      });
      const payload = {
        display_name: formData.display_name,
        status: formData.status,
        org_type: "customer" as const,
        version: formData.version,
        is_active: formData.is_active,
        // New scalar fields from wc3
        attention: formData.attention ?? undefined,
        contact_id: formData.contact_id ?? undefined,
        email: formData.email ?? undefined,
        phone: formData.phone ?? undefined,
        price_level: formData.price_level ?? undefined,
        terms: formData.terms ?? undefined,
        terms_id: formData.terms_id ?? undefined,
        address_full: formData.address_full ?? undefined,
        ...jsonPayload,
      };
      const res =
        mode === "add"
          ? await createCustomer(payload)
          : await updateCustomer({
              ...payload,
              id: data && data.id,
              org_type: "customer" as const,
            });
      if (res) {
        dispatch(
          showToast({
            message: `Customer ${
              mode === "add" ? "created" : "updated"
            } successfully`,
            type: "success",
          }),
        );

        // --- Auto-create contact for new customers ---
        if (mode === "add") {
          const newCustomerId = res?.id;
          if (newCustomerId) {
            try {
              await autoCreateContactForCustomer(
                newCustomerId,
                formData.display_name,
                formData.attention || "",
                formData.email || "",
                formData.phone || "",
              );
            } catch (contactErr: any) {
              // Contact creation is best-effort; don't block customer save
              console.error(
                "[CustomerDetail] Auto-contact creation failed:",
                contactErr,
              );
              dispatch(
                showToast({
                  message: `Customer saved, but contact creation failed: ${
                    contactErr?.message || "Unknown error"
                  }`,
                  type: "info",
                }),
              );
            }
          }
        }

        // Return to view mode after successful save
        if (isEditing) {
          setIsEditing(false);
        }
        // NOTE: onSaved() is intentionally NOT called here.
        // It should only be invoked by "Save & Close" flow via TransactionToolbar.
        return true;
      }
      return false;
    } catch (error: any) {
      dispatch(showToast({ message: error.message, type: "error" }));
      return false;
    }
  };

  /**
   * Auto-create a contact from new customer data, link the records
   * via refs.links, set customer.contact_id, then open the contact
   * detail page so the user can add an address.
   */
  const autoCreateContactForCustomer = useCallback(
    async (
      custId: number,
      displayName: string,
      attention: string,
      email: string,
      phone: string,
    ) => {
      // Parse attention into first/last name
      const nameParts = attention.trim().split(/\s+/);
      const firstName = nameParts[0] || displayName.split(/\s+/)[0] || "";
      const lastName =
        nameParts.length > 1
          ? nameParts.slice(1).join(" ")
          : displayName.split(/\s+/).slice(1).join(" ") || "";

      // 1. Create the contact with a link back to this customer
      const contactPayload = {
        name_first: firstName,
        name_last: lastName,
        attention: attention || displayName,
        email: email || `contact${custId}@placeholder.com`,
        phone: phone || undefined,
        company: displayName,
        customer_id: custId,
        comment: `Auto-created from customer #${custId}`,
        refs: {
          links: {
            rep: [],
            item: [],
            email: [],
            phone: [],
            order: [],
            domain: [],
            contact: [],
            customer: [String(custId)],
            document: [],
            address: [],
            manufacturer: [],
            project: [],
            vendor: [],
          },
          tags: [],
          categories: [],
          keywords: [],
          related_ids: [],
          depends_on: [],
        },
      };

      const contactResult = await createContact(
        contactPayload as CreateContactRequest,
      );
      const newContactId = contactResult?.id;

      if (!newContactId) {
        throw new Error("Contact created but no ID returned");
      }

      // 2. Update the customer with contact_id and refs.links.contact
      await updateCustomer({
        id: custId,
        contact_id: newContactId,
        refs: {
          links: {
            contact: [newContactId],
          },
        },
      } as any);

      dispatch(
        showToast({
          message: `Contact #${newContactId} created — opening to add address…`,
          type: "success",
        }),
      );

      // 3. Open the new contact detail page for address entry
      const contactPath = `/core/contact/detail/${newContactId}`;
      ensureWindow(contactPath, `Contact ${firstName} ${lastName}`.trim(), {
        maximized: false,
      });
      activateWindow(contactPath);
    },
    [dispatch, ensureWindow, activateWindow],
  );

  const onSubmit = async (formData: CustomerFormValues) => {
    await saveCustomer(formData);
  };

  // ---------------------------------------------------------------------------
  // Set Primary Contact – saves contact_id + denormalized fields on the org
  // ---------------------------------------------------------------------------
  const handleSetPrimary = useCallback(
    async (contact: {
      contact_id: number;
      attention?: string;
      email?: string | any[];
      phone?: string | any[];
    }) => {
      const custId = data?.id;
      if (!custId) return;

      // Extract scalar values from possibly polymorphic email/phone
      const emailStr =
        typeof contact.email === "string"
          ? contact.email
          : Array.isArray(contact.email) && contact.email.length > 0
          ? typeof contact.email[0] === "object"
            ? contact.email[0].value ?? ""
            : String(contact.email[0])
          : "";
      const phoneStr =
        typeof contact.phone === "string"
          ? contact.phone
          : Array.isArray(contact.phone) && contact.phone.length > 0
          ? typeof contact.phone[0] === "object"
            ? contact.phone[0].value ?? ""
            : String(contact.phone[0])
          : "";

      try {
        await updateCustomer({
          id: custId,
          contact_id: contact.contact_id,
          attention: contact.attention || null,
          email: emailStr || null,
          phone: phoneStr || null,
        } as any);

        // Update local form state so UI reflects the change immediately
        setValue("contact_id" as keyof CustomerFormValues, contact.contact_id);
        if (contact.attention)
          setValue("attention" as keyof CustomerFormValues, contact.attention);
        if (emailStr) setValue("email" as keyof CustomerFormValues, emailStr);
        if (phoneStr) setValue("phone" as keyof CustomerFormValues, phoneStr);

        // Refresh the parent record from the server
        const res = await getRecord("customer", custId);
        const rec = res?.record ?? res;
        if (rec) {
          setFetchedRecord(rec);
        }

        dispatch(
          showToast({
            message: `Contact #${contact.contact_id} set as primary`,
            type: "success",
          }),
        );
      } catch (err) {
        console.error("[CustomerDetail.handleSetPrimary] failed:", err);
        dispatch(
          showToast({
            message: "Failed to set primary contact",
            type: "error",
          }),
        );
      }
    },
    [data?.id, dispatch, setValue],
  );

  // Action buttons configuration based on mode
  const getActionButtons = () => {
    const buttons: React.ReactNode[] = [];

    if (mode === "view") {
      buttons.push(
        <button
          key="edit"
          type="button"
          onClick={() => setIsEditing(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
          title="Edit Customer"
        >
          <FaEdit size={14} />
          Edit
        </button>,
      );
    }

    // Prev/Next nav arrows
    if (prevId) {
      buttons.push(
        <button
          key="prev"
          type="button"
          onClick={() => openRecord(prevId)}
          className="p-2 text-slate-500 hover:text-blue-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          title={`Previous (#${prevId})`}
        >
          <FaChevronLeft size={14} />
        </button>,
      );
    }
    if (nextId) {
      buttons.push(
        <button
          key="next"
          type="button"
          onClick={() => openRecord(nextId)}
          className="p-2 text-slate-500 hover:text-blue-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          title={`Next (#${nextId})`}
        >
          <FaChevronRight size={14} />
        </button>,
      );
    }

    // Delete button (right side, before close)
    if (mode === "view" && data?.id && onDelete) {
      buttons.push(
        <button
          key="delete"
          type="button"
          onClick={onDelete}
          className="p-2 text-rose-600 hover:bg-rose-50 dark:hover:bg-slate-700 rounded-lg transition-colors"
          title="Delete customer"
        >
          <FaTrash size={14} />
        </button>,
      );
    }

    // Close button (right side)
    if (onCancel) {
      buttons.push(
        <button
          key="close"
          type="button"
          onClick={onCancel}
          className="p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          title="Close"
        >
          <FaTimes size={14} />
        </button>,
      );
    }

    return buttons;
  };

  const formData = watch();

  // In view mode, prefer direct data from props; in edit/add mode, use form values
  const customerData: Customer =
    mode === "view" && data
      ? {
          ...data,
          id: data.id,
          display_name: data.display_name,
          status: data.status,
          org_type: data.org_type,
          version: data.version,
          is_active: data.is_active,
          attention: data.attention,
          contact_id: data.contact_id,
          email: data.email,
          phone: data.phone,
          price_level: data.price_level,
          terms: data.terms,
          terms_id: data.terms_id,
          address_full: data.address_full,
          financial: data.financial,
        }
      : {
          ...formData,
          id: data?.id,
          display_name: formData.display_name,
          status: formData.status,
          org_type: formData.org_type,
          version: formData.version,
          is_active: formData.is_active,
        };

  // Handle loading and error states for data fetch
  if (loading) {
    return <RippleLoader />;
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-red-600 dark:text-red-400">{error}</div>
      </div>
    );
  }

  // For view/edit modes, wait for data before rendering. Use resolved `mode`
  // (which respects `modeProp`) so inline add mode doesn't block rendering.
  if (mode !== "add" && !data && !dataProp) {
    return <RippleLoader />;
  }

  return (
    <div className="h-full flex flex-col bg-white dark:bg-slate-900">
      {/* Compact Header */}
      <div className="shrink-0 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2">
        <div className="flex items-center justify-between">
          <div className="min-w-0 flex-1">
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100 truncate">
              <DevBadge label="CustomerDetail" className="mr-2" />
              {customerData.display_name || "New Customer"}
              {customerData.id && (
                <span className="ml-2 text-xs font-normal text-slate-500 dark:text-slate-400">
                  #{customerData.id}
                </span>
              )}
            </h2>
            <div className="flex items-center gap-2 mt-0.5">
              <span
                className={`inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium rounded ${
                  customerData.is_active
                    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400"
                    : "bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400"
                }`}
              >
                {customerData.is_active ? "Active" : "Inactive"}
              </span>
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {customerData.org_type || "customer"} • v
                {customerData.version ?? 1}
              </span>
              {(mode === "edit" || mode === "add") && isDirty && (
                <span className="px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-300 bg-amber-100 dark:bg-amber-900/30 rounded">
                  Unsaved changes
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-1 ml-3">
            {getActionButtons()}
          </div>
        </div>
      </div>

      {/* Transaction-style Toolbar (edit/add mode) */}
      {(mode === "edit" || mode === "add") && (
        <div className="sticky top-0 z-20 mx-0 px-3 py-2 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm border-b border-slate-200 dark:border-slate-700">
          <TransactionToolbar
            transactionType="order"
            transactionId={data?.id}
            isDirty={isDirty}
            isSaving={isSubmitting}
            isEditing
            onSave={handleSubmit(async (fd) => {
              await saveCustomer(fd);
            })}
            onSaved={onSaved}
            onCancel={handleCancel}
            canClone={false}
            canTransfer={false}
            canDelete={false}
            showTaskButton={false}
          />
        </div>
      )}

      {/* Persistent Basic Information Panel - always visible in view mode */}
      {/* In edit/add mode, show editable form fields instead */}
      <div className="shrink-0 px-3 py-2 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
        {mode === "view" ? (
          <BasicInformationPanel data={customerData} columns={columnCount} />
        ) : (
          <>
            <div
              className={`grid grid-cols-1 ${
                columnCount === 3 ? "lg:grid-cols-3" : "lg:grid-cols-2"
              } gap-x-6 gap-y-1`}
            >
              <HorizontalField
                label="display_name"
                htmlFor="display_name"
                required
                error={errors.display_name?.message}
              >
                <Input
                  type="text"
                  id="display_name"
                  placeholder="display_name"
                  {...register("display_name")}
                  error={
                    errors.display_name && errors.display_name.message
                      ? true
                      : false
                  }
                />
              </HorizontalField>

              <HorizontalField label="org_type" htmlFor="org_type">
                <Controller
                  name="org_type"
                  control={control}
                  render={({ field }) => (
                    <Select
                      options={ORG_TYPE_OPTIONS}
                      value={field.value ?? ""}
                      onChange={field.onChange}
                      placeholder="org_type"
                    />
                  )}
                />
              </HorizontalField>

              <HorizontalField label="email" htmlFor="email">
                <Input
                  type="email"
                  id="email"
                  placeholder="email"
                  {...register("email")}
                />
              </HorizontalField>

              <HorizontalField label="attention" htmlFor="attention">
                <Input
                  type="text"
                  id="attention"
                  placeholder="attention"
                  {...register("attention")}
                />
              </HorizontalField>

              <HorizontalField label="phone" htmlFor="phone">
                <Controller
                  name="phone"
                  control={control}
                  render={({ field }) => (
                    <InternationalPhoneInput
                      id="phone"
                      value={field.value ?? ""}
                      onBlur={field.onBlur}
                      onChange={field.onChange}
                    />
                  )}
                />
              </HorizontalField>

              <HorizontalField label="price_level" htmlFor="price_level">
                <Controller
                  name="price_level"
                  control={control}
                  render={({ field }) => (
                    <Select
                      options={PRICE_LEVEL_OPTIONS}
                      value={field.value ?? ""}
                      onChange={field.onChange}
                      placeholder="price_level"
                    />
                  )}
                />
              </HorizontalField>

              <HorizontalField label="terms" htmlFor="terms">
                <Controller
                  name="terms"
                  control={control}
                  render={({ field }) => (
                    <Select
                      options={TERMS_OPTIONS}
                      value={field.value ?? ""}
                      onChange={field.onChange}
                      placeholder="terms"
                    />
                  )}
                />
              </HorizontalField>

              <HorizontalField label="status" htmlFor="status" required>
                <Controller
                  name="status"
                  control={control}
                  render={({ field }) => (
                    <Select
                      options={STATUS_OPTIONS}
                      value={field.value ?? ""}
                      onChange={field.onChange}
                      placeholder="status"
                    />
                  )}
                />
              </HorizontalField>

              <HorizontalField label="version" htmlFor="version">
                <Input
                  type="number"
                  id="version"
                  placeholder="1"
                  {...register("version", { valueAsNumber: true })}
                />
              </HorizontalField>
            </div>
            <div
              className={`grid grid-cols-1 ${
                columnCount === 3 ? "lg:grid-cols-3" : "lg:grid-cols-2"
              } gap-x-6 gap-y-1`}
            >
              <HorizontalField label="address_full" htmlFor="address_full">
                <Input
                  type="text"
                  id="address_full"
                  placeholder="address_full"
                  {...register("address_full")}
                  className="w-100"
                />
              </HorizontalField>
              <div className="w-18 shrink-0" />
              <Controller
                name="is_active"
                control={control}
                render={({ field }) => (
                  <Checkbox
                    id="is_active"
                    checked={field.value ?? false}
                    onChange={field.onChange}
                    label="is_active"
                  />
                )}
              />
            </div>
          </>
        )}
      </div>
      <div className="flex items-center justify-between py-2 gap-4">
        <ColumnSelector value={columnCount} onChange={handleColumnChange} />
      </div>
      {/* Scrollable content: detail panels · transactions · items */}
      {mode !== "add" ? (
        <div className="space-y-2 px-4 py-2">
          {/* ── DetailTabs ────────────────────────────────────────── */}
          <div>
            <DetailTabs
              entityType="customer"
              activeTab={activeTab}
              onTabChange={handleTabChange}
              standardTabs={CUSTOMER_STANDARD_TABS}
              additionalTabs={CUSTOMER_ADDITIONAL_TABS}
              badges={tabBadges}
              showColumnSelector={false}
              columnCount={columnCount}
              onColumnCountChange={handleColumnChange}
            />
            <div className="flex-1 cus-bg-black-light rounded-md">
              <div className="p-2">
                {/* Standard Tabs - Comments */}
                {activeTab === "comments" && (
                  <CommentsPanel
                    entityType="customer"
                    entityId={data?.id || 0}
                    comments={data?.comments}
                    isEditing={mode !== "view" || isEditing}
                    onChange={(comments) =>
                      setFetchedRecord(
                        (prev) =>
                          ({
                            ...(prev || data || {}),
                            comments,
                          } as any),
                      )
                    }
                    onSave={async (comments) => {
                      if (!data?.id) return;
                      try {
                        await updateCustomer({
                          id: data.id,
                          comments: { mode: "update", value: comments },
                        } as any);
                        dispatch(
                          showToast({
                            message: "Comments saved",
                            type: "success",
                          }),
                        );
                      } catch {
                        dispatch(
                          showToast({
                            message: "Failed to save comments",
                            type: "error",
                          }),
                        );
                      }
                    }}
                    currentUser={`${currentUser?.name_first} ${currentUser?.name_last}`}
                    currentUserId={currentUser?.id}
                  />
                )}

                {/* Standard Tabs - Actions */}

                {activeTab === "actions" && (
                  <ActionsPanel
                    entityType="customer"
                    entityId={data?.id || 0}
                    data={
                      Array.isArray(data?.actions) ? data.actions : undefined
                    }
                    actionIds={
                      data?.actions &&
                      typeof data.actions === "object" &&
                      "ids" in data.actions
                        ? (data.actions as { ids?: number[] }).ids
                        : undefined
                    }
                    viewMode="table"
                    isEditing={isEditing}
                    parentModelName="customer"
                    parentIdOverride={data?.id}
                    onChange={(actions) =>
                      setFetchedRecord(
                        (prev) =>
                          ({
                            ...(prev || data || {}),
                            actions,
                          } as any),
                      )
                    }
                    onActionIdsChange={(ids) =>
                      setFetchedRecord(
                        (prev) =>
                          ({
                            ...(prev || data || {}),
                            actions: { ids },
                          } as any),
                      )
                    }
                    onSave={async (actions) => {
                      if (!data?.id) return;
                      try {
                        await updateCustomer({ id: data.id, actions } as any);
                        // Refresh from server to capture latest refs/actions snapshot
                        try {
                          const refreshed = await getRecord(
                            "customer",
                            data.id,
                          );
                          const next = (refreshed as any)?.record ?? refreshed;
                          if (next) {
                            setFetchedRecord(next as any);
                          }
                        } catch (refreshErr) {
                          console.error(
                            "[CustomerDetail] Action refresh failed",
                            refreshErr,
                          );
                        }
                        dispatch(
                          showToast({
                            message: "Action saved",
                            type: "success",
                          }),
                        );
                      } catch {
                        dispatch(
                          showToast({
                            message: "Failed to save action",
                            type: "error",
                          }),
                        );
                      }
                    }}
                    assigneeOptions={contactOptions}
                    projectOptions={projectOptions}
                  />
                )}
                {activeTab === "contacts" && (
                  <ContactPanel
                    contacts={fkContacts}
                    isEditing={true}
                    loading={fkContactsLoading}
                    parent_model="customer"
                    parentId={customerData.id}
                    customer_id={customerData.id}
                    customer_name={customerData.display_name}
                    primaryContactId={data?.contact_id}
                    onSetPrimary={handleSetPrimary}
                    onRefresh={() => setFkRefreshTrigger((n) => n + 1)}
                    onChange={(newContacts) => {
                      const currentRefs = safeParseJson(
                        formData.refs as unknown as string | undefined,
                        { links: {} },
                      );
                      setValue(
                        "refs" as keyof CustomerFormValues,
                        JSON.stringify(
                          {
                            ...currentRefs,
                            links: {
                              ...currentRefs.links,
                              contact: newContacts,
                            },
                          },
                          null,
                          2,
                        ) as any,
                        { shouldDirty: true },
                      );
                    }}
                    onSaveSuccess={() => {
                      setFkRefreshTrigger((n) => n + 1);
                      if (customerData.id) {
                        getRecord("customer", customerData.id)
                          .then((res: any) => {
                            const rec = res?.record ?? res;
                            if (rec) {
                              setFetchedRecord(rec);
                              Object.keys(rec).forEach((key) => {
                                if (key in JSON_DEFAULTS) {
                                  setValue(
                                    key as keyof CustomerFormValues,
                                    JSON.stringify(
                                      rec[key] ?? JSON_DEFAULTS[key],
                                      null,
                                      2,
                                    ),
                                  );
                                } else {
                                  setValue(
                                    key as keyof CustomerFormValues,
                                    rec[key],
                                  );
                                }
                              });
                            }
                          })
                          .catch(() => {});
                      }
                    }}
                  />
                )}

                {/* Standard Tabs - Documents */}
                {activeTab === "documents" && (
                  <DocumentsPanel
                    parent_model="customer"
                    parentId={data?.id || 0}
                    data={data?.refs?.links?.document}
                    isEditing={mode !== "view" || isEditing}
                    onChange={(docs) => {
                      console.log("Documents updated:", docs);
                    }}
                  />
                )}

                {/* Q&A tab */}
                {activeTab === "qa" && (
                  <QAPanel
                    parent_model="customer"
                    parentId={data?.id || 0}
                    data={data?.qa}
                  />
                )}

                {/* Standard Tabs - Raw (Admin) */}
                {activeTab === "raw" && (
                  <RawDataPanel
                    entityType="customer"
                    entityId={data?.id || 0}
                    data={data}
                  />
                )}
              </div>
            </div>
          </div>

          {/* ── Finance DetailTabs ────────────────────────────────────── */}

          <div>
            <DetailTabs
              entityType="customer-finance"
              activeTab={financeActiveTab}
              onTabChange={handleFinanceTabChange}
              standardTabs={FINANCE_STANDARD_TABS}
              additionalTabs={FINANCE_ADDITIONAL_TABS}
              badges={{}}
              showColumnSelector={false}
              columnCount={columnCount}
              onColumnCountChange={handleColumnChange}
            />
            <div className="flex-1 cus-bg-black-light rounded-md">
              <div className="p-2">
                {financeActiveTab === "transactions" && (
                  <TransactionTabs
                    orgType="customer"
                    orgId={customerData.id!}
                  />
                )}
              </div>
            </div>
          </div>

          {/* ── Items DetailTabs ────────────────────────────────────── */}
          <div>
            <DetailTabs
              entityType="customer-items"
              activeTab={itemsActiveTab}
              onTabChange={handleItemsTabChange}
              standardTabs={ITEMS_STANDARD_TABS}
              additionalTabs={ITEMS_ADDITIONAL_TABS}
              badges={{}}
              showColumnSelector={false}
              columnCount={columnCount}
              onColumnCountChange={handleColumnChange}
            />
            <div className="flex-1 cus-bg-black-light rounded-md">
              <div className="p-2">
                {itemsActiveTab === "products" && (
                  <ItemTabs orgType="customer" orgId={customerData.id!} />
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {/* ── Scalar & JSONB cards (view mode) ───────────────────── */}
      {mode === "view" && data && (
        <div className="space-y-2 px-4 py-2">
          <ScalarCard
            title="Organization Details"
            fields={[
              { label: "display_name", value: data.display_name },
              { label: "org_type", value: data.org_type },
              { label: "email", value: data.email },
              { label: "email_id", value: data.email_id },
              { label: "attention", value: data.attention },
              { label: "phone", value: data.phone },
              { label: "phone_id", value: data.phone_id },
              { label: "address_full", value: data.address_full },
              { label: "address_id", value: data.address_id },
              { label: "domain", value: data.domain },
              { label: "domain_id", value: data.domain_id },
              { label: "price_level", value: data.price_level },
              { label: "terms", value: data.terms },
              { label: "status", value: data.status },
              { label: "contact_id", value: data.contact_id },
            ]}
            columns={3}
          />
          <JsonCard
            title="Financial"
            fieldName="financial"
            data={data.financial as Record<string, unknown>}
            columns={2}
          />
          <JsonCard
            title="Connections"
            fieldName="connections"
            data={data.connections as Record<string, unknown>}
            columns={2}
          />
          <JsonCard
            title="Data"
            fieldName="data"
            data={data.data as Record<string, unknown>}
            columns={2}
          />
          <JsonCard
            title="Metrics"
            fieldName="metrics"
            data={data.metrics as Record<string, unknown>}
            columns={2}
          />
          <JsonCard
            title="GL Accounts"
            fieldName="gl_accounts"
            data={data.gl_accounts as Record<string, unknown>}
            columns={2}
          />
          <JsonCard
            title="Relations"
            fieldName="relations"
            data={data.relations as Record<string, unknown>}
            columns={2}
          />
          <BaseModelCards data={data} />
        </div>
      )}
    </div>
  );
}

export default withDevIdentifier(CustomerDetail, "CustomerDetail");
