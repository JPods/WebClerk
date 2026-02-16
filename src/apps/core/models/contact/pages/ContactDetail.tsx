/**
 * ContactDetail.tsx
 *
 * Standard Contact Detail page following the enterprise UI pattern:
 *
 * ┌────────────────────────────────────────┐
 * │  Header (Title, ID, Status, Actions)   │
 * ├────────────────────────────────────────┤
 * │  Toolbar (Save, Cancel) — edit/add     │
 * ├────────────────────────────────────────┤
 * │  Basic Information (PERSISTENT)        │
 * ├────────────────────────────────────────┤
 * │  Tab Navigation                        │
 * ├────────────────────────────────────────┤
 * │  Tab Content (scrollable)              │
 * └────────────────────────────────────────┘
 *
 * @see ui-form-layout-research.md for design rationale
 */

import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

// UI primitives
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import DropDown from "@/components/form/input/DropDown";
import Checkbox from "@/components/form/input/Checkbox";
import RippleLoader from "@/components/common/RippleLoader";

// API
import { getRecord, getRecords, saveRecord } from "@/api/wcapi";
import { createContact, updateContact } from "../services/contactApi";
import {
  contactSchema,
  updateContactSchema,
  mapRefsFormToApi,
} from "../utils/contactSchema";
import {
  ContactAddProps,
  CreateContactRequest,
  UpdateContactRequest,
} from "../types/contactType";

// State
import { showToast } from "@/store/slices/toastSlice";
import { useAppSelector } from "@/store/hooks";
import { useDispatch } from "react-redux";
import { useLocation, useParams, useSearchParams } from "react-router";
import { useWindowManager } from "@/context/WindowManagerContext";
import { useWindowPath } from "@/context/WindowPathContext";

// Hooks
import { useDetailFieldAccess } from "@/hooks/useDetailFieldAccess";

// Toolbar
import TransactionToolbar from "@/apps/common/components/TransactionToolbar";

// Tab navigation
import {
  DetailTabs,
  useDetailTabs,
  useColumnCount,
  TabConfig,
} from "@/components/common/DetailTabs";

// Icons
import {
  FaChevronLeft,
  FaChevronRight,
  FaEdit,
  FaUser,
  FaPlus,
  FaFileInvoiceDollar,
  FaSearch,
  FaShoppingCart,
  FaClipboardList,
} from "react-icons/fa";
import { History, Link, Phone, SlidersHorizontal } from "lucide-react";

// Panel Components
import {
  ActionsPanel,
  CommentsPanel,
  CommunicationsPanel,
  DocumentsPanel,
  MetadataPanel,
  PrefsPanel,
  RawDataPanel,
  RefsPanel,
} from "@/apps/common/components/panels";

// Org search dialog
import OrgSearchDialog from "@/apps/common/components/OrgSearchDialog";
import type {
  OrgSearchResult,
  SearchableOrgType,
} from "@/apps/common/components/OrgSearchDialog";

// ---------------------------------------------------------------------------
// Create Transaction Dropdown
// ---------------------------------------------------------------------------

const TRANSACTION_OPTIONS = [
  {
    value: "proposal",
    label: "Proposal",
    icon: FaClipboardList,
    path: "/transactions/proposal/detail/",
  },
  {
    value: "order",
    label: "Order",
    icon: FaShoppingCart,
    path: "/transactions/order/detail/",
  },
  {
    value: "invoice",
    label: "Invoice",
    icon: FaFileInvoiceDollar,
    path: "/transactions/invoice/detail/",
  },
] as const;

interface CreateTransactionDropdownProps {
  customerId?: number | null;
  customerName?: string;
  contactId?: number | null;
  contactName?: string;
  attention?: string | null;
  email?: string | null;
  phone?: string | null;
  ensureWindow: (
    path: string,
    title: string,
    opts?: { maximized?: boolean },
  ) => void;
}

function CreateTransactionDropdown({
  customerId,
  customerName,
  contactId,
  contactName,
  attention,
  email,
  phone,
  ensureWindow,
}: CreateTransactionDropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const handleSelect = (opt: (typeof TRANSACTION_OPTIONS)[number]) => {
    setOpen(false);
    const qs = new URLSearchParams();
    if (customerId) qs.set("customer_id", String(customerId));
    if (customerName) qs.set("customer_name", customerName);
    if (contactId) qs.set("contact_id", String(contactId));
    if (contactName) qs.set("contact_name", contactName);
    if (attention) qs.set("attention", attention);
    if (email) qs.set("email", email);
    if (phone) qs.set("phone", phone);
    const query = qs.toString();
    const path = `${opt.path}${query ? `?${query}` : ""}`;
    ensureWindow(path, `New ${opt.label}`, { maximized: false });
  };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-emerald-600 bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-900/20 dark:text-emerald-400 dark:hover:bg-emerald-900/30 rounded-lg transition-colors"
        title="Create transaction from this contact"
      >
        <FaPlus size={10} />
        Create
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 w-44 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg z-50 py-1">
          {TRANSACTION_OPTIONS.map((opt) => {
            const Icon = opt.icon;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => handleSelect(opt)}
                className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-left"
              >
                <Icon size={14} className="text-slate-400" />
                {opt.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const VALID_TABS = [
  "actions",
  "comments",
  "communications",
  "documents",
  "history",
  "metadata",
  "prefs",
  "raw",
  "refs",
];

const CONTACT_DETAIL_FIELDS = [
  "attention",
  "email",
  "password",
  "cnf_password",
  "name_first",
  "name_last",
  "name_middle",
  "name_prefix",
  "name_suffix",
  "company",
  "title",
  "department",
  "customer_id",
  "rep_id",
  "vendor_id",
  "employee_id",
  "manufacturer_id",
  "other_id",
  "role",
  "is_active",
  "is_staff",
] as const;

const ROLE_OPTIONS = [
  { value: "user", label: "User" },
  { value: "admin", label: "Administrator" },
  { value: "manager", label: "Manager" },
  { value: "staff", label: "Staff" },
  { value: "guest", label: "Guest" },
];

/** Maps parent org model name → the foreign-key field on Contact */
const PARENT_MODEL_TO_ID_FIELD: Record<string, string> = {
  customer: "customer_id",
  vendor: "vendor_id",
  rep: "rep_id",
  employee: "employee_id",
  manufacturer: "manufacturer_id",
};

/** Maps FK field name → org type for the search dialog */
const ID_FIELD_TO_ORG_TYPE: Record<string, SearchableOrgType> = {
  customer_id: "customer",
  vendor_id: "vendor",
  rep_id: "rep",
  employee_id: "employee",
  manufacturer_id: "manufacturer",
  other_id: "organization",
};

// ---------------------------------------------------------------------------
// HorizontalField — label-left for edit mode
// ---------------------------------------------------------------------------

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
    <div className="flex items-center gap-2 py-1.5">
      <Label
        htmlFor={htmlFor}
        className="w-32 shrink-0 text-right text-sm font-medium text-slate-600 dark:text-slate-400"
      >
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </Label>
      <div className="flex-1 min-w-0">
        {children}
        {error && <p className="mt-0.5 text-xs text-red-500">{error}</p>}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// InfoRow — read-only horizontal label/value pair
// ---------------------------------------------------------------------------

const InfoRow: React.FC<{ label: string; value: React.ReactNode }> = ({
  label,
  value,
}) => (
  <div className="flex items-center gap-2">
    <dt className="w-32 shrink-0 text-right text-sm text-slate-500 dark:text-slate-400">
      {label}
    </dt>
    <dd className="font-medium text-sm text-slate-900 dark:text-slate-100">
      {value || "—"}
    </dd>
  </div>
);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type CommunicationsData = {
  emails?: any[];
  phones?: any[];
  addresses?: any[];
  domains?: any[];
};

const normalizeNumber = (value: any): number | undefined => {
  if (value === null || value === undefined || value === "") return undefined;
  const num = Number(value);
  return isNaN(num) ? undefined : num;
};

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function ContactDetail({
  modeProp,
  dataProp,
  hideBreadcrumb: _hideBreadcrumb,
  onSaved,
  inline: _inline = false,
  onCancelInline,
  id: idProp,
  recordId,
}: ContactAddProps) {
  const dispatch = useDispatch();
  const location = useLocation();
  const params = useParams<{ id?: string }>();
  const [searchParams] = useSearchParams();
  const windowManager = useWindowManager();

  // Floating windows provide their full path (incl. query string) via context.
  // This is more reliable than useSearchParams() which reads the browser URL
  // and may not yet reflect the navigate() call that created the window.
  const windowPath = useWindowPath();
  const effectiveSearchParams = useMemo(() => {
    if (windowPath && windowPath.includes("?")) {
      return new URLSearchParams(windowPath.split("?")[1]);
    }
    return searchParams;
  }, [windowPath, searchParams]);

  // Auth
  const authUser = useAppSelector((state) => state.auth.user);
  const currentUserName = authUser
    ? `${authUser.name_first || ""}${authUser.name_last || ""}`
    : "You";
  const currentUserId = authUser?.id;

  const routeState = (location.state as any) || {};

  // ---------------------------------------------------------------------------
  // Parent context (when opened from an org detail page)
  // Query params like ?parent_model=customer&parent_id=42&customer_name=Acme
  // ---------------------------------------------------------------------------

  const parentModel = effectiveSearchParams.get("parent_model") || undefined;
  const parentId = effectiveSearchParams.get("parent_id")
    ? parseInt(effectiveSearchParams.get("parent_id")!, 10)
    : undefined;
  const parentCustomerId = effectiveSearchParams.get("customer_id")
    ? parseInt(effectiveSearchParams.get("customer_id")!, 10)
    : undefined;
  const parentCustomerName =
    effectiveSearchParams.get("customer_name") || undefined;

  // Which contact field to auto-populate (e.g. "customer_id" for parent_model=customer)
  const parentIdField = parentModel
    ? PARENT_MODEL_TO_ID_FIELD[parentModel]
    : undefined;

  // ---------------------------------------------------------------------------
  // ID Resolution
  // ---------------------------------------------------------------------------

  const urlId =
    idProp ||
    recordId ||
    params.id ||
    effectiveSearchParams.get("id") ||
    routeState.data?.id ||
    dataProp?.id;

  const contactIdFromUrl = urlId
    ? typeof urlId === "number"
      ? urlId
      : parseInt(String(urlId), 10)
    : null;

  // ---------------------------------------------------------------------------
  // Mode
  // ---------------------------------------------------------------------------

  const baseMode: "add" | "edit" | "view" =
    modeProp || routeState.mode || (contactIdFromUrl ? "view" : "add");
  const [effectiveMode, setEffectiveMode] = useState(baseMode);

  useEffect(() => {
    setEffectiveMode(baseMode);
  }, [baseMode]);

  const isEditing = effectiveMode === "edit" || effectiveMode === "add";

  // ---------------------------------------------------------------------------
  // Data Loading
  // ---------------------------------------------------------------------------

  const [fetchedData, setFetchedData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const initialData = dataProp || routeState.data || null;
  const data = fetchedData || initialData;
  const activeContactId = data?.id || contactIdFromUrl || null;

  useEffect(() => {
    if (contactIdFromUrl && contactIdFromUrl !== fetchedData?.id) {
      if (initialData?.id === contactIdFromUrl) return;
      setIsLoading(true);
      getRecord("contact", contactIdFromUrl)
        .then((result) => setFetchedData(result?.record || result))
        .catch((err) =>
          console.error("[ContactDetail] Failed to fetch contact:", err),
        )
        .finally(() => setIsLoading(false));
    }
  }, [contactIdFromUrl, initialData?.id, fetchedData?.id]);

  // ---------------------------------------------------------------------------
  // Communications local state
  // ---------------------------------------------------------------------------

  // Helper to get non-empty array or fallback
  const getCommsArray = (
    primary: any[] | undefined,
    fallback: any[] | undefined,
  ) => {
    if (primary && primary.length > 0) return primary;
    return fallback || [];
  };

  const [communications, setCommunications] = useState<CommunicationsData>({
    emails: getCommsArray(
      data?.communications?.emails,
      data?.refs?.links?.email,
    ),
    phones: getCommsArray(
      data?.communications?.phones,
      data?.refs?.links?.phone,
    ),
    addresses: getCommsArray(
      data?.communications?.addresses,
      data?.refs?.links?.location,
    ),
    domains: getCommsArray(
      data?.communications?.domains,
      data?.refs?.links?.domain,
    ),
  });

  useEffect(() => {
    if (data?.communications || data?.refs?.links) {
      setCommunications({
        emails: getCommsArray(
          data.communications?.emails,
          data.refs?.links?.email,
        ),
        phones: getCommsArray(
          data.communications?.phones,
          data.refs?.links?.phone,
        ),
        addresses: getCommsArray(
          data.communications?.addresses,
          data.refs?.links?.location,
        ),
        domains: getCommsArray(
          data.communications?.domains,
          data.refs?.links?.domain,
        ),
      });
    }
  }, [data?.communications, data?.refs?.links]);

  // ---------------------------------------------------------------------------
  // Tab Navigation
  // ---------------------------------------------------------------------------

  const { activeTab, setActiveTab } = useDetailTabs(
    "contact",
    "actions",
    VALID_TABS,
  );
  const { columnCount, setColumnCount } = useColumnCount("contact", 3);

  const additionalTabs: TabConfig[] = useMemo(
    () => [
      { id: "communications", label: "Comms", icon: <Phone size={14} /> },
      { id: "history", label: "History", icon: <History size={14} /> },
      { id: "metadata", label: "Metadata", icon: <History size={14} /> },
      { id: "prefs", label: "Prefs", icon: <SlidersHorizontal size={14} /> },
      { id: "refs", label: "Refs", icon: <Link size={14} /> },
    ],
    [],
  );

  const tabBadges = useMemo(
    () => ({
      comments:
        (Array.isArray(data?.comments?.public)
          ? data.comments.public.length
          : 0) +
        (Array.isArray(data?.comments?.process)
          ? data.comments.process.length
          : 0) +
        (Array.isArray(data?.comments?.partner)
          ? data.comments.partner.length
          : 0) +
        (Array.isArray(data?.comments?.notes) ? data.comments.notes.length : 0),
      documents: data?.refs?.links?.document?.length || 0,
      actions: Array.isArray(data?.actions) ? data.actions.length : 0,
    }),
    [data],
  );

  // ---------------------------------------------------------------------------
  // Contact & Project options (for ActionsPanel)
  // ---------------------------------------------------------------------------

  const [contactOptions, setContactOptions] = useState<
    Array<{ id: string; label: string }>
  >([]);
  const [projectOptions, setProjectOptions] = useState<
    Array<{ id: string; name?: string; intent?: string }>
  >([]);

  useEffect(() => {
    getRecords("contact", { is_active: true, limit: 500 })
      .then((response: any) => {
        const records: any[] =
          response?.results || response?.data || response?.items || [];
        setContactOptions(
          records
            .filter((r: any) => r.id != null)
            .map((r: any) => ({
              id: String(r.id),
              label: r.attention || r.name || `Contact #${r.id}`,
            }))
            .sort((a, b) => a.label.localeCompare(b.label)),
        );
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    getRecords("project", { is_active: true, limit: 500 })
      .then((response: any) => {
        const records: any[] =
          response?.results || response?.data || response?.items || [];
        setProjectOptions(
          records
            .filter((r: any) => r.id != null)
            .map((r: any) => ({
              id: String(r.id),
              name: r.name || undefined,
              intent: r.intent || undefined,
            }))
            .sort((a, b) =>
              (a.name || a.intent || "").localeCompare(
                b.name || b.intent || "",
              ),
            ),
        );
      })
      .catch(() => {});
  }, []);

  // ---------------------------------------------------------------------------
  // Field Access Control
  // ---------------------------------------------------------------------------

  const contactFieldNames = useMemo(() => CONTACT_DETAIL_FIELDS.slice(), []);
  const { isAdmin, isFieldVisible, isFieldReadOnly } = useDetailFieldAccess(
    "contact",
    contactFieldNames,
  );

  /**
   * Parent-populated ID fields are read-only. Two sources:
   * 1. Query params (e.g. ?parent_model=customer&parent_id=42) — add mode from org page
   * 2. Fetched record data (e.g. contact already has customer_id set) — view/edit of
   *    a contact that was created from an org detail page
   */
  const parentPopulatedFields = useMemo(() => {
    const fields = new Set<string>();
    // Only lock fields that were explicitly set via parent-context URL params
    // (e.g. ?parent_model=customer&parent_id=42 from an org detail page).
    // Existing values on the record should remain editable.
    if (parentIdField && parentId) fields.add(parentIdField);
    if (parentCustomerId) fields.add("customer_id");
    return fields;
  }, [parentIdField, parentId, parentCustomerId]);

  const isFieldDisabled = (fieldName: string) => {
    if (effectiveMode === "view") return true;
    if (parentPopulatedFields.has(fieldName)) return true;
    if (!isAdmin && isFieldReadOnly(fieldName)) return true;
    return false;
  };

  const shouldRenderField = (fieldName: string) => {
    if (isAdmin) return true;
    return isFieldVisible(fieldName);
  };

  // ---------------------------------------------------------------------------
  // React Hook Form
  // ---------------------------------------------------------------------------

  const {
    register,
    control,
    handleSubmit,
    reset,
    setValue,
    formState: { errors, isDirty, isSubmitting },
  } = useForm({
    resolver: zodResolver(
      baseMode === "edit" ? updateContactSchema : contactSchema,
    ),
    defaultValues: {
      // Auto-populate the parent org ID field when opened from an org page
      ...(parentIdField && parentId ? { [parentIdField]: parentId } : {}),
      // Also populate customer_id if provided separately (e.g. from a vendor's ContactPanel)
      ...(parentCustomerId ? { customer_id: parentCustomerId } : {}),
      // Pre-fill company from parent display name
      ...(parentCustomerName ? { company: parentCustomerName } : {}),
      refs: {
        tags: [],
        categories: [],
        keywords: [],
        depends_on: {},
        related_ids: [],
        links: {
          rep: [],
          item: [],
          email: [],
          order: [],
          phone: [],
          domain: [],
          contact: [],
          customer: [],
          document: [],
          address: [],
          manufacturer: [],
          project: [],
          vendor: [],
          // Seed the parent link so refs.links.<parent> = [parentId]
          ...(parentModel && parentId ? { [parentModel]: [parentId] } : {}),
        },
      },
    },
  });

  // Sync form when data loads
  useEffect(() => {
    if (!data) {
      // Add mode — don't call reset({}), which would wipe the parent-seeded
      // defaultValues (customer_id, company, refs.links.<parent>, etc.).
      // useForm already initialised with the correct defaults.
      return;
    }
    reset({
      ...data,
      customer_id: normalizeNumber(data.customer_id),
      rep_id: normalizeNumber(data.rep_id),
      vendor_id: normalizeNumber(data.vendor_id),
      employee_id: normalizeNumber(data.employee_id),
      manufacturer_id: normalizeNumber(data.manufacturer_id),
      other_id: normalizeNumber(data.other_id),
      refs: {
        ...data.refs,
        links: {
          ...data.refs?.links,
          email: (data.refs?.links?.email ?? []).map((e: any) => ({
            id: e.id ?? 0,
            name: e.name ?? "",
            address: e.address ?? "",
          })),
          phone: (data.refs?.links?.phone ?? []).map((p: any) => ({
            id: p.id ?? 0,
            name: p.name ?? "",
            number: p.number ?? "",
          })),
          address: (data.refs?.links?.address ?? []).map((a: any) => ({
            id: a.id ?? 0,
            name: a.name ?? "",
            address_line1: a.address_line1 ?? "",
            address_line2: a.address_line2 ?? "",
            city: a.city ?? "",
            state: a.state ?? "",
            postal_code: a.postal_code ?? "",
            country: a.country ?? "",
          })),
          domain: (data.refs?.links?.domain ?? []).map((d: any) => ({
            id: d.id ?? 0,
            name: d.name ?? "",
            domain: d.domain ?? "",
          })),
        },
      },
    });
  }, [data, reset]);

  // ---------------------------------------------------------------------------
  // Org Search Dialog State
  // ---------------------------------------------------------------------------

  /** Which FK field is being searched — null when dialog is closed */
  const [orgSearchField, setOrgSearchField] = useState<string | null>(null);

  /** Handle org selection from the search dialog */
  const handleOrgSelect = useCallback(
    (org: OrgSearchResult, fieldName: string) => {
      // When opened from toolbar ("other_id" with allowTypeSwitch), resolve
      // the actual FK field based on the selected org's type.
      let targetField = fieldName;
      if (fieldName === "other_id" && org.org_type) {
        const resolved = PARENT_MODEL_TO_ID_FIELD[org.org_type];
        if (resolved) targetField = resolved;
      }

      // 1. Set the scalar FK field value via react-hook-form's setValue
      setValue(targetField as any, org.id, {
        shouldDirty: true,
        shouldValidate: true,
      });

      // 2. Update refs.links.<org_type> with selected record data
      const orgType =
        org.org_type || ID_FIELD_TO_ORG_TYPE[targetField];
      if (orgType && orgType !== "organization") {
        setFetchedData((prev: any) => {
          const existing = prev || data;
          const currentLinks = existing?.refs?.links || {};
          const linkEntry = {
            id: org.id,
            display_name: org.display_name,
            ida: org.ida,
            email: org.email,
            phone: org.phone,
          };
          return {
            ...existing,
            refs: {
              ...(existing?.refs || {}),
              links: {
                ...currentLinks,
                [orgType]: [linkEntry],
              },
            },
          };
        });
      }

      setOrgSearchField(null);
    },
    [data, setValue],
  );

  // ---------------------------------------------------------------------------
  // Validation error handler — surfaces errors that handleSubmit swallows
  // ---------------------------------------------------------------------------

  const onValidationError = useCallback(
    (validationErrors: any) => {
      const messages = Object.entries(validationErrors)
        .map(
          ([field, err]: [string, any]) =>
            `${field}: ${err?.message || "invalid"}`,
        )
        .join(", ");
      console.warn("[ContactDetail] Validation errors:", validationErrors);
      dispatch(
        showToast({
          message: `Please fix: ${messages}`,
          type: "error",
        }),
      );
    },
    [dispatch],
  );

  // ---------------------------------------------------------------------------
  // Set Primary Communication Item
  // Saves the *_id field on the contact record (email_id, phone_id, etc.)
  // and also denormalizes the value into the scalar field (email, phone, etc.)
  // ---------------------------------------------------------------------------

  const handleSetPrimaryItem = useCallback(
    async (type: "email" | "phone" | "address" | "domain", id: number) => {
      if (!data?.id) return;

      const fieldMap: Record<string, string> = {
        email: "email_id",
        phone: "phone_id",
        address: "address_id",
        domain: "domain_id",
      };
      const idField = fieldMap[type];
      if (!idField) return;

      // Build a minimal update payload
      const payload: Record<string, any> = { id: data.id, [idField]: id };

      // Also denormalize the scalar value from the communications list
      if (type === "email") {
        const match = communications?.emails?.find((e: any) => e.id === id);
        if (match)
          payload.email = match.email || match.value || match.address || "";
      } else if (type === "phone") {
        const match = communications?.phones?.find((p: any) => p.id === id);
        if (match) payload.phone = match.number || match.value || "";
      } else if (type === "address") {
        const match = communications?.addresses?.find((a: any) => a.id === id);
        if (match) {
          payload.address_full =
            match.full ||
            [
              match.address1,
              [match.city, match.state, match.zip].filter(Boolean).join(", "),
              match.country,
            ]
              .filter(Boolean)
              .join(", ");
        }
      } else if (type === "domain") {
        const match = communications?.domains?.find((d: any) => d.id === id);
        if (match) payload.domain = match.domain || match.value || "";
      }

      try {
        await updateContact(payload as any);
        // Refresh the record from the server
        const res = await getRecord("contact", data.id);
        const rec = (res as any)?.record ?? res;
        if (rec) setFetchedData(rec);
        dispatch(
          showToast({ message: `Primary ${type} updated`, type: "success" }),
        );
      } catch (err) {
        console.error(`[ContactDetail.handleSetPrimaryItem] failed:`, err);
        dispatch(
          showToast({
            message: `Failed to set primary ${type}`,
            type: "error",
          }),
        );
      }
    },
    [data?.id, communications, dispatch, updateContact],
  );

  // ---------------------------------------------------------------------------
  // Form Submission
  // ---------------------------------------------------------------------------

  const onSubmit = useCallback(
    async (
      formData:
        | z.infer<typeof contactSchema>
        | z.infer<typeof updateContactSchema>,
    ) => {
      try {
        const mappedRefs = formData.refs
          ? mapRefsFormToApi(formData.refs)
          : undefined;

        console.log("[ContactDetail] Submitting:", {
          baseMode,
          formData,
          mappedRefs,
        });

        const basePayload = {
          email: formData.email,
          name_first: formData.name_first,
          name_last: formData.name_last,
          name_middle: formData.name_middle,
          name_prefix: formData.name_prefix,
          name_suffix: formData.name_suffix,
          company: formData.company,
          title: formData.title,
          department: formData.department,
          role: formData.role,
          is_active: formData.is_active,
          is_staff: formData.is_staff,
          // Disabled inputs are excluded by react-hook-form, so fall back to
          // parent-seeded values (query params) or fetched record values.
          customer_id:
            formData.customer_id ?? parentCustomerId ?? data?.customer_id,
          rep_id: formData.rep_id ?? data?.rep_id,
          vendor_id: formData.vendor_id ?? data?.vendor_id,
          employee_id: formData.employee_id ?? data?.employee_id,
          manufacturer_id: formData.manufacturer_id ?? data?.manufacturer_id,
          other_id: formData.other_id ?? data?.other_id,
          refs: mappedRefs,
        };

        const payload =
          baseMode === "add"
            ? {
                ...basePayload,
                password: (formData as any).password,
                // cnf_password is frontend-only validation — never send to backend
              }
            : basePayload;

        const res =
          baseMode === "add"
            ? await createContact(payload as CreateContactRequest)
            : await updateContact({
                ...payload,
                id: data?.id,
              } as UpdateContactRequest);

        if (res) {
          // ── Extract the server-assigned contact ID ──
          // The ID is only known after wc3 saves the record and returns it.
          const newContactId =
            (res as any)?.record?.id ?? res?.id ?? (res as any)?.data?.id;
          console.log(
            "[ContactDetail] Save response:",
            res,
            "→ newContactId:",
            newContactId,
          );

          // ── Sync parent org's refs.links.contact[] ──
          // When a new contact is created from an org detail page,
          // update the parent record to include this contact in its refs.
          if (
            baseMode === "add" &&
            parentModel &&
            parentId &&
            newContactId &&
            typeof newContactId === "number"
          ) {
            try {
              await saveRecord(parentModel, {
                id: parentId,
                refs: {
                  links: {
                    contact: [newContactId],
                  },
                },
              });
            } catch (linkErr) {
              console.error(
                `[ContactDetail] Failed to update ${parentModel} #${parentId} refs.links.contact:`,
                linkErr,
              );
              // Non-fatal — the contact was still created successfully
            }
          }

          dispatch(
            showToast({
              message: `Contact ${
                baseMode === "add" ? "created" : "updated"
              } successfully`,
              type: "success",
            }),
          );

          // Broadcast a custom event so panels (e.g. ContactPanel) can refresh.
          window.dispatchEvent(
            new CustomEvent("contact-saved", {
              detail: {
                contactId: newContactId ?? data?.id,
                parentModel,
                parentId,
              },
            }),
          );

          if (onSaved) onSaved();
        }
      } catch (error: unknown) {
        // Extract the backend error message from Axios response if available
        const axiosErr = error as any;
        const backendMsg =
          axiosErr?.response?.data?.error ||
          axiosErr?.response?.data?.message ||
          (typeof axiosErr?.response?.data === "string"
            ? axiosErr.response.data
            : null);
        const displayMsg = backendMsg
          ? `Save failed: ${backendMsg}`
          : error instanceof Error
          ? error.message
          : "Save failed";
        console.error("[ContactDetail] Save error:", {
          status: axiosErr?.response?.status,
          data: axiosErr?.response?.data,
          message: displayMsg,
        });
        dispatch(showToast({ message: displayMsg, type: "error" }));
      }
    },
    [
      baseMode,
      data?.id,
      dispatch,
      onSaved,
      parentModel,
      parentId,
      parentCustomerId,
      data?.customer_id,
      data?.rep_id,
      data?.vendor_id,
      data?.employee_id,
      data?.manufacturer_id,
      data?.other_id,
    ],
  );

  // ---------------------------------------------------------------------------
  // Nav Arrows (prev/next from list order)
  // ---------------------------------------------------------------------------

  const listOrder: number[] = useMemo(() => {
    try {
      const raw = localStorage.getItem("contact-list-order");
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }, []);

  const currentIndex = activeContactId
    ? listOrder.indexOf(activeContactId)
    : -1;
  const prevId = currentIndex > 0 ? listOrder[currentIndex - 1] : null;
  const nextId =
    currentIndex >= 0 && currentIndex < listOrder.length - 1
      ? listOrder[currentIndex + 1]
      : null;

  const openRecord = useCallback(
    (id: number) => {
      windowManager.ensureWindow(
        `/core/contact/detail/${id}`,
        `Contact #${id}`,
        { maximized: false },
      );
    },
    [windowManager],
  );

  // ---------------------------------------------------------------------------
  // Action Buttons (header)
  // ---------------------------------------------------------------------------

  const getActionButtons = () => {
    const buttons: React.ReactNode[] = [];

    if (effectiveMode === "view") {
      buttons.push(
        <CreateTransactionDropdown
          key="create-txn"
          customerId={data?.customer_id ?? parentCustomerId}
          customerName={data?.company ?? parentCustomerName}
          contactId={data?.id}
          contactName={displayName !== "New Contact" ? displayName : undefined}
          attention={data?.attention}
          email={data?.email}
          phone={data?.phone}
          ensureWindow={windowManager.ensureWindow}
        />,
      );
      buttons.push(
        <button
          key="edit"
          type="button"
          onClick={() => setEffectiveMode("edit")}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
          title="Edit Contact"
        >
          <FaEdit size={14} />
          Edit
        </button>,
      );
      if (onCancelInline) {
        buttons.push(
          <button
            key="close"
            type="button"
            onClick={onCancelInline}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600 rounded-lg transition-colors"
            title="Close"
          >
            Close
          </button>,
        );
      }
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

    return buttons;
  };

  // ---------------------------------------------------------------------------
  // Cancel handler
  // ---------------------------------------------------------------------------

  const handleCancel = useCallback(() => {
    if (onCancelInline) {
      onCancelInline();
    } else {
      setEffectiveMode("view");
      if (data) reset(data);
    }
  }, [onCancelInline, data, reset]);

  // ---------------------------------------------------------------------------
  // Derived display values
  // ---------------------------------------------------------------------------

  const displayName = data
    ? [data.name_first, data.name_last].filter(Boolean).join(" ") ||
      data.attention ||
      data.email ||
      `Contact #${data.id}`
    : "New Contact";

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (isLoading) return <RippleLoader />;

  return (
    <div className="h-full flex flex-col bg-white dark:bg-slate-900">
      {/* ─── HEADER ─── */}
      <div className="shrink-0 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 truncate">
              <span className="mr-2 px-1.5 py-0.5 text-[10px] font-mono font-normal tracking-wide uppercase bg-indigo-100 text-indigo-600 dark:bg-indigo-900/40 dark:text-indigo-300 rounded">
                Contact
              </span>
              {displayName}
              {activeContactId && (
                <span className="ml-2 text-sm font-normal text-slate-500 dark:text-slate-400">
                  #{activeContactId}
                </span>
              )}
            </h2>
            <div className="flex items-center gap-3 mt-1">
              <span
                className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${
                  data?.is_active !== false
                    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400"
                    : "bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400"
                }`}
              >
                {data?.is_active !== false ? "Active" : "Inactive"}
              </span>
              {data?.role && (
                <span className="text-sm text-slate-500 dark:text-slate-400 capitalize">
                  {data.role}
                </span>
              )}
              {data?.company && (
                <span className="text-sm text-slate-500 dark:text-slate-400">
                  {data.company}
                </span>
              )}
              {isEditing && isDirty && (
                <span className="px-3 py-1 text-xs font-medium text-amber-700 dark:text-amber-300 bg-amber-100 dark:bg-amber-900/30 rounded-full">
                  Unsaved changes
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 ml-4">
            {getActionButtons()}
          </div>
        </div>
      </div>

      {/* ─── TOOLBAR (edit/add only) ─── */}
      {isEditing && (
        <div className="sticky top-0 z-20 px-4 py-3 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm border-b border-slate-200 dark:border-slate-700 flex items-center gap-3">
          <TransactionToolbar
            transactionType="order"
            transactionId={data?.id}
            isDirty={isDirty}
            isSaving={isSubmitting}
            isEditing
            onSave={handleSubmit(onSubmit, onValidationError)}
            onSaveAndClose={handleSubmit(async (fd) => {
              await onSubmit(fd);
              handleCancel();
            }, onValidationError)}
            onCancel={handleCancel}
            canClone={false}
            canTransfer={false}
            canDelete={false}
            showTaskButton={false}
          />
          {/* ── Assign Org button ── */}
          <button
            type="button"
            onClick={() => setOrgSearchField("other_id")}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-blue-50 hover:text-blue-600 dark:hover:bg-blue-900/20 dark:hover:text-blue-400 border border-slate-200 dark:border-slate-700 rounded-lg transition-colors"
            title="Search and assign an organization"
          >
            <FaSearch size={12} />
            Assign&nbsp;Org
          </button>
        </div>
      )}

      {/* ─── BASIC INFORMATION (PERSISTENT) ─── */}
      <div className="shrink-0 px-4 py-3 border-b border-slate-200 dark:border-slate-700">
        {effectiveMode === "view" && data ? (
          /* ── Read-only view ── */
          <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3 flex items-center gap-2">
              <FaUser size={16} />
              Basic Information
            </h3>
            <dl
              className={`grid grid-cols-1 ${
                columnCount === 3 ? "lg:grid-cols-3" : "lg:grid-cols-2"
              } gap-x-6 gap-y-2 text-sm`}
            >
              <InfoRow label="name_first" value={data.name_first} />
              <InfoRow label="name_last" value={data.name_last} />
              <InfoRow label="email" value={data.email} />
              <InfoRow label="phone" value={data.phone} />
              <InfoRow label="address_full" value={data.address_full} />
              <InfoRow label="domain" value={data.domain} />
              <InfoRow label="attention" value={data.attention} />
              <InfoRow label="name_prefix" value={data.name_prefix} />
              <InfoRow label="name_middle" value={data.name_middle} />
              <InfoRow label="name_suffix" value={data.name_suffix} />
              <InfoRow label="company" value={data.company} />
              <InfoRow label="title" value={data.title} />
              <InfoRow label="department" value={data.department} />
              <InfoRow label="role" value={data.role} />
              <InfoRow label="customer_id" value={data.customer_id} />
              <InfoRow label="vendor_id" value={data.vendor_id} />
              <InfoRow label="rep_id" value={data.rep_id} />
              <InfoRow label="employee_id" value={data.employee_id} />
              <InfoRow label="manufacturer_id" value={data.manufacturer_id} />
              <InfoRow label="other_id" value={data.other_id} />
              <InfoRow
                label="is_active"
                value={
                  <span
                    className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full ${
                      data.is_active !== false
                        ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400"
                        : "bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400"
                    }`}
                  >
                    {data.is_active !== false ? "Yes" : "No"}
                  </span>
                }
              />
            </dl>
          </div>
        ) : (
          /* ── Editable form ── */
          <form
            id="contact-form"
            onSubmit={handleSubmit(onSubmit, onValidationError)}
          >
            <div
              className={`grid grid-cols-1 ${
                columnCount === 3 ? "lg:grid-cols-3" : "lg:grid-cols-2"
              } gap-x-6 gap-y-0`}
            >
              {shouldRenderField("name_first") && (
                <HorizontalField
                  label="name_first"
                  htmlFor="name_first"
                  required
                  error={errors.name_first?.message}
                >
                  <Input
                    type="text"
                    id="name_first"
                    placeholder="First name"
                    {...register("name_first")}
                    error={!!errors.name_first?.message}
                    disabled={isFieldDisabled("name_first")}
                  />
                </HorizontalField>
              )}

              {shouldRenderField("name_last") && (
                <HorizontalField
                  label="name_last"
                  htmlFor="name_last"
                  required
                  error={errors.name_last?.message}
                >
                  <Input
                    type="text"
                    id="name_last"
                    placeholder="Last name"
                    {...register("name_last")}
                    error={!!errors.name_last?.message}
                    disabled={isFieldDisabled("name_last")}
                  />
                </HorizontalField>
              )}

              {shouldRenderField("email") && (
                <HorizontalField
                  label="email"
                  htmlFor="email"
                  required
                  error={errors.email?.message}
                >
                  <Input
                    type="email"
                    id="email"
                    placeholder="Primary email"
                    {...register("email")}
                    error={!!errors.email?.message}
                    disabled={isFieldDisabled("email")}
                  />
                </HorizontalField>
              )}

              {shouldRenderField("phone") && (
                <HorizontalField label="phone" htmlFor="phone">
                  <Input
                    type="text"
                    id="phone"
                    placeholder="Primary phone"
                    {...register("phone" as any)}
                    disabled={isFieldDisabled("phone")}
                  />
                </HorizontalField>
              )}

              {shouldRenderField("address_full") && (
                <HorizontalField label="address_full" htmlFor="address_full">
                  <Input
                    type="text"
                    id="address_full"
                    placeholder="Full address"
                    {...register("address_full" as any)}
                    disabled={isFieldDisabled("address_full")}
                  />
                </HorizontalField>
              )}

              {shouldRenderField("domain") && (
                <HorizontalField label="domain" htmlFor="domain">
                  <Input
                    type="text"
                    id="domain"
                    placeholder="Primary domain"
                    {...register("domain" as any)}
                    disabled={isFieldDisabled("domain")}
                  />
                </HorizontalField>
              )}

              {shouldRenderField("attention") && (
                <HorizontalField label="attention" htmlFor="attention">
                  <Input
                    type="text"
                    id="attention"
                    placeholder="Attention / display name"
                    {...register("attention")}
                    disabled={isFieldDisabled("attention")}
                  />
                </HorizontalField>
              )}

              {shouldRenderField("name_prefix") && (
                <HorizontalField label="name_prefix" htmlFor="name_prefix">
                  <Input
                    type="text"
                    id="name_prefix"
                    placeholder="Mr., Ms., Dr."
                    {...register("name_prefix")}
                    disabled={isFieldDisabled("name_prefix")}
                  />
                </HorizontalField>
              )}

              {shouldRenderField("name_middle") && (
                <HorizontalField label="name_middle" htmlFor="name_middle">
                  <Input
                    type="text"
                    id="name_middle"
                    placeholder="Middle name"
                    {...register("name_middle")}
                    disabled={isFieldDisabled("name_middle")}
                  />
                </HorizontalField>
              )}

              {shouldRenderField("name_suffix") && (
                <HorizontalField label="name_suffix" htmlFor="name_suffix">
                  <Input
                    type="text"
                    id="name_suffix"
                    placeholder="Jr., Sr., III"
                    {...register("name_suffix")}
                    disabled={isFieldDisabled("name_suffix")}
                  />
                </HorizontalField>
              )}

              {shouldRenderField("company") && (
                <HorizontalField label="company" htmlFor="company">
                  <Input
                    type="text"
                    id="company"
                    placeholder="Company name"
                    {...register("company")}
                    disabled={isFieldDisabled("company")}
                  />
                </HorizontalField>
              )}

              {shouldRenderField("title") && (
                <HorizontalField label="title" htmlFor="title">
                  <Input
                    type="text"
                    id="title"
                    placeholder="Job title"
                    {...register("title")}
                    disabled={isFieldDisabled("title")}
                  />
                </HorizontalField>
              )}

              {shouldRenderField("department") && (
                <HorizontalField label="department" htmlFor="department">
                  <Input
                    type="text"
                    id="department"
                    placeholder="Department"
                    {...register("department")}
                    disabled={isFieldDisabled("department")}
                  />
                </HorizontalField>
              )}

              {shouldRenderField("role") && (
                <HorizontalField label="role" htmlFor="role">
                  <Controller
                    name="role"
                    control={control}
                    render={({ field }) => (
                      <DropDown
                        id="role"
                        options={ROLE_OPTIONS}
                        value={field.value || "user"}
                        onChange={field.onChange}
                        disabled={isFieldDisabled("role")}
                      />
                    )}
                  />
                </HorizontalField>
              )}

              {/* System IDs */}
              {/* ── Org Association ID Fields with Search ── */}
              {(["customer_id", "vendor_id", "rep_id", "employee_id", "manufacturer_id", "other_id"] as const).map(
                (fieldName) =>
                  shouldRenderField(fieldName) && (
                    <HorizontalField
                      key={fieldName}
                      label={fieldName}
                      htmlFor={fieldName}
                    >
                      <div className="flex items-center gap-1.5">
                        <Input
                          type="number"
                          id={fieldName}
                          placeholder={`${fieldName.replace("_id", "").replace(/^./, (c) => c.toUpperCase())} ID`}
                          {...register(fieldName as any, {
                            valueAsNumber: true,
                          })}
                          disabled={isFieldDisabled(fieldName)}
                        />
                        {effectiveMode !== "view" && (
                          <button
                            type="button"
                            onClick={() => setOrgSearchField(fieldName)}
                            className="shrink-0 p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                            title={`Search ${fieldName.replace("_id", "")}s`}
                          >
                            <FaSearch size={13} />
                          </button>
                        )}
                      </div>
                    </HorizontalField>
                  ),
              )}

              {/* Passwords — add mode only */}
              {effectiveMode === "add" && shouldRenderField("password") && (
                <HorizontalField
                  label="password"
                  htmlFor="password"
                  required
                  error={(errors as any).password?.message}
                >
                  <Input
                    type="password"
                    id="password"
                    placeholder="Password"
                    {...register("password" as any)}
                    error={!!(errors as any).password?.message}
                    disabled={isFieldDisabled("password")}
                  />
                </HorizontalField>
              )}

              {effectiveMode === "add" && shouldRenderField("cnf_password") && (
                <HorizontalField
                  label="cnf_password"
                  htmlFor="cnf_password"
                  required
                  error={(errors as any).cnf_password?.message}
                >
                  <Input
                    type="password"
                    id="cnf_password"
                    placeholder="Confirm password"
                    {...register("cnf_password" as any)}
                    error={!!(errors as any).cnf_password?.message}
                    disabled={isFieldDisabled("cnf_password")}
                  />
                </HorizontalField>
              )}

              {/* Checkboxes */}
              <div className="flex gap-6 py-2 col-span-full">
                {shouldRenderField("is_active") && (
                  <Controller
                    name="is_active"
                    control={control}
                    render={({ field }) => (
                      <Checkbox
                        label="Active"
                        checked={field.value ?? true}
                        onChange={field.onChange}
                        disabled={isFieldDisabled("is_active")}
                      />
                    )}
                  />
                )}
                {shouldRenderField("is_staff") && (
                  <Controller
                    name="is_staff"
                    control={control}
                    render={({ field }) => (
                      <Checkbox
                        label="Staff"
                        checked={field.value ?? false}
                        onChange={field.onChange}
                        disabled={isFieldDisabled("is_staff")}
                      />
                    )}
                  />
                )}
              </div>
            </div>
          </form>
        )}
      </div>

      {/* ─── TAB NAVIGATION ─── */}
      {activeContactId && data?.id && (
        <>
          <DetailTabs
            entityType="contact"
            activeTab={activeTab}
            onTabChange={setActiveTab}
            standardTabs={["actions", "comments", "documents", "raw"]}
            additionalTabs={additionalTabs}
            badges={tabBadges}
            showColumnSelector
            columnCount={columnCount}
            onColumnCountChange={setColumnCount}
          />

          {/* ─── TAB CONTENT (scrollable) ─── */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-4">
              {activeTab === "actions" && (
                <ActionsPanel
                  entityType="contact"
                  entityId={data.id}
                  data={Array.isArray(data.actions) ? data.actions : undefined}
                  actionIds={
                    data.actions &&
                    typeof data.actions === "object" &&
                    "ids" in data.actions
                      ? (data.actions as { ids?: number[] }).ids
                      : undefined
                  }
                  viewMode="table"
                  isEditing={isEditing}
                  onChange={(actions) =>
                    setFetchedData((prev: any) => ({
                      ...(prev || data),
                      actions,
                    }))
                  }
                  onActionIdsChange={(ids) =>
                    setFetchedData((prev: any) => ({
                      ...(prev || data),
                      actions: { ids },
                    }))
                  }
                  onSave={async (actions) => {
                    try {
                      await updateContact({ id: data.id, actions } as any);
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

              {activeTab === "comments" && (
                <CommentsPanel
                  entityType="contact"
                  entityId={data.id}
                  comments={data.comments}
                  isEditing={isEditing}
                  onChange={(comments) =>
                    setFetchedData((prev: any) => ({
                      ...(prev || data),
                      comments,
                    }))
                  }
                  onSave={async (comments) => {
                    try {
                      await updateContact({
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
                  currentUser={currentUserName}
                  currentUserId={currentUserId}
                />
              )}

              {activeTab === "communications" && activeContactId && (
                <CommunicationsPanel
                  entityType="contact"
                  entityId={activeContactId}
                  contactId={activeContactId}
                  data={communications}
                  onChange={(comms) => {
                    setCommunications(comms);
                    // Also sync back to refs.links AND communications so useEffect doesn't overwrite
                    setFetchedData((prev: any) => ({
                      ...(prev || data),
                      communications: {
                        ...(prev?.communications || data?.communications || {}),
                        emails: comms.emails || [],
                        phones: comms.phones || [],
                        addresses: comms.addresses || [],
                        domains: comms.domains || [],
                      },
                      refs: {
                        ...(prev?.refs || data?.refs || {}),
                        links: {
                          ...(prev?.refs?.links || data?.refs?.links || {}),
                          email: comms.emails || [],
                          phone: comms.phones || [],
                          location: comms.addresses || [],
                          domain: comms.domains || [],
                        },
                      },
                    }));
                  }}
                  primaryEmailId={data?.email_id}
                  primaryPhoneId={data?.phone_id}
                  primaryAddressId={data?.address_id}
                  primaryDomainId={data?.domain_id}
                  onSetPrimaryItem={handleSetPrimaryItem}
                />
              )}

              {activeTab === "documents" && (
                <DocumentsPanel
                  parent_model="contact"
                  parentId={data.id}
                  data={data?.refs?.links?.document}
                  isEditing={isEditing}
                />
              )}

              {activeTab === "history" && (
                <MetadataPanel
                  entityType="contact"
                  entityId={data.id}
                  data={data?.metadata}
                />
              )}

              {activeTab === "metadata" && (
                <MetadataPanel
                  entityType="contact"
                  entityId={data.id}
                  data={data?.metadata}
                />
              )}

              {activeTab === "prefs" && (
                <PrefsPanel
                  entityType="contact"
                  entityId={data.id}
                  data={data?.prefs}
                />
              )}

              {activeTab === "raw" && (
                <RawDataPanel
                  entityType="contact"
                  entityId={data.id}
                  data={data}
                />
              )}

              {activeTab === "refs" && (
                <RefsPanel
                  entityType="contact"
                  entityId={data.id}
                  data={data?.refs}
                  onChange={(refs: any) =>
                    setFetchedData((prev: any) => ({
                      ...(prev || data),
                      refs,
                    }))
                  }
                />
              )}
            </div>
          </div>
        </>
      )}

      {/* ─── Org Search Dialog ─── */}
      <OrgSearchDialog
        open={!!orgSearchField}
        orgType={
          orgSearchField
            ? ID_FIELD_TO_ORG_TYPE[orgSearchField] || "organization"
            : "customer"
        }
        allowTypeSwitch={orgSearchField === "other_id"}
        onSelect={(org) => {
          if (orgSearchField) handleOrgSelect(org, orgSearchField);
        }}
        onClose={() => setOrgSearchField(null)}
      />
    </div>
  );
}
