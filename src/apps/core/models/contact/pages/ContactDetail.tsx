/**
 * ContactDetail.tsx
 * 
 * Standard Contact Detail page using Enterprise Best Practices Layout following UX research:
 * - Two-column layout with labels on the left (scannable)
 * - Logical field groupings in collapsible sections
 * - Consistent label widths for vertical alignment
 * - Compact but readable spacing
 * - Visual hierarchy with section headers
 * - Keyboard navigation support
 * 
 * This is the main ContactDetail component. Alternative layouts available via
 * ContactDetailStart.tsx which provides a layout selector.
 * 
 * References:
 * - Nielsen Norman Group enterprise form guidelines
 * - Luke Wroblewski's label placement research
 * - Baymard Institute density studies
 */

import { useEffect, useMemo, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import DetailShell from "@/components/common/DetailShell";
import ComponentCard from "@/components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import Input from "../../../../../components/form/input/InputField";
import DropDown from "../../../../../components/form/input/DropDown";
import { createContact, updateContact } from "../services/contactApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useParams, useSearchParams } from "react-router";
import { getRecord } from "@/api/wcapi";
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
import Checkbox from "../../../../../components/form/input/Checkbox";
import { 
  FaSave, FaChevronDown, FaChevronRight, FaTimes, FaEdit,
  FaUser, FaBuilding, FaIdCard, FaCog,
  FaStar, FaThLarge, FaCompressAlt, FaAlignLeft, FaListAlt, FaColumns, FaLayerGroup
} from "react-icons/fa";
import { useDetailFieldAccess } from "@/hooks/useDetailFieldAccess";

// Panel Components
import {
  CommentsPanel,
  MetadataPanel,
  RefsPanel,
  PrefsPanel,
  RawDataPanel,
  ActionsPanel,
  CommunicationsPanel,
} from "@/apps/common/components/panels";

// ------------------------------------
// Layout Selector for team discussion
// ------------------------------------
type LayoutStyle = "best-practice" | "grid" | "compact" | "dense" | "horizontal" | "two-column";

interface LayoutOption {
  value: LayoutStyle;
  label: string;
  icon: React.ReactNode;
  description: string;
}

const layoutOptions: LayoutOption[] = [
  { value: "best-practice", label: "Best Practice", icon: <FaStar className="w-3.5 h-3.5" />, description: "Enterprise UX standard - collapsible sections" },
  { value: "grid", label: "Grid", icon: <FaThLarge className="w-3.5 h-3.5" />, description: "3-column grid with labels above" },
  { value: "compact", label: "Compact", icon: <FaCompressAlt className="w-3.5 h-3.5" />, description: "Dense 3-column layout" },
  { value: "dense", label: "Dense", icon: <FaAlignLeft className="w-3.5 h-3.5" />, description: "Ultra-compact inline labels" },
  { value: "horizontal", label: "Horizontal", icon: <FaListAlt className="w-3.5 h-3.5" />, description: "2-column with left labels" },
  { value: "two-column", label: "Two Column", icon: <FaColumns className="w-3.5 h-3.5" />, description: "Card-based layout" },
];

function LayoutSelector({ value, onChange }: { value: LayoutStyle; onChange: (layout: LayoutStyle) => void }) {
  return (
    <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded-lg">
      <FaLayerGroup className="text-slate-400 w-3 h-3" />
      {layoutOptions.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={`p-1.5 rounded transition-all ${
            value === option.value
              ? "bg-blue-500 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600"
          }`}
          title={`${option.label}: ${option.description}`}
        >
          {option.icon}
        </button>
      ))}
    </div>
  );
}

// ------------------------------------
// Enterprise Field Row Component
// Label on left (fixed width), input on right
// Optimized for daily use and scannability
// ------------------------------------
interface FieldRowProps {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
  error?: string;
  required?: boolean;
  hint?: string;
}

function FieldRow({ label, htmlFor, children, error, required, hint }: FieldRowProps) {
  return (
    <div className="flex items-start gap-3 py-2">
      <Label 
        htmlFor={htmlFor} 
        className="w-32 shrink-0 pt-2 text-right text-sm font-medium text-slate-600 dark:text-slate-400"
      >
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </Label>
      <div className="flex-1 min-w-0">
        {children}
        {hint && !error && <p className="mt-0.5 text-xs text-slate-400">{hint}</p>}
        {error && <p className="mt-0.5 text-xs text-red-500">{error}</p>}
      </div>
    </div>
  );
}

// ------------------------------------
// Collapsible Section Component
// Groups related fields together
// ------------------------------------
interface SectionProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultExpanded?: boolean;
}

function Section({ title, icon, children, defaultExpanded = true }: SectionProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className="mb-4 border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
      <button
        type="button"
        className="w-full flex items-center justify-between px-4 py-2.5 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <FaChevronDown className="text-slate-400 w-3 h-3" />
          ) : (
            <FaChevronRight className="text-slate-400 w-3 h-3" />
          )}
          <span className="text-slate-500">{icon}</span>
          <span className="font-semibold text-sm text-slate-700 dark:text-slate-200">{title}</span>
        </div>
      </button>
      {isExpanded && (
        <div className="px-4 py-3 bg-white dark:bg-slate-900">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-6">
            {children}
          </div>
        </div>
      )}
    </div>
  );
}

// ------------------------------------
// Field Configuration
// ------------------------------------
const CONTACT_DETAIL_FIELDS = [
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

const normalizeNumber = (value: any): number | undefined => {
  if (value === null || value === undefined || value === "") return undefined;
  const num = Number(value);
  return isNaN(num) ? undefined : num;
};

// ------------------------------------
// Main Component
// ------------------------------------
export default function ContactDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
  id: idProp,
  recordId,
}: ContactAddProps) {
  const dispatch = useDispatch();
  const location = useLocation();
  const params = useParams<{ id?: string }>();
  const [searchParams] = useSearchParams();
  const routeState = (location.state as any) || {};

  // Get ID from multiple sources (in priority order):
  // 1. Direct id/recordId prop (from WcapiRouteHandler)
  // 2. Path params (e.g., /contact/22)
  // 3. Search params (e.g., /wcapi/get/?model_name=contact&id=22)
  // 4. Route state (e.g., navigate with state)
  // 5. dataProp?.id (passed directly)
  const urlId = idProp || recordId || params.id || searchParams.get("id") || routeState.data?.id || dataProp?.id;
  const contactIdFromUrl = urlId ? (typeof urlId === 'number' ? urlId : parseInt(String(urlId), 10)) : null;
  
  console.log('[ContactDetail] ID resolution:', { 
    idProp,
    recordId,
    'params.id': params.id, 
    'searchParams.id': searchParams.get("id"), 
    'routeState.data?.id': routeState.data?.id,
    'dataProp?.id': dataProp?.id,
    contactIdFromUrl 
  });
  
  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const initialData = dataProp || routeState.data || null;
  
  // State for fetched data (when navigating via URL with id param)
  const [fetchedData, setFetchedData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  // Use fetched data if available and matches URL id, otherwise use prop/state data
  // Priority: fetchedData (if matches URL) > initialData (if matches URL) > fetch needed
  const data = fetchedData || initialData;
  
  // The actual contact ID - USE THE LOADED DATA'S ID as the source of truth
  // This is the ID of the contact record displayed in the form
  const activeContactId = data?.id || contactIdFromUrl || null;
  
  console.log('[ContactDetail] Data check:', {
    contactIdFromUrl,
    'data?.id': data?.id,
    'initialData?.id': initialData?.id,
    'fetchedData?.id': fetchedData?.id,
    activeContactId,
  });
  
  // Fetch contact data when URL id doesn't match current data
  useEffect(() => {
    // Always fetch if we have a URL id that doesn't match current data
    if (contactIdFromUrl && contactIdFromUrl !== fetchedData?.id) {
      // Check if initialData already has the right contact
      if (initialData?.id === contactIdFromUrl) {
        console.log('[ContactDetail] initialData matches URL id, no fetch needed');
        return;
      }
      
      setIsLoading(true);
      console.log('[ContactDetail] Fetching contact:', contactIdFromUrl);
      getRecord("contact", contactIdFromUrl)
        .then((result) => {
          console.log('[ContactDetail] Fetched contact:', result);
          setFetchedData(result?.record || result);
        })
        .catch((err) => {
          console.error('[ContactDetail] Failed to fetch contact:', err);
        })
        .finally(() => setIsLoading(false));
    }
  }, [contactIdFromUrl, initialData?.id, fetchedData?.id]);
  
  // Allow toggling between view and edit modes
  const [effectiveMode, setEffectiveMode] = useState<"add" | "edit" | "view">(mode);
  
  // Layout selector for team discussion
  const [selectedLayout, setSelectedLayout] = useState<LayoutStyle>("best-practice");
  
  // Local state for communications (updated by CommunicationsPanel after successful API calls)
  const [communications, setCommunications] = useState({
    emails: data?.communications?.emails || data?.refs?.links?.email || [],
    phones: data?.communications?.phones || data?.refs?.links?.phone || [],
    addresses: data?.communications?.addresses || data?.refs?.links?.address || [],
    domains: data?.communications?.domains || data?.refs?.links?.domain || [],
  });
  
  // Sync effectiveMode when mode prop changes
  useEffect(() => {
    setEffectiveMode(mode);
  }, [mode]);
  
  // Sync communications when data changes (e.g., after refetch)
  useEffect(() => {
    if (data?.communications || data?.refs?.links) {
      setCommunications({
        emails: data.communications?.emails || data.refs?.links?.email || [],
        phones: data.communications?.phones || data.refs?.links?.phone || [],
        addresses: data.communications?.addresses || data.refs?.links?.address || [],
        domains: data.communications?.domains || data.refs?.links?.domain || [],
      });
    }
  }, [data?.communications, data?.refs?.links]);
  
  const contactFieldNames = useMemo(() => CONTACT_DETAIL_FIELDS.slice(), []);
  const {
    isAdmin,
    isFieldVisible,
    isFieldReadOnly,
  } = useDetailFieldAccess("contact", contactFieldNames);

  const isFieldDisabled = (fieldName: string) => {
    if (effectiveMode === "view") return true;
    if (!isAdmin && isFieldReadOnly(fieldName)) return true;
    return false;
  };

  const shouldRenderField = (fieldName: string) => {
    if (isAdmin) return true;
    return isFieldVisible(fieldName);
  };

  // React Hook Form
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(mode === "edit" ? updateContactSchema : contactSchema),
    defaultValues: {
      refs: {
        tags: [],
        categories: [],
        keywords: [],
        depends_on: {},
        related_ids: [],
        links: {
          rep: [], item: [], email: [], order: [], phone: [], domain: [],
          contact: [], customer: [], document: [], address: [],
          manufacturer: [], project: [], vendor: [],
        },
      },
    },
  });

  // Load Edit Data
  useEffect(() => {
    if (!data) {
      reset({});
      return;
    }

    const normalizedContact = {
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
            id: e.id ?? 0, name: e.name ?? "", address: e.address ?? "",
          })),
          phone: (data.refs?.links?.phone ?? []).map((p: any) => ({
            id: p.id ?? 0, name: p.name ?? "", number: p.number ?? "",
          })),
          address: (data.refs?.links?.address ?? []).map((a: any) => ({
            id: a.id ?? 0, name: a.name ?? "", address_line1: a.address_line1 ?? "",
            address_line2: a.address_line2 ?? "", city: a.city ?? "",
            state: a.state ?? "", postal_code: a.postal_code ?? "", country: a.country ?? "",
          })),
          domain: (data.refs?.links?.domain ?? []).map((d: any) => ({
            id: d.id ?? 0, name: d.name ?? "", domain: d.domain ?? "",
          })),
        },
      },
    };

    reset(normalizedContact);
  }, [data, reset]);

  // Form submission
  const onSubmit = async (formData: z.infer<typeof contactSchema> | z.infer<typeof updateContactSchema>) => {
    try {
      const mappedRefs = formData.refs ? mapRefsFormToApi(formData.refs) : undefined;
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
        customer_id: formData.customer_id,
        rep_id: formData.rep_id,
        vendor_id: formData.vendor_id,
        employee_id: formData.employee_id,
        manufacturer_id: formData.manufacturer_id,
        other_id: formData.other_id,
        refs: mappedRefs,
      };

      const payload = mode === "add"
        ? { ...basePayload, password: (formData as any).password, cnf_password: (formData as any).cnf_password }
        : basePayload;

      const res = mode === "add"
        ? await createContact(payload as CreateContactRequest)
        : await updateContact({ ...payload, id: data?.id } as UpdateContactRequest);

      if (res) {
        dispatch(showToast({ message: `Contact ${mode === "add" ? "created" : "updated"} successfully`, type: "success" }));
        if (onSaved) onSaved();
      }
    } catch (error: unknown) {
      if (error instanceof Error) {
        dispatch(showToast({ message: error.message, type: "error" }));
      }
    }
  };

  const roleOptions = [
    { value: "user", label: "User" },
    { value: "admin", label: "Administrator" },
    { value: "manager", label: "Manager" },
    { value: "staff", label: "Staff" },
    { value: "guest", label: "Guest" },
  ];

  // Show loading state while fetching
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <span className="ml-2 text-gray-600">Loading contact...</span>
      </div>
    );
  }

  return (
    <DetailShell
      title="Contact"
      mode={mode}
      inline={inline}
      hideBreadcrumb={hideBreadcrumb}
      onCancelInline={onCancelInline}
      card={false}
    >
      <ComponentCard>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
            {shouldRenderField("email") && (
              <div>
                <Label htmlFor="email">email</Label>
                <Input
                  type="email"
                  id="email"
                  placeholder="Primary email address for login"
                  {...register("email")}
                  error={errors.email && errors.email.message ? true : false}
                  hint={errors.email && errors.email.message}
                  disabled={isFieldDisabled("email")}
                />
              </div>
            )}
          </div>
          {mode === "add" && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
                {shouldRenderField("password") && (
                  <div>
                    <Label htmlFor="password">password</Label>
                    <Input
                      type="password"
                      id="password"
                      placeholder="Password"
                      {...register("password" as any)}
                      error={
                        (errors as any).password &&
                        (errors as any).password.message
                          ? true
                          : false
                      }
                      hint={
                        (errors as any).password?.message ||
                        "Your password can't be too similar to your other personal information. Your password must contain at least 8 characters. Your password can't be a commonly used password. Your password can't be entirely numeric."
                      }
                      disabled={isFieldDisabled("password")}
                    />
                  </div>
                )}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
                {shouldRenderField("cnf_password") && (
                  <div>
                    <Label htmlFor="cnf_password">cnf_password</Label>
                    <Input
                      type="password"
                      id="cnf_password"
                      placeholder="Confirm Password"
                      {...register("cnf_password" as any)}
                      error={
                        (errors as any).cnf_password &&
                        (errors as any).cnf_password.message
                          ? true
                          : false
                      }
                      hint={
                        (errors as any).cnf_password?.message ||
                        "Enter the same password as before, for verification."
                      }
                      disabled={isFieldDisabled("cnf_password")}
                    />
                  </div>
                )}
              </div>
            </>
          )}
          <h5 className=" dark:text-white text-md font-semibold mt-6 mb-3 custom-header-inner">
            Personal info
          </h5>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
            {shouldRenderField("name_first") && (
              <FieldRow label="First Name" htmlFor="name_first" error={errors.name_first?.message} required>
                <Input
                  type="text"
                  id="name_first"
                  placeholder="First name"
                  {...register("name_first")}
                  error={!!errors.name_first?.message}
                  disabled={isFieldDisabled("name_first")}
                />
              </FieldRow>
            )}

            {shouldRenderField("name_prefix") && (
              <FieldRow label="Prefix" htmlFor="name_prefix">
                <Input
                  type="text"
                  id="name_prefix"
                  placeholder="Mr., Ms., Dr."
                  {...register("name_prefix")}
                  disabled={isFieldDisabled("name_prefix")}
                />
              </FieldRow>
            )}

            {/* Row 2: Last Name (left), Middle (right) */}
            {shouldRenderField("name_last") && (
              <FieldRow label="Last Name" htmlFor="name_last" error={errors.name_last?.message} required>
                <Input
                  type="text"
                  id="name_last"
                  placeholder="Last name"
                  {...register("name_last")}
                  error={!!errors.name_last?.message}
                  disabled={isFieldDisabled("name_last")}
                />
              </FieldRow>
            )}

            {shouldRenderField("name_middle") && (
              <FieldRow label="Middle Name" htmlFor="name_middle">
                <Input
                  type="text"
                  id="name_middle"
                  placeholder="Middle name"
                  {...register("name_middle")}
                  disabled={isFieldDisabled("name_middle")}
                />
              </FieldRow>
            )}

            {/* Row 3: Attention (left), Suffix (right) */}
            {shouldRenderField("attention") && (
              <FieldRow label="Attention" htmlFor="attention" hint="Auto-filled from first/last name">
                <Input
                  type="text"
                  id="attention"
                  placeholder="Attention line"
                  {...register("attention")}
                  disabled={isFieldDisabled("attention")}
                />
              </FieldRow>
            )}

            {shouldRenderField("name_suffix") && (
              <FieldRow label="Suffix" htmlFor="name_suffix">
                <Input
                  type="text"
                  id="name_suffix"
                  placeholder="Jr., Sr., III"
                  {...register("name_suffix")}
                  disabled={isFieldDisabled("name_suffix")}
                />
              </FieldRow>
            )}
          </Section>

          {/* 2. Company Information Section */}
          <Section title="Company Information" icon={<FaBuilding className="w-4 h-4" />} defaultExpanded={true}>
            {shouldRenderField("company") && (
              <FieldRow label="Company" htmlFor="company">
                <Input
                  type="text"
                  id="company"
                  placeholder="Company name"
                  {...register("company")}
                  disabled={isFieldDisabled("company")}
                />
              </FieldRow>
            )}

            {shouldRenderField("title") && (
              <FieldRow label="Title" htmlFor="title">
                <Input
                  type="text"
                  id="title"
                  placeholder="Job title"
                  {...register("title")}
                  disabled={isFieldDisabled("title")}
                />
              </FieldRow>
            )}

            {shouldRenderField("department") && (
              <FieldRow label="Department" htmlFor="department">
                <Input
                  type="text"
                  id="department"
                  placeholder="Department"
                  {...register("department")}
                  disabled={isFieldDisabled("department")}
                />
              </FieldRow>
            )}
          </Section>

          {/* 3. Communications Panel - emails, phones, addresses, domains */}
          {/* Use activeContactId which is guaranteed to match URL */}
          {mode !== "add" && activeContactId && (
            <CommunicationsPanel
              entityType="contact"
              entityId={activeContactId}
              contactId={activeContactId}
              data={communications}
              onChange={(comms) => {
                console.log('Communications updated:', comms);
                // Update local state with new communications data
                setCommunications(comms);
              }}
              defaultCollapsed={false}
            />
          )}

          {/* 4. Actions Panel - expanded (only for edit/view) */}
          {mode !== "add" && data?.id && (
            <ActionsPanel
              entityType="contact"
              entityId={data.id}
              data={data.actions}
              onChange={(actions) => {
                console.log('Actions updated:', actions);
              }}
              defaultCollapsed={false}
            />
          )}

          {/* 5. Comments Panel - collapsed */}
          {mode !== "add" && data?.id && (
            <CommentsPanel
              entityType="contact"
              entityId={data.id}
              data={data.comments}
              onChange={(comments) => {
                console.log('Comments updated:', comments);
              }}
              defaultCollapsed={true}
            />
          )}

          {/* 6. Metadata Panel - collapsed (admin only) */}
          {mode !== "add" && data?.id && isAdmin && (
            <MetadataPanel
              entityType="contact"
              entityId={data.id}
              data={data.metadata}
              onChange={(metadata) => {
                console.log('Metadata updated:', metadata);
              }}
              defaultCollapsed={true}
            />
          )}

          {/* 7. Prefs Panel - collapsed */}
          {mode !== "add" && data?.id && (
            <PrefsPanel
              entityType="contact"
              entityId={data.id}
              data={data.prefs}
              onChange={(prefs) => {
                console.log('Prefs updated:', prefs);
              }}
              defaultCollapsed={true}
            />
          )}

          {/* 8. Refs Panel - collapsed (admin only) */}
          {mode !== "add" && data?.id && isAdmin && (
            <RefsPanel
              entityType="contact"
              entityId={data.id}
              data={data.refs}
              onChange={(refs) => {
                console.log('Refs updated:', refs);
              }}
              defaultCollapsed={true}
            />
          )}

          {/* 9. Raw Data Panel - collapsed (admin only, seldom used) */}
          {mode !== "add" && data?.id && isAdmin && (
            <RawDataPanel
              entityType="contact"
              entityId={data.id}
              data={data}
              defaultCollapsed={true}
            />
          )}

          {/* 10. System IDs Section - collapsed */}
          <Section title="System IDs" icon={<FaCog className="w-4 h-4" />} defaultExpanded={false}>
            {shouldRenderField("customer_id") && (
              <FieldRow label="Customer ID" htmlFor="customer_id">
                <Input
                  type="number"
                  id="customer_id"
                  placeholder="Customer ID"
                  {...register("customer_id")}
                  disabled={isFieldDisabled("customer_id")}
                />
              </FieldRow>
            )}

            {shouldRenderField("rep_id") && (
              <FieldRow label="Rep ID" htmlFor="rep_id">
                <Input
                  type="number"
                  id="rep_id"
                  placeholder="Rep ID"
                  {...register("rep_id")}
                  disabled={isFieldDisabled("rep_id")}
                />
              </FieldRow>
            )}

            {shouldRenderField("vendor_id") && (
              <FieldRow label="Vendor ID" htmlFor="vendor_id">
                <Input
                  type="number"
                  id="vendor_id"
                  placeholder="Vendor ID"
                  {...register("vendor_id")}
                  disabled={isFieldDisabled("vendor_id")}
                />
              </FieldRow>
            )}

            {shouldRenderField("employee_id") && (
              <FieldRow label="Employee ID" htmlFor="employee_id">
                <Input
                  type="number"
                  id="employee_id"
                  placeholder="Employee ID"
                  {...register("employee_id")}
                  disabled={isFieldDisabled("employee_id")}
                />
              </FieldRow>
            )}

            {shouldRenderField("manufacturer_id") && (
              <FieldRow label="Manufacturer ID" htmlFor="manufacturer_id">
                <Input
                  type="number"
                  id="manufacturer_id"
                  placeholder="Manufacturer ID"
                  {...register("manufacturer_id")}
                  disabled={isFieldDisabled("manufacturer_id")}
                />
              </FieldRow>
            )}

            {shouldRenderField("other_id") && (
              <FieldRow label="Other ID" htmlFor="other_id">
                <Input
                  type="number"
                  id="other_id"
                  placeholder="Other ID"
                  {...register("other_id")}
                  disabled={isFieldDisabled("other_id")}
                />
              </FieldRow>
            )}
          </Section>

          {/* 10. Account Section - collapsed */}
          <Section title="Account" icon={<FaUser className="w-4 h-4" />} defaultExpanded={false}>
            {shouldRenderField("email") && (
              <FieldRow label="Email" htmlFor="email" error={errors.email?.message} required>
                <Input
                  type="email"
                  id="email"
                  placeholder="Primary email address"
                  {...register("email")}
                  error={!!errors.email?.message}
                  disabled={isFieldDisabled("email")}
                />
              </FieldRow>
            )}

            {effectiveMode === "add" && (
              <>
                {shouldRenderField("password") && (
                  <FieldRow label="Password" htmlFor="password" error={(errors as any).password?.message} required hint="Min 8 chars, not common">
                    <Input
                      type="password"
                      id="password"
                      placeholder="Password"
                      {...register("password" as any)}
                      error={!!(errors as any).password?.message}
                      disabled={isFieldDisabled("password")}
                    />
                  </FieldRow>
                )}
                {shouldRenderField("cnf_password") && (
                  <FieldRow label="Confirm" htmlFor="cnf_password" error={(errors as any).cnf_password?.message} required>
                    <Input
                      type="password"
                      id="cnf_password"
                      placeholder="Confirm password"
                      {...register("cnf_password" as any)}
                      error={!!(errors as any).cnf_password?.message}
                      disabled={isFieldDisabled("cnf_password")}
                    />
                  </FieldRow>
                )}
              </>
            )}

            {shouldRenderField("role") && (
              <FieldRow label="Role" htmlFor="role">
                <Controller
                  name="role"
                  control={control}
                  render={({ field }) => (
                    <DropDown
                      id="role"
                      options={roleOptions}
                      value={field.value || "user"}
                      onChange={field.onChange}
                      disabled={isFieldDisabled("role")}
                    />
                  )}
                />
              </FieldRow>
            )}

            <div className="flex gap-6 py-2 col-span-2">
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
          </Section>
        </form>
      </ComponentCard>
    </DetailShell>
  );
}
