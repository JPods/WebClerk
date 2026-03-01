/**
 * ContactDetail2.tsx
 *
 * Contact Detail page with ScalarCard / JsonCard / BaseModelCards pattern.
 * Identical to ContactDetail.tsx except the view-mode Basic Information
 * section uses the shared collapsible-card components so every scalar and
 * JSONB first-level field is surfaced, clustered by use.
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
import { createPortal } from "react-dom";
import { Controller, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

// UI primitives
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import DropDown from "@/components/form/input/DropDown";
import Checkbox from "@/components/form/input/Checkbox";
import { DevBadge } from "@/components/common/DevBadge";
import { DetailFeatureBadge } from "@/components/common/DetailFeatureBadge";
import RippleLoader from "@/components/common/RippleLoader";

// API
import { deleteRecord, getRecord, getRecords, saveRecord } from "@/api/wcapi";
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
import { useInflightSaves } from "@/hooks/useInflightSaves";
import { useAutoSaveContact } from "../hooks/useAutoSaveContact";

// Toolbar
import TransactionToolbar from "@/apps/common/components/TransactionToolbar";

// Tab navigation
import {
  DetailTabs,
  useDetailTabs,
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
  FaSpinner,
  FaTrash,
  FaTimes,
  FaAddressBook,
  FaBuilding,
} from "react-icons/fa";
import {
  History,
  Link,
  Phone,
  SlidersHorizontal,
  User2,
  Mail,
  Building2,
  ShieldCheck,
} from "lucide-react";

// Shared detail card components
import {
  ScalarCard,
  JsonCard,
  BaseModelCards,
} from "@/apps/common/components/detail";

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
import {
  CommunicationAddEditModal,
  type CommunicationModalType,
  type CommunicationModalData,
} from "@/apps/common/components/panels/CommunicationAddEditModal";

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

type CommType = CommunicationModalType;

function commTypeToModelName(type: CommType): string {
  return type;
}

function commTypeToContactIdField(
  type: CommType,
): "email_id" | "phone_id" | "address_id" | "domain_id" {
  if (type === "email") return "email_id";
  if (type === "phone") return "phone_id";
  if (type === "address") return "address_id";
  return "domain_id";
}

function commTypeToContactScalarField(
  type: CommType,
): "email" | "phone" | "address_full" | "domain" {
  if (type === "email") return "email";
  if (type === "phone") return "phone";
  if (type === "address") return "address_full";
  return "domain";
}

function getCommDisplayValue(type: CommType, item: any): string {
  if (!item) return "";
  if (type === "email") return item.email || item.address || item.value || "";
  if (type === "phone") return item.number || item.value || item.format || "";
  if (type === "domain") return item.domain || item.value || item.path || "";
  // address
  return (
    item.full ||
    [
      item.address1,
      [item.city, item.state, item.zip].filter(Boolean).join(", "),
      item.country,
    ]
      .filter(Boolean)
      .join(", ")
  );
}

function mapModalToCommModelPayload(
  type: CommType,
  formData: CommunicationModalData,
  contactId: number,
) {
  if (type === "email") {
    const email = String((formData as any).email || "").trim();
    return {
      ...(formData.id ? { id: formData.id } : {}),
      contact_id: contactId,
      email,
      name: (formData as any).name || "",
      attention: (formData as any).attention || "",
      is_primary: !!(formData as any).is_primary,
    };
  }
  if (type === "phone") {
    const number = String((formData as any).number || "").trim();
    return {
      ...(formData.id ? { id: formData.id } : {}),
      contact_id: contactId,
      number,
      name: (formData as any).name || "",
      attention: (formData as any).attention || "",
    };
  }
  if (type === "domain") {
    const path = String(
      (formData as any).domain || (formData as any).path || "",
    ).trim();
    return {
      ...(formData.id ? { id: formData.id } : {}),
      contact_id: contactId,
      path,
      type: (formData as any).type || "",
      status: (formData as any).verified
        ? "active"
        : (formData as any).status || "active",
    };
  }

  // address
  const address1 = String((formData as any).address1 || "").trim();
  return {
    ...(formData.id ? { id: formData.id } : {}),
    contact_id: contactId,
    address1,
    address2: (formData as any).address2 || "",
    city: (formData as any).city || "",
    state: (formData as any).state || "",
    zip: (formData as any).zip || "",
    country: (formData as any).country || "",
  };
}

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
        className="w-32 shrink-0 text-left text-sm font-medium text-slate-600 dark:text-slate-400"
      >
        {label} :{required && <span className="text-red-500 ml-0.5">*</span>}
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
    <dt className="w-32 shrink-0 text-left text-sm text-slate-500 dark:text-slate-400">
      {label} :
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

const normalizeContactFkFields = (record: any) => {
  if (!record || typeof record !== "object") return record;
  const out = { ...record };
  const pickId = (v: any) => {
    if (v == null) return undefined;
    if (typeof v === "number" && Number.isFinite(v)) return v;
    if (typeof v === "string" && v.trim() && !Number.isNaN(Number(v)))
      return Number(v);
    if (typeof v === "object") {
      const nested = (v as any).id;
      if (typeof nested === "number" && Number.isFinite(nested)) return nested;
      if (
        typeof nested === "string" &&
        nested.trim() &&
        !Number.isNaN(Number(nested))
      )
        return Number(nested);
    }
    return undefined;
  };

  // WCAPI often returns FK ids under the field name (customer, rep, ...) not the attname (customer_id).
  if (out.customer_id == null) out.customer_id = pickId(out.customer);
  if (out.rep_id == null) out.rep_id = pickId(out.rep);
  if (out.vendor_id == null) out.vendor_id = pickId(out.vendor);
  if (out.employee_id == null) out.employee_id = pickId(out.employee);
  if (out.manufacturer_id == null)
    out.manufacturer_id = pickId(out.manufacturer);

  return out;
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

  const parseRecordId = (value: unknown): number | null => {
    if (typeof value === "number") {
      return Number.isFinite(value) ? value : null;
    }
    if (typeof value === "string") {
      const parsed = Number.parseInt(value, 10);
      return Number.isFinite(parsed) ? parsed : null;
    }
    return null;
  };

  const contactIdFromUrl = parseRecordId(urlId);

  // ---------------------------------------------------------------------------
  // Mode
  // ---------------------------------------------------------------------------

  // recordMode controls validation + save behavior.
  // Detail pages always open in edit mode — switch to read-only only when needed.
  const recordMode: "add" | "edit" = useMemo(() => {
    if (modeProp === "add") return "add";
    if (contactIdFromUrl != null) return "edit";
    // With no ID, default to add. routeState.mode may be set by navigations,
    // but it shouldn't force edit-mode for a non-existent record.
    return "add";
  }, [modeProp, contactIdFromUrl]);

  const initialUiMode: "add" | "edit" | "view" = useMemo(() => {
    return recordMode === "add" ? "add" : "edit";
  }, [recordMode]);

  const [effectiveMode, setEffectiveMode] = useState<"add" | "edit" | "view">(
    initialUiMode,
  );

  useEffect(() => {
    setEffectiveMode(initialUiMode);
  }, [initialUiMode]);

  const isEditing = effectiveMode === "edit" || effectiveMode === "add";

  // ---------------------------------------------------------------------------
  // Data Loading
  // ---------------------------------------------------------------------------

  const [fetchedData, setFetchedData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const initialData = dataProp || routeState.data || null;
  const data = normalizeContactFkFields(fetchedData || initialData);
  const activeContactId = data?.id || contactIdFromUrl || null;

  // ---------------------------------------------------------------------------
  // In-flight saves tracker (background child-record saves)
  // ---------------------------------------------------------------------------

  const { track: _track, inflightCount, waitForAll } = useInflightSaves();

  useEffect(() => {
    if (contactIdFromUrl != null && contactIdFromUrl !== fetchedData?.id) {
      if (initialData?.id === contactIdFromUrl) return;
      setIsLoading(true);
      getRecord("contact", contactIdFromUrl)
        .then((result) =>
          setFetchedData(normalizeContactFkFields(result?.record || result)),
        )
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
      data?.refs?.links?.address,
    ),
    domains: getCommsArray(
      data?.communications?.domains,
      data?.refs?.links?.domain,
    ),
  });

  useEffect(() => {
    if (data?.communications || data?.refs?.links) {
      const next = {
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
          data.refs?.links?.address,
        ),
        domains: getCommsArray(
          data.communications?.domains,
          data.refs?.links?.domain,
        ),
      };

      const same = JSON.stringify(communications) === JSON.stringify(next);
      if (!same) setCommunications(next);
    }
  }, [data?.communications, data?.refs?.links, communications]);

  // setValue is initialized by useForm later in this component.
  // We store it in a ref so earlier callbacks (defined before useForm) don't hit TDZ.
  const formSetValueRef = useRef<null | ((...args: any[]) => void)>(null);
  const formGetValuesRef = useRef<null | ((name: string) => any)>(null);
  const formGetAllValuesRef = useRef<null | (() => any)>(null);
  // Remember last reset id to avoid repeated resets causing render loops
  const lastResetIdRef = useRef<number | null | undefined>(undefined);

  // Prefer the authoritative communications tables when we have a saved contact id.
  // This makes the Basic Info pickers and the Comms tab reflect real records.
  useEffect(() => {
    if (!activeContactId) return;

    let cancelled = false;
    (async () => {
      try {
        const [emailRes, phoneRes, addressRes, domainRes] = await Promise.all([
          getRecords("email", { contact: activeContactId, limit: 200 }),
          getRecords("phone", { contact: activeContactId, limit: 200 }),
          getRecords("address", { contact: activeContactId, limit: 200 }),
          getRecords("domain", { contact: activeContactId, limit: 200 }),
        ]);

        const rawEmails = (emailRes as any)?.results ?? [];
        const emails = rawEmails
          .filter((r: any) => {
            const cid = Number(r?.contact ?? r?.contact_id);
            return !Number.isFinite(cid) || cid === activeContactId;
          })
          .map((r: any) => ({
            id: r.id,
            name: r.name || "",
            type: r.type || "",
            email: r.email,
            address: r.email,
            value: r.email,
            is_primary: !!r.is_primary,
            is_verified: !!r.is_verified,
          }));

        const rawPhones = (phoneRes as any)?.results ?? [];
        const phones = rawPhones
          .filter((r: any) => {
            const cid = Number(r?.contact ?? r?.contact_id);
            return !Number.isFinite(cid) || cid === activeContactId;
          })
          .map((r: any) => ({
            id: r.id,
            name: r.name || "",
            number: r.number,
            value: r.number,
            format: r.format || "",
            country_code: r.country_code || "",
          }));

        const rawAddresses = (addressRes as any)?.results ?? [];
        const addresses = rawAddresses
          .filter((r: any) => {
            const cid = Number(r?.contact ?? r?.contact_id);
            return !Number.isFinite(cid) || cid === activeContactId;
          })
          .map((r: any) => ({
            id: r.id,
            name: r.address_type || "",
            address1: r.address1,
            address2: r.address2,
            city: r.city,
            state: r.state,
            zip: r.zip,
            country: r.country,
            full: r.full,
          }));

        const rawDomains = (domainRes as any)?.results ?? [];
        const domains = rawDomains
          .filter((r: any) => {
            const cid = Number(r?.contact ?? r?.contact_id);
            return !Number.isFinite(cid) || cid === activeContactId;
          })
          .map((r: any) => ({
            id: r.id,
            name: r.type || "",
            domain: r.path,
            path: r.path,
            value: r.path,
            status: r.status,
          }));

        if (!cancelled) {
          setCommunications({ emails, phones, addresses, domains });
        }
      } catch (e) {
        // If tables are empty or endpoint errors, fall back to refs-based comms.
        console.warn("[ContactDetail] communications model fetch failed:", e);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [activeContactId]);

  // ---------------------------------------------------------------------------
  // Basic Info communications pickers (email/phone/address/domain)
  // - Select from existing linked comm records (searchable)
  // - Add new record (creates communication model row via wcapi)
  // - Set as primary by updating contact.{*_id} + scalar field without refetching
  //   (avoids wiping other unsaved form edits)
  // ---------------------------------------------------------------------------

  const [commSelectState, setCommSelectState] = useState<{
    open: boolean;
    type: CommType;
  }>({ open: false, type: "email" });
  const [commSelectQuery, setCommSelectQuery] = useState<string>("");
  const [commGlobalResults, setCommGlobalResults] = useState<any[]>([]);
  const [commGlobalLoading, setCommGlobalLoading] = useState(false);

  const [commModalState, setCommModalState] = useState<{
    open: boolean;
    type: CommType;
    data?: CommunicationModalData;
  }>({ open: false, type: "email" });

  const [commSaving, setCommSaving] = useState(false);

  // ---------------------------------------------------------------------------
  // Auto-save contact on first child-record attempt
  // ---------------------------------------------------------------------------

  const handleContactCreated = useCallback(
    (newId: number, res: any) => {
      const record = res?.record ?? res;
      setFetchedData(normalizeContactFkFields(record));
      setEffectiveMode("edit");

      // Broadcast so parent panels can refresh
      window.dispatchEvent(
        new CustomEvent("contact-saved", {
          detail: { contactId: newId, parentModel, parentId },
        }),
      );

      // Sync parent org's refs.links.contact[]
      if (parentModel && parentId) {
        saveRecord(parentModel, {
          id: parentId,
          refs: { links: { contact: [newId] } },
        }).catch((err: any) =>
          console.error(
            `[ContactDetail2] Failed to link contact to ${parentModel} #${parentId}:`,
            err,
          ),
        );
      }
    },
    [parentModel, parentId],
  );

  const { ensureContactId, autoSaveInProgress } = useAutoSaveContact({
    recordMode,
    activeContactId,
    getValues: () => formGetAllValuesRef.current?.() ?? {},
    parentModel,
    parentId,
    parentCustomerId,
    parentCustomerName,
    onContactCreated: handleContactCreated,
  });

  const openCommSelect = async (type: CommType) => {
    const cid = await ensureContactId();
    if (!cid) return; // auto-save failed or required fields missing
    setCommSelectQuery("");
    setCommSelectState({ open: true, type });
  };

  const closeCommSelect = () =>
    setCommSelectState((s) => ({ ...s, open: false }));

  // Global search results for selector dialog (shows all records; not limited to this contact)
  useEffect(() => {
    if (!commSelectState.open) return;

    let cancelled = false;
    (async () => {
      setCommGlobalLoading(true);
      try {
        const modelName = commTypeToModelName(commSelectState.type);
        const q = commSelectQuery.trim();
        const params: Record<string, any> = { limit: 200 };
        if (q) {
          params.search = q;
          params.q = q;
        }
        const res: any = await getRecords(modelName, params);
        const rows: any[] = res?.results || [];
        if (!cancelled) setCommGlobalResults(rows);
      } catch (e) {
        if (!cancelled) setCommGlobalResults([]);
      } finally {
        if (!cancelled) setCommGlobalLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [commSelectState.open, commSelectState.type, commSelectQuery]);

  const filteredCommItems = useMemo(() => {
    const q = commSelectQuery.trim().toLowerCase();
    if (!q) return commGlobalResults;
    return commGlobalResults.filter((item: any) => {
      const value = getCommDisplayValue(
        commSelectState.type,
        item,
      ).toLowerCase();
      const label = String(item?.name || item?.type || "").toLowerCase();
      return (
        value.includes(q) ||
        label.includes(q) ||
        String(item?.id || "").includes(q)
      );
    });
  }, [commGlobalResults, commSelectQuery, commSelectState.type]);

  const copyCommToThisContact = useCallback(
    async (type: CommType, row: any): Promise<number> => {
      if (!activeContactId) throw new Error("No active contact id");
      const modelName = commTypeToModelName(type);
      const existingContact = Number(row?.contact ?? row?.contact_id);

      // If record is already attached to this contact, reuse it.
      if (
        Number.isFinite(existingContact) &&
        existingContact === activeContactId &&
        row?.id
      ) {
        return Number(row.id);
      }

      // Otherwise, create a new record attached to this contact (safer than re-assigning ownership)
      let createPayload: Record<string, any> = { contact_id: activeContactId };
      if (type === "email") {
        createPayload = {
          ...createPayload,
          email: row?.email || row?.address || row?.value || "",
          name: row?.name || "",
          attention: row?.attention || "",
          type: row?.type || "",
          is_primary: false,
        };
      } else if (type === "phone") {
        createPayload = {
          ...createPayload,
          number: row?.number || row?.value || "",
          name: row?.name || "",
          attention: row?.attention || "",
          country_code: row?.country_code || "",
          format: row?.format || "",
        };
      } else if (type === "domain") {
        createPayload = {
          ...createPayload,
          path: row?.path || row?.domain || row?.value || "",
          type: row?.type || "",
          status: row?.status || "active",
          comment: row?.comment || "",
        };
      } else if (type === "address") {
        createPayload = {
          ...createPayload,
          address1: row?.address1 || "",
          address2: row?.address2 || "",
          city: row?.city || "",
          state: row?.state || "",
          zip: row?.zip || "",
          country: row?.country || "",
          full: row?.full || "",
          address_type: row?.address_type || row?.name || "",
        };
      }

      const res: any = await saveRecord(modelName, createPayload);
      const record = res?.record ?? res;
      const newId = Number(record?.id ?? res?.id);
      if (!Number.isFinite(newId) || newId <= 0) {
        throw new Error("Failed to link communication record");
      }
      return newId;
    },
    [activeContactId],
  );

  const refreshCommType = useCallback(
    async (type: CommType) => {
      if (!activeContactId) return;
      try {
        const modelName = commTypeToModelName(type);
        const res: any = await getRecords(modelName, {
          contact: activeContactId,
          limit: 200,
        });
        const rows: any[] = (res?.results || []).filter((r: any) => {
          const cid = Number(r?.contact ?? r?.contact_id);
          return !Number.isFinite(cid) || cid === activeContactId;
        });

        if (type === "email") {
          const emails = rows.map((r) => ({
            id: r.id,
            name: r.name || "",
            type: r.type || "",
            email: r.email,
            address: r.email,
            value: r.email,
            is_primary: !!r.is_primary,
            is_verified: !!r.is_verified,
          }));
          setCommunications((prev) => ({ ...(prev || {}), emails }));
        } else if (type === "phone") {
          const phones = rows.map((r) => ({
            id: r.id,
            name: r.name || "",
            number: r.number,
            value: r.number,
            format: r.format || "",
            country_code: r.country_code || "",
          }));
          setCommunications((prev) => ({ ...(prev || {}), phones }));
        } else if (type === "address") {
          const addresses = rows.map((r) => ({
            id: r.id,
            name: r.address_type || "",
            address1: r.address1,
            address2: r.address2,
            city: r.city,
            state: r.state,
            zip: r.zip,
            country: r.country,
            full: r.full,
          }));
          setCommunications((prev) => ({ ...(prev || {}), addresses }));
        } else if (type === "domain") {
          const domains = rows.map((r) => ({
            id: r.id,
            name: r.type || "",
            domain: r.path,
            path: r.path,
            value: r.path,
            status: r.status,
            is_primary: data?.domain_id ? r.id === data.domain_id : false,
            verified: r.status
              ? String(r.status).toLowerCase() === "active"
              : false,
          }));
          setCommunications((prev) => ({ ...(prev || {}), domains }));
        }
      } catch (e) {
        console.warn("[ContactDetail] refreshCommType failed:", e);
      }
    },
    [activeContactId, data?.domain_id],
  );

  const setPrimaryCommWithoutRefetch = useCallback(
    async (type: CommType, commId: number, displayValue: string) => {
      if (!activeContactId) return;
      const idField = commTypeToContactIdField(type);
      const scalarField = commTypeToContactScalarField(type);

      const payload: Record<string, any> = {
        id: activeContactId,
        mode: "update",
        [idField]: commId,
      };

      // Do NOT blindly overwrite Contact.email (login + unique).
      // Only mirror the selected email into the scalar field when it matches the current form value
      // (or when current is blank). This prevents 400s from uniqueness/validation.
      if (type === "email") {
        const currentEmailRaw =
          (formGetValuesRef.current?.("email") as string | undefined) ??
          (data?.email as string | undefined) ??
          "";
        const currentEmail = String(currentEmailRaw || "")
          .trim()
          .toLowerCase();
        const selectedEmail = String(displayValue || "")
          .trim()
          .toLowerCase();
        if (!currentEmail || currentEmail === selectedEmail) {
          payload[scalarField] = displayValue;
        }
      } else {
        payload[scalarField] = displayValue;
      }
      try {
        await updateContact(payload as any);
        if (payload[scalarField] !== undefined) {
          formSetValueRef.current?.(scalarField as any, displayValue, {
            shouldDirty: true,
          });
        }
      } catch (err: any) {
        const details = err?.response?.data || err;
        console.error("[ContactDetail] Failed to set primary comm:", {
          type,
          commId,
          scalarField,
          idField,
          payload,
          details,
        });
        const message =
          details?.message ||
          details?.detail ||
          details?.error?.details ||
          err?.message ||
          "Failed to update contact";
        dispatch(showToast({ message: String(message), type: "error" }));
        throw err;
      }
    },
    [activeContactId, updateContact, dispatch],
  );

  const handleSelectComm = useCallback(
    async (item: any) => {
      const type = commSelectState.type;
      const cid = await ensureContactId();
      if (!cid) return;

      setCommSaving(true);
      try {
        const linkedId = await copyCommToThisContact(type, item);
        await refreshCommType(type);
        const displayValue = getCommDisplayValue(type, item);
        await setPrimaryCommWithoutRefetch(type, linkedId, displayValue);
        closeCommSelect();
      } catch {
        // toast/log already emitted in setPrimaryCommWithoutRefetch
      } finally {
        setCommSaving(false);
      }
    },
    [
      ensureContactId,
      commSelectState.type,
      copyCommToThisContact,
      refreshCommType,
      setPrimaryCommWithoutRefetch,
    ],
  );

  const handleAddNewComm = useCallback((type: CommType) => {
    setCommModalState({ open: true, type, data: undefined });
  }, []);

  const handleSaveNewComm = useCallback(
    async (payload: CommunicationModalData) => {
      const type = commModalState.type;
      const contactId = await ensureContactId();
      if (!contactId) return;

      setCommSaving(true);
      try {
        const modelName = commTypeToModelName(type);
        const modelPayload = mapModalToCommModelPayload(
          type,
          payload,
          contactId,
        );

        console.log("[ContactDetail2] Phase 1: Saving communication record:", {
          type: modelName,
          contactId,
          payload: modelPayload,
        });

        // ── Step 1: Create/Update the communication record
        const res: any = await saveRecord(modelName, modelPayload);

        console.log("[ContactDetail2] Phase 2: saveRecord response:", {
          status: res?.status,
          statusCode: res?.statusCode,
          hasRecord: !!res?.record,
          hasId: res?.id || (res?.record && res.record.id),
          fullResponse: res,
        });

        const record = res?.record ?? res;
        const newId = Number(record?.id ?? res?.id);

        if (!Number.isFinite(newId) || newId <= 0) {
          throw new Error(
            `Failed to create ${modelName} record. Response: ${JSON.stringify({
              newId,
              record,
              resId: res?.id,
            })}`,
          );
        }

        console.log(
          `[ContactDetail2] Phase 3: Successfully created ${modelName} record #${newId}`,
        );

        // ── Step 2: Normalize the created record for refs.links
        let refsLinkItem: any = {
          id: newId,
          ...(record || {}),
        };

        if (type === "email") {
          refsLinkItem = {
            id: newId,
            email: record?.email || record?.address || "",
            name: record?.name || "",
            type: record?.type || "",
            is_primary: record?.is_primary || true,
            is_verified: record?.is_verified || false,
          };
        } else if (type === "phone") {
          refsLinkItem = {
            id: newId,
            number: record?.number || "",
            name: record?.name || "",
            country_code: record?.country_code || "",
            format: record?.format || "",
          };
        } else if (type === "address") {
          refsLinkItem = {
            id: newId,
            address1: record?.address1 || "",
            address2: record?.address2 || "",
            city: record?.city || "",
            state: record?.state || "",
            zip: record?.zip || "",
            country: record?.country || "",
            full: record?.full || "",
          };
        } else if (type === "domain") {
          refsLinkItem = {
            id: newId,
            domain: record?.domain || record?.path || "",
            path: record?.path || record?.domain || "",
            type: record?.type || "website",
            status: record?.status || "active",
          };
        }

        console.log("[ContactDetail2] Phase 4: Normalized refs.links item:", {
          type,
          refsLinkItem,
        });

        // ── Step 3: Update contact's refs.links[type] array
        const linkFieldName = `${type}s`; // e.g., "emails", "phones", "addresses", "domains"
        const currentLinks =
          communications?.[linkFieldName as keyof CommunicationsData] || [];

        // Add new item to the array (in edit mode, replace existing item with same ID)
        const updatedLinks =
          payload?.id && payload.id > 0
            ? currentLinks.map((item: any) =>
                item.id === payload.id ? refsLinkItem : item,
              )
            : [...currentLinks, refsLinkItem];

        console.log("[ContactDetail2] Phase 5: Updating contact.refs.links:", {
          type,
          linkFieldName,
          currentCount: currentLinks.length,
          newCount: updatedLinks.length,
          updatedLinks,
        });

        // Save refs.links update to contact
        await saveRecord("contact", {
          id: contactId,
          mode: "update",
          refs: {
            mode: "update",
            value: {
              links: {
                [type]: updatedLinks,
              },
            },
          },
        });

        console.log(
          `[ContactDetail2] Phase 6: Successfully updated contact.refs.links.${type}`,
        );

        // ── Step 4: Refresh the communications list
        await refreshCommType(type);

        // ── Step 5: Update the form state to reflect the new primary
        const displayValue = getCommDisplayValue(type, refsLinkItem);

        console.log("[ContactDetail2] Phase 7: Setting primary comm:", {
          type,
          newId,
          displayValue,
        });

        // Update the form's scalar field (email, phone, etc.)
        formSetValueRef.current?.(
          commTypeToContactScalarField(type) as any,
          displayValue,
          {
            shouldDirty: true,
          },
        );

        // Update the contact's FK field (*_id)
        const idField = commTypeToContactIdField(type);
        formSetValueRef.current?.(idField as any, newId, {
          shouldDirty: true,
        });

        console.log(
          `[ContactDetail2] Phase 8: Successfully updated contact.${idField} = ${newId}`,
        );

        dispatch(
          showToast({
            message: `${
              type.charAt(0).toUpperCase() + type.slice(1)
            } saved successfully and added to contact`,
            type: "success",
          }),
        );

        setCommModalState((s) => ({ ...s, open: false }));
      } catch (e) {
        const errorDetails = e instanceof Error ? e.message : String(e);
        console.error("[ContactDetail2] handleSaveNewComm failed:", {
          error: e,
          errorMessage: errorDetails,
          type: commModalState.type,
          contactId,
        });
        dispatch(
          showToast({
            message: `Failed to add ${commModalState.type}: ${errorDetails}`,
            type: "error",
          }),
        );
      } finally {
        setCommSaving(false);
      }
    },
    [
      ensureContactId,
      commModalState.type,
      dispatch,
      refreshCommType,
      saveRecord,
      setPrimaryCommWithoutRefetch,
    ],
  );

  const CommSelectDialog = commSelectState.open
    ? createPortal(
        <div
          className="fixed inset-0 z-50 bg-black/40 flex items-start justify-center pt-[12vh]"
          onClick={() => closeCommSelect()}
        >
          <div
            className="w-full max-w-lg mx-4 bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-700"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100 capitalize">
                Select {commSelectState.type}
              </div>
              <button
                type="button"
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                onClick={() => closeCommSelect()}
              >
                <FaChevronRight />
              </button>
            </div>
            <div className="p-4 space-y-3">
              <div className="flex items-center gap-2">
                <input
                  value={commSelectQuery}
                  onChange={(e) => setCommSelectQuery(e.target.value)}
                  placeholder="Search..."
                  className="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800"
                />
                <button
                  type="button"
                  className="px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30 rounded-lg"
                  onClick={() => handleAddNewComm(commSelectState.type)}
                >
                  Add new
                </button>
              </div>

              <div className="max-h-72 overflow-y-auto border border-slate-200 dark:border-slate-700 rounded-lg">
                {commGlobalLoading ? (
                  <div className="p-3 text-sm text-slate-500 dark:text-slate-400 flex items-center gap-2">
                    <FaSpinner className="animate-spin" size={12} />
                    Loading...
                  </div>
                ) : filteredCommItems.length === 0 ? (
                  <div className="p-3 text-sm text-slate-500 dark:text-slate-400">
                    No matches
                  </div>
                ) : (
                  filteredCommItems.map((item: any, idx: number) => {
                    const value = getCommDisplayValue(
                      commSelectState.type,
                      item,
                    );
                    const label = item?.name || item?.type || "";
                    return (
                      <button
                        key={`${item?.id ?? value ?? "comm"}-${idx}`}
                        type="button"
                        onClick={() => handleSelectComm(item)}
                        className="w-full text-left px-3 py-2 border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50"
                        disabled={commSaving}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <div className="text-sm text-slate-900 dark:text-slate-100 truncate">
                              {value || "--"}
                            </div>
                            {label ? (
                              <div className="text-xs text-slate-500 dark:text-slate-400 truncate">
                                {label}
                              </div>
                            ) : null}
                          </div>
                          <div className="text-xs text-slate-400 font-mono shrink-0">
                            #{item?.id}
                          </div>
                        </div>
                      </button>
                    );
                  })
                )}
              </div>

              {commSaving && (
                <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-2">
                  <FaSpinner className="animate-spin" size={12} />
                  Saving...
                </div>
              )}
            </div>
          </div>
        </div>,
        document.body,
      )
    : null;

  // ---------------------------------------------------------------------------
  // Tab Navigation
  // ---------------------------------------------------------------------------

  const { activeTab, setActiveTab } = useDetailTabs(
    "contact",
    "actions",
    VALID_TABS,
  );

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
    getValues,
    reset,
    setValue,
    formState: { errors, isDirty, isSubmitting },
  } = useForm({
    resolver: zodResolver(
      recordMode === "edit" ? updateContactSchema : contactSchema,
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

  useEffect(() => {
    formSetValueRef.current = setValue as any;
  }, [setValue]);

  useEffect(() => {
    formGetValuesRef.current = (name: string) => (getValues as any)(name);
  }, [getValues]);

  useEffect(() => {
    formGetAllValuesRef.current = getValues;
  }, [getValues]);

  // Auto-fill attention = "{first} {last}" and keep it in sync while editing.
  const watchedFirstName = useWatch({ control, name: "name_first" });
  const watchedLastName = useWatch({ control, name: "name_last" });
  useEffect(() => {
    if (!isEditing) return;
    const next = [watchedFirstName, watchedLastName]
      .map((v) => String(v || "").trim())
      .filter(Boolean)
      .join(" ")
      .replace(/\s+/g, " ")
      .trim();
    const current = String(getValues("attention") || "");
    if (current !== next) {
      setValue("attention", next, {
        shouldDirty: false,
        shouldValidate: false,
      });
    }
  }, [isEditing, watchedFirstName, watchedLastName, getValues, setValue]);

  // Sync form when data loads
  useEffect(() => {
    if (!data) {
      return;
    }
    const currentId = data?.id ?? null;
    if (lastResetIdRef.current === currentId) return;
    // Add mode — don't call reset({}) when there's no data; when data exists
    // reset once for this record id and remember it to avoid loops.
    reset({
      ...data,
      customer_id: normalizeNumber(data.customer_id ?? data.customer),
      rep_id: normalizeNumber(data.rep_id ?? data.rep),
      vendor_id: normalizeNumber(data.vendor_id ?? data.vendor),
      employee_id: normalizeNumber(data.employee_id ?? data.employee),
      manufacturer_id: normalizeNumber(
        data.manufacturer_id ?? data.manufacturer,
      ),
      other_id: normalizeNumber(data.other_id),
      refs: {
        tags: data.refs?.tags ?? [],
        categories: data.refs?.categories ?? [],
        keywords: data.refs?.keywords ?? [],
        related_ids: data.refs?.related_ids ?? [],
        depends_on: data.refs?.depends_on ?? {},
        links: {
          rep: data.refs?.links?.rep ?? [],
          item: data.refs?.links?.item ?? [],
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
          order: data.refs?.links?.order ?? [],
          domain: (data.refs?.links?.domain ?? []).map((d: any) => ({
            id: d.id ?? 0,
            name: d.name ?? "",
            domain: d.domain ?? "",
          })),
          contact: data.refs?.links?.contact ?? [],
          customer: data.refs?.links?.customer ?? [],
          document: data.refs?.links?.document ?? [],
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
          manufacturer: data.refs?.links?.manufacturer ?? [],
          project: data.refs?.links?.project ?? [],
          vendor: data.refs?.links?.vendor ?? [],
        },
      },
    });
    lastResetIdRef.current = currentId;
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
      const orgType = org.org_type || ID_FIELD_TO_ORG_TYPE[targetField];
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
          recordMode,
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
            formData.customer_id ??
            parentCustomerId ??
            data?.customer_id ??
            data?.customer,
          rep_id: formData.rep_id ?? data?.rep_id ?? data?.rep,
          vendor_id: formData.vendor_id ?? data?.vendor_id ?? data?.vendor,
          employee_id:
            formData.employee_id ?? data?.employee_id ?? data?.employee,
          manufacturer_id:
            formData.manufacturer_id ??
            data?.manufacturer_id ??
            data?.manufacturer,
          other_id: formData.other_id ?? data?.other_id,
          refs: mappedRefs,
        };

        const payload =
          recordMode === "add"
            ? {
                ...basePayload,
                password: (formData as any).password,
                // cnf_password is frontend-only validation — never send to backend
              }
            : basePayload;

        const res =
          recordMode === "add"
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
            recordMode === "add" &&
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
                recordMode === "add" ? "created" : "updated"
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
      recordMode,
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

  const handleClose = useCallback(async () => {
    // Wait for any background child-record saves to finish
    if (inflightCount > 0) {
      await waitForAll();
    }
    if (onCancelInline) {
      onCancelInline();
      return;
    }
    windowManager.closeWindow(windowPath || location.pathname);
  }, [
    onCancelInline,
    windowManager,
    windowPath,
    location.pathname,
    inflightCount,
    waitForAll,
  ]);

  const handleDeleteContact = useCallback(async () => {
    const contactId = data?.id;
    if (!contactId) return;
    if (!window.confirm(`Delete contact #${contactId}?`)) return;

    try {
      await deleteRecord("contact", contactId);
      dispatch(showToast({ message: "Contact deleted", type: "success" }));

      window.dispatchEvent(
        new CustomEvent("contact-deleted", {
          detail: { contactId },
        }),
      );

      // Allow parent list pages (inline detail) to refetch immediately.
      onSaved?.();
      handleClose();
    } catch (err) {
      console.error("[ContactDetail] delete failed:", err);
      dispatch(
        showToast({ message: "Failed to delete contact", type: "error" }),
      );
    }
  }, [data?.id, dispatch, onSaved, handleClose]);

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

    // Delete (right side, before close)
    if (effectiveMode === "view" && data?.id) {
      buttons.push(
        <button
          key="delete-contact"
          type="button"
          onClick={handleDeleteContact}
          className="p-2 text-rose-600 hover:bg-rose-50 dark:hover:bg-slate-700 rounded-lg transition-colors"
          title="Delete contact"
        >
          <FaTrash size={14} />
        </button>,
      );
    }

    // Close detail (always shown at far right)
    buttons.push(
      <button
        key="close-detail"
        type="button"
        onClick={handleClose}
        className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
        title="Close detail"
      >
        <FaTimes size={14} />
      </button>,
    );

    return buttons;
  };

  // ---------------------------------------------------------------------------
  // Cancel handler
  // ---------------------------------------------------------------------------

  const handleCancel = useCallback(() => {
    if (recordMode === "add") {
      // Stay on the page, just clear changes back to defaultValues.
      reset();
      setEffectiveMode("add");
      return;
    }
    setEffectiveMode("view");
    if (data) reset(data);
  }, [recordMode, data, reset]);

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
              <DevBadge label="Contact" className="mr-2" />
              <DetailFeatureBadge
                features={{ autoSave: true, bgSaveChildren: true }}
                className="mr-2"
              />
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
              {(autoSaveInProgress || inflightCount > 0) && (
                <span className="px-3 py-1 text-xs font-medium text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center gap-1.5">
                  <FaSpinner className="animate-spin" size={10} />
                  {autoSaveInProgress
                    ? "Auto-saving…"
                    : `${inflightCount} saving…`}
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
          /* ── Read-only view — ScalarCard / JsonCard / BaseModelCards ── */
          <div className="space-y-0">
            {/* ── Name ── */}
            <ScalarCard
              title="Name"
              icon={<User2 size={14} />}
              columns={3}
              fields={[
                { label: "name_first", value: data.name_first },
                { label: "name_last", value: data.name_last },
                { label: "name_middle", value: data.name_middle },
                { label: "name_prefix", value: data.name_prefix },
                { label: "name_suffix", value: data.name_suffix },
                { label: "attention", value: data.attention },
              ]}
            />

            {/* ── Contact Info ── */}
            <ScalarCard
              title="Contact Info"
              icon={<Mail size={14} />}
              columns={3}
              fields={[
                { label: "email", value: data.email, highlight: true },
                { label: "email_id", value: data.email_id },
                { label: "phone", value: data.phone },
                { label: "phone_id", value: data.phone_id },
                { label: "address_full", value: data.address_full },
                { label: "address_id", value: data.address_id },
                { label: "domain", value: data.domain },
                { label: "domain_id", value: data.domain_id },
              ]}
            />

            {/* ── Organization ── */}
            <ScalarCard
              title="Organization"
              icon={<Building2 size={14} />}
              columns={3}
              fields={[
                { label: "company", value: data.company },
                { label: "title", value: data.title },
                { label: "department", value: data.department },
                { label: "role", value: data.role },
                { label: "comment", value: data.comment },
                { label: "customer_id", value: data.customer_id },
                { label: "vendor_id", value: data.vendor_id },
                { label: "rep_id", value: data.rep_id },
                { label: "employee_id", value: data.employee_id },
                { label: "manufacturer_id", value: data.manufacturer_id },
                { label: "other_id", value: data.other_id },
              ]}
            />

            {/* ── Auth & System ── */}
            <ScalarCard
              title="Auth & System"
              icon={<ShieldCheck size={14} />}
              columns={3}
              fields={[
                { label: "is_active", value: data.is_active },
                { label: "is_staff", value: data.is_staff },
                { label: "is_superuser", value: data.is_superuser },
                { label: "dt_joined", value: data.dt_joined },
                { label: "last_login", value: data.last_login },
              ]}
            />

            {/* ── JSONB — actions ── */}
            <JsonCard
              title="Actions"
              fieldName="actions"
              data={data.actions as Record<string, unknown> | null | undefined}
              columns={3}
              defaultExpanded={false}
            />

            {/* ── BaseModel Identity + Envelopes ── */}
            <BaseModelCards data={data as Record<string, unknown>} />
          </div>
        ) : (
          /* ── Editable form ── */
          <form
            id="contact-form"
            onSubmit={handleSubmit(onSubmit, onValidationError)}
          >
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2 flex items-center gap-2">
              <FaUser size={16} />
              Basic Information
            </h3>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-x-6 gap-y-0">
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
              {shouldRenderField("attention") && (
                <HorizontalField label="attention" htmlFor="attention">
                  <Input
                    type="text"
                    id="attention"
                    placeholder="Auto from first + last"
                    {...register("attention")}
                    disabled
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
            </div>

            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 my-2 flex items-center gap-2">
              <FaAddressBook size={16} />
              Contact Information
            </h3>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-x-6 gap-y-0">
              {shouldRenderField("email") && (
                <HorizontalField
                  label="email"
                  htmlFor="email"
                  required
                  error={errors.email?.message}
                >
                  <div className="flex items-center gap-1.5">
                    <Input
                      type="email"
                      id="email"
                      placeholder="Primary email"
                      {...register("email")}
                      error={!!errors.email?.message}
                      disabled={isFieldDisabled("email")}
                    />
                    {effectiveMode !== "view" && (
                      <button
                        type="button"
                        onClick={() => openCommSelect("email")}
                        className="shrink-0 p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                        title="Select or add email"
                        disabled={
                          isFieldDisabled("email") || autoSaveInProgress
                        }
                      >
                        <FaSearch size={13} />
                      </button>
                    )}
                  </div>
                </HorizontalField>
              )}

              {shouldRenderField("phone") && (
                <HorizontalField label="phone" htmlFor="phone">
                  <div className="flex items-center gap-1.5">
                    <Input
                      type="text"
                      id="phone"
                      placeholder="Primary phone"
                      {...register("phone" as any)}
                      disabled={isFieldDisabled("phone")}
                    />
                    {effectiveMode !== "view" && (
                      <button
                        type="button"
                        onClick={() => openCommSelect("phone")}
                        className="shrink-0 p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                        title="Select or add phone"
                        disabled={
                          isFieldDisabled("phone") || autoSaveInProgress
                        }
                      >
                        <FaSearch size={13} />
                      </button>
                    )}
                  </div>
                </HorizontalField>
              )}

              {shouldRenderField("address_full") && (
                <HorizontalField label="address_full" htmlFor="address_full">
                  <div className="flex items-center gap-1.5">
                    <Input
                      type="text"
                      id="address_full"
                      placeholder="Full address"
                      {...register("address_full" as any)}
                      disabled={isFieldDisabled("address_full")}
                    />
                    {effectiveMode !== "view" && (
                      <button
                        type="button"
                        onClick={() => openCommSelect("address")}
                        className="shrink-0 p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                        title="Select or add address"
                        disabled={
                          isFieldDisabled("address_full") || autoSaveInProgress
                        }
                      >
                        <FaSearch size={13} />
                      </button>
                    )}
                  </div>
                </HorizontalField>
              )}

              {shouldRenderField("domain") && (
                <HorizontalField label="domain" htmlFor="domain">
                  <div className="flex items-center gap-1.5">
                    <Input
                      type="text"
                      id="domain"
                      placeholder="Primary domain"
                      {...register("domain" as any)}
                      disabled={isFieldDisabled("domain")}
                    />
                    {effectiveMode !== "view" && (
                      <button
                        type="button"
                        onClick={() => openCommSelect("domain")}
                        className="shrink-0 p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                        title="Select or add domain"
                        disabled={
                          isFieldDisabled("domain") || autoSaveInProgress
                        }
                      >
                        <FaSearch size={13} />
                      </button>
                    )}
                  </div>
                </HorizontalField>
              )}
            </div>
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 my-2 flex items-center gap-2">
              <FaBuilding size={16} />
              Company Information
            </h3>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-x-6 gap-y-0">
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
              {(
                [
                  "customer_id",
                  "vendor_id",
                  "rep_id",
                  "employee_id",
                  "manufacturer_id",
                  "other_id",
                ] as const
              ).map(
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
                          placeholder={`${fieldName
                            .replace("_id", "")
                            .replace(/^./, (c) => c.toUpperCase())} ID`}
                          {...register(fieldName as any, {
                            valueAsNumber: true,
                          })}
                          //disabled={isFieldDisabled(fieldName)}
                          disabled={
                            effectiveMode === "edit" || effectiveMode === "add"
                          }
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
      {activeContactId && data?.id ? (
        <>
          <DetailTabs
            entityType="contact"
            activeTab={activeTab}
            onTabChange={setActiveTab}
            standardTabs={["actions", "comments", "documents", "raw"]}
            additionalTabs={additionalTabs}
            badges={tabBadges}
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
                          address: comms.addresses || [],
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
      ) : (
        /* Unsaved contact — show hint that tabs appear after save */
        <div className="flex-1 flex items-center justify-center text-sm text-slate-400 dark:text-slate-500">
          {autoSaveInProgress ? (
            <span className="flex items-center gap-2">
              <FaSpinner className="animate-spin" size={14} />
              Saving contact…
            </span>
          ) : (
            <span>
              Fill in the required fields above. Tabs &amp; related records will
              appear once the contact is saved
              {effectiveMode === "add" &&
                " — or use the search buttons to auto-save and link records."}
            </span>
          )}
        </div>
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

      {/* ─── Communications Pickers (Basic Info) ─── */}
      {CommSelectDialog}
      <CommunicationAddEditModal
        isOpen={commModalState.open}
        type={commModalState.type}
        data={commModalState.data}
        onClose={() => setCommModalState((s) => ({ ...s, open: false }))}
        onSave={handleSaveNewComm}
        isSaving={commSaving}
        contactId={activeContactId ?? undefined}
      />
    </div>
  );
}
