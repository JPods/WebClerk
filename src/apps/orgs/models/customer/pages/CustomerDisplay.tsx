import { useEffect, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import Label from "../../../../../components/form/Label";
import { Input, Select } from "../../../../../components/wrapper";

import { createCustomer, updateCustomer } from "../services/customerApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { FaChevronLeft, FaChevronRight, FaEdit, FaTrash, FaDollarSign, FaFileAlt, FaPhone, FaLink, FaChartBar, FaCreditCard, FaUsers, FaCog, FaColumns } from "react-icons/fa";
import { customerSchema } from "../utils/customerSchema";
import { CustomerAddProps } from "../types/customerType";
import Checkbox from "@/components/form/input/Checkbox";
import CustomerDataPanel from "./CustomerDataPanel";
import TransactionToolbar from "@/apps/transactions/components/TransactionToolbar";
import JsonFieldEditor from "@/apps/transactions/components/JsonFieldEditor";
import { CustomerFinancialPanel, BasicInformationPanel, FinancialSummaryPanel } from "@/apps/common/components/panels";


// Professional customer display component for right-side column
type CustomerFormValues = z.infer<typeof customerSchema>;

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
  financial: { credit: { limit: 0, used: 0 }, balances: { open: 0, current: 0 }, metrics: { ytd: { sales: 0 } } },
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

function HorizontalField({ label, htmlFor, children, error, required }: HorizontalFieldProps) {
  return (
    <div className="flex items-center gap-2 py-2">
      <Label htmlFor={htmlFor} className="w-20 shrink-0 text-right text-sm font-medium text-slate-600 dark:text-slate-400">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </Label>
      <div className="flex-1 min-w-0">
        {children}
        {error && <p className="mt-0.5 text-xs text-red-500">{error}</p>}
      </div>
    </div>
  );
}

// Column layout options
const COLUMN_OPTIONS = [
  { value: 2, label: "2 Columns" },
  { value: 3, label: "3 Columns" },
];

const STORAGE_KEY = "customerDetail_columnCount";
const TAB_STORAGE_KEY = "customerDetail_activeTab";
const VALID_TABS = ["communication", "financial", "relations", "documents", "connections", "data", "metrics", "gl_accounts"];

export default function CustomerDetail({
  modeProp,
  dataProp,
  hideBreadcrumb: _hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
  onPrev,
  onNext,
  onCancel,
  onEdit,
  onDelete,
}: CustomerAddProps) {
  const dispatch = useDispatch();
  const [activeTab, setActiveTab] = useState(() => {
    const stored = localStorage.getItem(TAB_STORAGE_KEY);
    return stored && VALID_TABS.includes(stored) ? stored : "communication";
  });
  const [isEditing, setIsEditing] = useState(false);

  // Persist activeTab to localStorage when it changes
  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
    localStorage.setItem(TAB_STORAGE_KEY, tabId);
  };
  const [columnCount, setColumnCount] = useState<2 | 3>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "2" ? 2 : 3; // Default to 3 columns
  });

  const handleColumnChange = (cols: 2 | 3) => {
    setColumnCount(cols);
    localStorage.setItem(STORAGE_KEY, String(cols));
  };

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
      ...Object.fromEntries(Object.entries(JSON_DEFAULTS).map(([k, v]) => [k, JSON.stringify(v)])),
    },
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const baseMode: "add" | "edit" | "view" = (modeProp || (routeState.mode as "add" | "edit" | "view") || "add");
  // Allow local edit override when in view mode
  const mode: "add" | "edit" | "view" = (baseMode === "view" && isEditing) ? "edit" : baseMode;
  const data = dataProp || routeState.data || null;

  useEffect(() => {
    if (mode === "add") {
      reset({
        is_active: false,
        version: 1,
        org_type: "customer",
        ...Object.fromEntries(Object.entries(JSON_DEFAULTS).map(([k, v]) => [k, JSON.stringify(v)])),
      });
      return;
    }
    if (data) {
      Object.keys(data).forEach((key: any) => {
        if (data[key] !== undefined) {
          if (key in JSON_DEFAULTS) {
            setValue(key, JSON.stringify(data[key] ?? JSON_DEFAULTS[key], null, 2));
          } else {
            setValue(key, data[key]);
          }
        }
      });
      Object.keys(JSON_DEFAULTS).forEach((key) => {
        if (data[key] === undefined) {
          setValue(key as keyof CustomerFormValues, JSON.stringify(JSON_DEFAULTS[key]));
        }
      });
    } else {
      reset({
        is_active: false,
        version: 1,
        org_type: "customer",
        ...Object.fromEntries(Object.entries(JSON_DEFAULTS).map(([k, v]) => [k, JSON.stringify(v)])),
      });
    }
  }, [data, reset, setValue, mode]);

  const parseJsonField = (label: string, raw?: string) => {
    if (!raw || raw.trim() === "") return undefined;
    try {
      return JSON.parse(raw);
    } catch {
      dispatch(showToast({ message: `${label} must be valid JSON`, type: "error" }));
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
        nextValues[key] = JSON.stringify(data[key] ?? JSON_DEFAULTS[key], null, 2);
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
        const parsed = parseJsonField(key, formData[key as keyof CustomerFormValues] as string | undefined);
        if (parsed !== undefined) {
          jsonPayload[key] = parsed;
        }
      });
      const payload = {
        display_name: formData.display_name,
        status: formData.status,
        org_type: formData.org_type,
        version: formData.version,
        is_active: formData.is_active,
        // New scalar fields from wc3
        attention: formData.attention || null,
        contact_id: formData.contact_id || null,
        email: formData.email || null,
        phone: formData.phone || null,
        price_level: formData.price_level || null,
        ...jsonPayload,
      };
      const res =
        mode === "add"
          ? await createCustomer(payload)
          : await updateCustomer({ ...payload, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Customer ${
              mode === "add" ? "created" : "updated"
            } successfully`,
            type: "success",
          })
        );
        // Return to view mode after successful save
        if (isEditing) {
          setIsEditing(false);
        }
        if (onSaved) {
          onSaved();
        }
        return true;
      }
      return false;
    } catch (error: any) {
      dispatch(showToast({ message: error.message, type: "error" }));
      return false;
    }
  };

  const onSubmit = async (formData: CustomerFormValues) => {
    await saveCustomer(formData);
  };

  // Action buttons configuration based on mode
  const getActionButtons = () => {
    const buttons = [];

    if (baseMode === "view" && !isEditing) {
      // View mode - show Edit button to switch to edit mode
      buttons.push(
        <button
          key="edit-local"
          type="button"
          onClick={() => setIsEditing(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
          title="Edit Customer"
        >
          <FaEdit size={14} />
          Edit
        </button>
      );
      if (onCancel) {
        buttons.push(
          <button
            key="close"
            type="button"
            onClick={onCancel}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600 rounded-lg transition-colors"
            title="Close"
          >
            Close
          </button>
        );
      }
      if (onEdit) {
        buttons.push(
          <button
            key="edit"
            type="button"
            onClick={onEdit}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
            title="Edit Customer"
          >
            <FaEdit size={14} />
            Edit
          </button>
        );
      }
      if (onDelete) {
        buttons.push(
          <button
            key="delete"
            type="button"
            onClick={onDelete}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/30 rounded-lg transition-colors"
            title="Delete Customer"
          >
            <FaTrash size={14} />
            Delete
          </button>
        );
      }
    } else {
      // Add/Edit mode - no action buttons
    }

    // Navigation buttons (always available if callbacks provided)
    if (onPrev) {
      buttons.push(
        <button
          key="prev"
          type="button"
          onClick={onPrev}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600 rounded-lg transition-colors"
          title="Previous"
        >
          <FaChevronLeft size={14} />
          Prev
        </button>
      );
    }

    if (onNext) {
      buttons.push(
        <button
          key="next"
          type="button"
          onClick={onNext}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600 rounded-lg transition-colors"
          title="Next"
        >
          Next
          <FaChevronRight size={14} />
        </button>
      );
    }

    return buttons;
  };

  // Tab definitions
  const tabs = [
    { id: "communication", label: "Contact", icon: <FaPhone size={14} /> },
    { id: "financial", label: "Financial", icon: <FaDollarSign size={14} /> },
    { id: "relations", label: "Relations", icon: <FaUsers size={14} /> },
    { id: "documents", label: "Documents", icon: <FaFileAlt size={14} /> },
    { id: "connections", label: "Connections", icon: <FaLink size={14} /> },
    { id: "data", label: "Data", icon: <FaCog size={14} /> },
    { id: "metrics", label: "Metrics", icon: <FaChartBar size={14} /> },
    { id: "gl_accounts", label: "GL Accounts", icon: <FaCreditCard size={14} /> },
  ];

  const formData = watch();
  
  // In view mode, prefer direct data from props; in edit/add mode, use form values
  const customerData: Customer = mode === "view" && data
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

  // Function to get data for specific tab
  const getTabData = (tabId: string) => {
    const baseData = { ...customerData };
    const jsonData = Object.fromEntries(
      Object.entries(JSON_DEFAULTS).map(([key, defaultValue]) => {
        try {
          const parsed = JSON.parse(formData[key as keyof CustomerFormValues] as string || JSON.stringify(defaultValue));
          return [key, parsed];
        } catch {
          return [key, defaultValue];
        }
      })
    );

    // Define which fields belong to each tab
    const tabFieldMapping: Record<string, string[]> = {
      communication: ['contacts', 'addresses', 'domains', 'phones', 'emails'],
      financial: ['financial'],
      relations: ['relations'],
      documents: ['docs'],
      connections: ['connections'],
      data: ['data'],
      metrics: ['metrics'],
      gl_accounts: ['gl_accounts'],
    };

    const fieldsForTab = tabFieldMapping[tabId] || [];
    const filteredData: Record<string, any> = {};

    fieldsForTab.forEach(field => {
      if (jsonData[field] !== undefined) {
        filteredData[field] = jsonData[field];
      }
    });

    return { ...baseData, ...filteredData };
  };

  return (
    <div className="h-full flex flex-col bg-white dark:bg-slate-900">
      {/* Compact Header */}
      <div className="shrink-0 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 truncate">
              {customerData.display_name || "New Customer"}
              {customerData.id && <span className="ml-2 text-sm font-normal text-slate-500 dark:text-slate-400">#{customerData.id}</span>}
            </h2>
            <div className="flex items-center gap-3 mt-1">
              <span className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${
                customerData.is_active
                  ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400'
                  : 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400'
              }`}>
                {customerData.is_active ? 'Active' : 'Inactive'}
              </span>
              <span className="text-sm text-slate-500 dark:text-slate-400">
                {customerData.org_type || 'customer'} • v{customerData.version ?? 1}
              </span>
              {(mode === "edit" || mode === "add") && isDirty && (
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

      {/* Transaction-style Toolbar (edit/add mode) */}
      {(mode === "edit" || mode === "add") && (
        <div className="sticky top-0 z-20 mx-0 px-4 py-3 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm border-b border-slate-200 dark:border-slate-700">
          <TransactionToolbar
            transactionType="order"
            transactionId={data?.id}
            isDirty={isDirty}
            isSaving={isSubmitting}
            isEditing
            onSave={handleSubmit(async (fd) => {
              await saveCustomer(fd);
            })}
            onSaveAndClose={
              (inline ? !!onCancelInline : !!onCancel)
                ? handleSubmit(async (fd) => {
                    const ok = await saveCustomer(fd);
                    if (ok) handleCancel();
                  })
                : undefined
            }
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
      <div className="shrink-0 px-4 py-3 border-b border-slate-200 dark:border-slate-700">
        {mode === "view" ? (
          <div className="space-y-3">
            <BasicInformationPanel
              data={customerData}
              columns={columnCount}
            />
            {/* Financial Summary - Collapsible */}
            {customerData.financial && (
              <FinancialSummaryPanel
                customer={customerData.financial?.customer}
                common={customerData.financial?.common}
                currency="USD"
                defaultCollapsed={true}
                columns={columnCount}
              />
            )}
          </div>
        ) : (
          /* Editable Basic Information - Horizontal Layout */
          <div className={`grid grid-cols-1 ${columnCount === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2'} gap-x-6 gap-y-1`}>
            <HorizontalField label="Company" htmlFor="display_name" required error={errors.display_name?.message}>
              <Input
                type="text"
                id="display_name"
                placeholder="Enter company name"
                {...register("display_name")}
                error={errors.display_name && errors.display_name.message ? true : false}
              />
            </HorizontalField>

            <HorizontalField label="Email" htmlFor="email">
              <Input
                type="email"
                id="email"
                placeholder="Primary email"
                {...register("email")}
              />
            </HorizontalField>

            <HorizontalField label="Attention" htmlFor="attention">
              <Input
                type="text"
                id="attention"
                placeholder="Attn: line"
                {...register("attention")}
              />
            </HorizontalField>

            <HorizontalField label="Phone" htmlFor="phone">
              <Input
                type="tel"
                id="phone"
                placeholder="Primary phone"
                {...register("phone")}
              />
            </HorizontalField>

            <HorizontalField label="Price Level" htmlFor="price_level">
              <Input
                type="text"
                id="price_level"
                placeholder="retail, wholesale"
                {...register("price_level")}
              />
            </HorizontalField>

            <HorizontalField label="Status" htmlFor="status" required>
              <Controller
                name="status"
                control={control}
                render={({ field }) => (
                  <Select
                    options={STATUS_OPTIONS}
                    value={field.value}
                    onChange={field.onChange}
                    placeholder="Select status"
                  />
                )}
              />
            </HorizontalField>

            <HorizontalField label="Org Type" htmlFor="org_type">
              <Controller
                name="org_type"
                control={control}
                render={({ field }) => (
                  <Select
                    options={ORG_TYPE_OPTIONS}
                    value={field.value}
                    onChange={field.onChange}
                    placeholder="Select type"
                  />
                )}
              />
            </HorizontalField>

            <HorizontalField label="Version" htmlFor="version">
              <Input
                type="number"
                id="version"
                placeholder="1"
                {...register("version", { valueAsNumber: true })}
              />
            </HorizontalField>

            <div className="flex items-center gap-2 py-2">
              <div className="w-20 shrink-0" />
              <Controller
                name="is_active"
                control={control}
                render={({ field }) => (
                  <Checkbox
                    id="is_active"
                    checked={field.value ?? false}
                    onChange={field.onChange}
                    label="Active"
                  />
                )}
              />
            </div>
          </div>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="shrink-0 border-b border-slate-200 dark:border-slate-700">
        <nav className="px-4">
          <div className="flex items-center justify-between py-2 gap-4">
            <div className="flex gap-1 overflow-x-auto">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => handleTabChange(tab.id)}
                  className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-all duration-200 whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border-b-2 border-blue-600'
                      : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>
            {/* Column Layout Selector */}
            <div className="flex items-center gap-2 shrink-0 bg-slate-100 dark:bg-slate-700 rounded-md px-2 py-1">
              <FaColumns className="text-slate-500 dark:text-slate-400" size={12} />
              <span className="text-xs text-slate-500 dark:text-slate-400">Cols:</span>
              <div className="flex rounded border border-slate-300 dark:border-slate-600 overflow-hidden">
                {COLUMN_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => handleColumnChange(opt.value as 2 | 3)}
                    className={`px-2 py-0.5 text-xs font-medium transition-colors ${
                      columnCount === opt.value
                        ? 'bg-blue-500 text-white'
                        : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
                  >
                    {opt.value}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </nav>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto">
        <form onSubmit={handleSubmit(onSubmit)} className="h-full">
          <div className="p-4">
            {/* Tab content - structured data display */}
            {mode === "view" ? (
              activeTab === "financial" ? (
                /* Full Financial Details Panel */
                <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
                  <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4 flex items-center gap-2">
                    <FaDollarSign size={16} className="text-green-500" />
                    Financial Details
                  </h3>
                  <CustomerFinancialPanel
                    customer={customerData.financial?.customer}
                    common={customerData.financial?.common}
                    currency="USD"
                    showAll={true}
                    columns={columnCount}
                  />
                </div>
              ) : (
                <CustomerDataPanel
                  data={getTabData(activeTab)}
                  showScalars={false}
                  grouped={false}
                  onSelectCategory={() => {}}
                />
              )
            ) : (
              <div className="space-y-4">
                {(
                  {
                    communication: [
                      { field: "contacts", label: "contacts" },
                      { field: "addresses", label: "addresses" },
                      { field: "domains", label: "domains" },
                      { field: "phones", label: "phones" },
                      { field: "emails", label: "emails" },
                    ],
                    financial: [{ field: "financial", label: "financial" }],
                    relations: [{ field: "relations", label: "relations" }],
                    documents: [{ field: "docs", label: "docs" }],
                    connections: [{ field: "connections", label: "connections" }],
                    data: [{ field: "data", label: "data" }],
                    metrics: [{ field: "metrics", label: "metrics" }],
                    gl_accounts: [{ field: "gl_accounts", label: "gl_accounts" }],
                  } as Record<
                    string,
                    Array<{ field: keyof CustomerFormValues; label: string }>
                  >
                )[activeTab]?.map(({ field, label }) => (
                  <JsonFieldEditor
                    key={String(field)}
                    label={label}
                    value={safeParseJson(
                      formData[field] as unknown as string | undefined,
                      JSON_DEFAULTS[String(field)],
                    )}
                    readonly={false}
                    defaultExpanded
                    maxHeight="520px"
                    onChange={(val) => {
                      setValue(
                        field,
                        JSON.stringify(val ?? JSON_DEFAULTS[String(field)], null, 2) as any,
                        { shouldDirty: true, shouldValidate: true },
                      );
                    }}
                  />
                )) ?? (
                  <div className="text-slate-400 text-sm">No editor for this tab.</div>
                )}
              </div>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
