import { useEffect, useMemo, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input, TextArea } from "../../../../../components/wrapper";

import { createCustomer, updateCustomer } from "../services/customerApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { FaChevronLeft, FaChevronRight, FaSave, FaTimes, FaEdit, FaTrash, FaBuilding, FaMapMarkerAlt, FaPhone, FaEnvelope, FaLink, FaDollarSign, FaFileAlt } from "react-icons/fa";
import { customerSchema } from "../utils/customerSchema";
import { CustomerAddProps } from "../types/customerType";
import Checkbox from "@/components/form/input/Checkbox";


// Dashboard-style containers for modular customer view
type CustomerFormValues = z.infer<typeof customerSchema>;

interface Customer {
  id?: number;
  display_name?: string;
  status?: string;
  org_type?: string;
  version?: number;
  is_active?: boolean;
  contacts?: string;
  locations?: string;
  domains?: string;
  phones?: string;
  emails?: string;
  docs?: string;
  connections?: string;
  relations?: string;
  financial?: string;
  data?: string;
  metrics?: string;
  gl_accounts?: string;
}

const JSON_DEFAULTS: Record<string, string> = {
  contacts: "[]",
  locations: "[]",
  domains: "[]",
  phones: "[]",
  emails: "[]",
  docs: "[]",
  connections: "{}",
  relations: "{}",
  financial: "{}",
  data: "{}",
  metrics: "{}",
  gl_accounts: "{}",
};

const JSON_FIELDS: Array<{ key: keyof CustomerFormValues; label: string; placeholder: string }> = [
  { key: "contacts", label: "Contacts", placeholder: "[]" },
  { key: "locations", label: "Locations", placeholder: "[]" },
  { key: "domains", label: "Domains", placeholder: "[]" },
  { key: "phones", label: "Phones", placeholder: "[]" },
  { key: "emails", label: "Emails", placeholder: "[]" },
  { key: "relations", label: "Relations", placeholder: "{}" },
  { key: "financial", label: "Financial", placeholder: "{}" },
  { key: "docs", label: "Documents", placeholder: "[]" },
  { key: "connections", label: "Connections", placeholder: "{}" },
  { key: "data", label: "Data", placeholder: "{}" },
  { key: "metrics", label: "Metrics", placeholder: "{}" },
  { key: "gl_accounts", label: "GL Accounts", placeholder: "{}" },
];

// Status Badge Component
const StatusBadge: React.FC<{ status?: string }> = ({ status }) => {
  const statusStyles: Record<string, string> = {
    active: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    inactive:
      "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
    pending:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    suspended:
      "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
    archived: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  };

  return (
    <span
      className={`px-2 py-1 text-xs font-medium rounded-full ${
        statusStyles[status?.toLowerCase() ?? "pending"] ?? statusStyles.pending
      }`}
    >
      {status?.replace("_", " ") ?? "pending"}
    </span>
  );
};

const formatLabel = (value: string) =>
  value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());

const isObjectValue = (value: unknown) =>
  typeof value === "object" && value !== null;

const renderScalarValue = (value: unknown) => {
  if (value === null || value === undefined || value === "") {
    return <span className="text-slate-400">—</span>;
  }
  return <span className="text-slate-800 dark:text-slate-200">{String(value)}</span>;
};

// Customer Header Component
const CustomerHeader: React.FC<{
  data: Customer;
}> = ({ data }) => {
  const contactsData = typeof data.contacts === "string" ? JSON.parse(data.contacts || "[]") : data.contacts || [];
  const locationsData = typeof data.locations === "string" ? JSON.parse(data.locations || "[]") : data.locations || [];
  const docsData = typeof data.docs === "string" ? JSON.parse(data.docs || "[]") : data.docs || [];

  return (
    <div className="space-y-6">
      {/* Customer Header Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Customer Details */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaBuilding className="text-blue-500" />
            Company Details
          </h3>
          <dl className="space-y-3 text-xs">
            <div className="flex justify-between items-center">
              <dt className="text-slate-500 dark:text-slate-400">Display Name</dt>
              <dd className="font-medium text-slate-900 dark:text-white">
                {data.display_name || "—"}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-slate-500 dark:text-slate-400">Org Type</dt>
              <dd className="font-medium text-slate-900 dark:text-white">
                {data.org_type?.toUpperCase() || "—"}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-slate-500 dark:text-slate-400">Version</dt>
              <dd className="font-medium text-slate-900 dark:text-white">
                {data.version || 1}
              </dd>
            </div>
          </dl>
        </div>

        {/* Center: Status & Quick Info */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
            Status
          </h3>
          <div className="space-y-4">
            <div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">
                Current Status
              </div>
              <StatusBadge status={data.status} />
            </div>
            <div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">
                Active
              </div>
              <span
                className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${
                  data.is_active
                    ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                    : "bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400"
                }`}
              >
                {data.is_active ? "Active" : "Inactive"}
              </span>
            </div>
          </div>
        </div>

        {/* Right: Summary Stats */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
            Summary
          </h3>
          <dl className="space-y-3 text-xs">
            <div className="flex justify-between items-center">
              <dt className="text-slate-500 dark:text-slate-400 flex items-center gap-1">
                <FaPhone size={12} /> Contacts
              </dt>
              <dd className="font-semibold text-slate-900 dark:text-white">
                {Array.isArray(contactsData) ? contactsData.length : 0}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-slate-500 dark:text-slate-400 flex items-center gap-1">
                <FaMapMarkerAlt size={12} /> Locations
              </dt>
              <dd className="font-semibold text-slate-900 dark:text-white">
                {Array.isArray(locationsData) ? locationsData.length : 0}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-slate-500 dark:text-slate-400 flex items-center gap-1">
                <FaFileAlt size={12} /> Documents
              </dt>
              <dd className="font-semibold text-slate-900 dark:text-white">
                {Array.isArray(docsData) ? docsData.length : 0}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex gap-2">
        <button
          type="button"
          className="px-4 py-2 text-xs font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors flex items-center gap-2"
        >
          <FaEnvelope size={14} />
          Email
        </button>
      </div>
    </div>
  );
};

export function CustomerDataPanel({ data }: { data: any }) {
  const entries = useMemo(() => Object.entries(data || {}), [data]);
  const [scalarEntries, objectEntries] = useMemo(() => {
    const scalars: Array<[string, unknown]> = [];
    const objects: Array<[string, unknown]> = [];
    entries.forEach(([key, value]) => {
      if (Array.isArray(value) || isObjectValue(value)) {
        objects.push([key, value]);
      } else {
        scalars.push([key, value]);
      }
    });
    return [scalars, objects];
  }, [entries]);

  if (!entries.length) {
    return (
      <section className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900/40">
        No customer data available.
      </section>
    );
  }

  return (
    <section className="grid gap-4 lg:grid-cols-2">
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Scalar Fields</h3>
          <span className="text-xs text-slate-400">{scalarEntries.length}</span>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {scalarEntries.map(([key, value]) => (
            <div
              key={key}
              className="rounded-xl border border-slate-100 bg-slate-50 p-3 shadow-sm dark:border-slate-800 dark:bg-slate-950"
            >
              <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                {formatLabel(key)}
              </div>
              <div className="mt-1 text-sm">{renderScalarValue(value)}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Object & List Fields</h3>
          <span className="text-xs text-slate-400">{objectEntries.length}</span>
        </div>
        <div className="space-y-3">
          {objectEntries.map(([key, value]) => (
            <details
              key={key}
              className="rounded-xl border border-slate-100 bg-slate-50 p-3 shadow-sm dark:border-slate-800 dark:bg-slate-950"
            >
              <summary className="cursor-pointer text-sm font-semibold text-slate-700 dark:text-slate-200">
                {formatLabel(key)}
              </summary>
              <pre className="mt-2 max-h-60 overflow-auto rounded-lg bg-white p-3 text-xs text-slate-600 shadow-inner dark:bg-slate-900 dark:text-slate-300">
                {JSON.stringify(value, null, 2)}
              </pre>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

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
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("summary");

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
    control,
    watch,
  } = useForm<CustomerFormValues>({
    resolver: zodResolver(customerSchema) as any,
    defaultValues: {
      is_active: false,
      version: 1,
      org_type: "customer",
      ...JSON_DEFAULTS,
    },
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;

  useEffect(() => {
    if (mode === "add") {
      reset({
        is_active: false,
        version: 1,
        org_type: "customer",
        ...JSON_DEFAULTS,
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
          setValue(key as keyof CustomerFormValues, JSON_DEFAULTS[key]);
        }
      });
    } else {
      reset({
        is_active: false,
        version: 1,
        org_type: "customer",
        ...JSON_DEFAULTS,
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

  const onSubmit = async (formData: CustomerFormValues) => {
    try {
      const jsonPayload: Record<string, any> = {};
      JSON_FIELDS.forEach(({ key, label }) => {
        const parsed = parseJsonField(label, formData[key] as string | undefined);
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
        if (onSaved) {
          onSaved();
        }
      }
    } catch (error: any) {
      dispatch(showToast({ message: error.message, type: "error" }));
    }
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
      return;
    }
    if (inline && onCancelInline) {
      onCancelInline();
      return;
    }
    navigate(-1);
  };

  // Tab definitions similar to OrderDetail
  const tabs = [
    { id: "summary", label: "Summary" },
    { id: "overview", label: "Overview" },
    { id: "contacts", label: "Contacts", icon: <FaPhone size={14} /> },
    { id: "locations", label: "Locations", icon: <FaMapMarkerAlt size={14} /> },
    { id: "domains", label: "Domains", icon: <FaLink size={14} /> },
    { id: "financial", label: "Financial", icon: <FaDollarSign size={14} /> },
    { id: "relations", label: "Relations" },
    { id: "documents", label: "Documents", icon: <FaFileAlt size={14} /> },
    { id: "connections", label: "Connections" },
    { id: "data", label: "Data" },
    { id: "metrics", label: "Metrics" },
    { id: "gl_accounts", label: "GL Accounts" },
  ];

  const formData = watch();
  const customerData: Customer = {
    ...formData,
    id: data?.id,
    display_name: formData.display_name,
    status: formData.status,
    org_type: formData.org_type,
    version: formData.version,
    is_active: formData.is_active,
  };

  return (
    <ComponentCard>
      {/* Header Section - Similar to OrderDetail */}
      {!inline && (
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-widest text-slate-400">
              Customer
            </div>
            <div className="text-lg font-semibold text-slate-800 dark:text-slate-100">
              {watch("display_name") || data?.display_name || "New Customer"}
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-full bg-white shadow border border-slate-200 px-2 py-1 dark:bg-slate-800 dark:border-slate-700">
            <button
              type="button"
              onClick={handleCancel}
              className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              title="Cancel"
            >
              <FaTimes className="text-slate-600 dark:text-slate-400" />
            </button>
            {mode === "view" ? (
              <>
                <button
                  type="button"
                  onClick={onEdit}
                  className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                  title="Edit"
                  disabled={!onEdit}
                >
                  <FaEdit className="text-slate-600 dark:text-slate-400" />
                </button>
                <button
                  type="button"
                  onClick={onDelete}
                  className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                  title="Delete"
                  disabled={!onDelete}
                >
                  <FaTrash className="text-rose-600 dark:text-rose-400" />
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={handleSubmit(onSubmit)}
                className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                title="Save"
                disabled={isSubmitting}
              >
                <FaSave className="text-slate-600 dark:text-slate-400" />
              </button>
            )}
            <button
              type="button"
              onClick={onPrev}
              className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors disabled:opacity-50"
              title="Previous"
              disabled={!onPrev}
            >
              <FaChevronLeft className="text-slate-600 dark:text-slate-400" />
            </button>
            <button
              type="button"
              onClick={onNext}
              className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors disabled:opacity-50"
              title="Next"
              disabled={!onNext}
            >
              <FaChevronRight className="text-slate-600 dark:text-slate-400" />
            </button>
          </div>
        </div>
      )}

      {/* Tab Navigation - Similar to OrderDetail */}
      <div className="flex items-center gap-2 py-2 border-b border-slate-200 dark:border-slate-700 mb-6 overflow-x-auto">
        <div className="flex min-w-max items-center gap-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`relative pb-2 text-sm font-semibold transition flex items-center gap-1 whitespace-nowrap ${
                activeTab === tab.id
                  ? "text-blue-600 dark:text-blue-400"
                  : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
              }`}
            >
              {tab.icon && tab.icon}
              {tab.label}
              {activeTab === tab.id && (
                <span className="absolute -bottom-2 left-0 right-0 h-0.5 rounded-full bg-blue-600 dark:bg-blue-400" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Summary Tab - Shows header like OrderDetail */}
        {activeTab === "summary" && (
          <div className="space-y-6">
            <CustomerHeader data={customerData} />
          </div>
        )}

        {/* Overview Tab - General information */}
        {activeTab === "overview" && (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <h3 className="mb-6 text-sm font-semibold text-slate-700 dark:text-slate-200">
              General Information
            </h3>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <Label htmlFor="display_name">Company Name</Label>
                <Input
                  type="text"
                  id="display_name"
                  placeholder="Company Name"
                  {...register("display_name")}
                  error={
                    errors.display_name && errors.display_name.message
                      ? true
                      : false
                  }
                  hint={errors.display_name && errors.display_name.message}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="status">Status</Label>
                <Input
                  type="text"
                  id="status"
                  placeholder="e.g., active, pending"
                  {...register("status")}
                  error={errors.status && errors.status.message ? true : false}
                  hint={errors.status && errors.status.message}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="org_type">Organization Type</Label>
                <Input
                  type="text"
                  id="org_type"
                  placeholder="customer"
                  {...register("org_type")}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="version">Version</Label>
                <Input
                  type="number"
                  id="version"
                  placeholder="1"
                  {...register("version", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
            </div>
            <div className="mt-6">
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

        {/* JSON Data Tabs */}
        {activeTab !== "summary" && activeTab !== "overview" && (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            {JSON_FIELDS.filter((field) => {
              if (activeTab === "documents") return field.key === "docs";
              return field.key === activeTab;
            }).map((field) => (
              <div key={field.key} className="space-y-2">
                <Label htmlFor={String(field.key)}>{field.label}</Label>
                <TextArea
                  register={register(field.key)}
                  rows={12}
                  placeholder={field.placeholder}
                  disabled={mode === "view"}
                />
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  JSON format expected. {field.placeholder === "[]" ? "Array" : "Object"}.
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Action Buttons */}
        {mode !== "view" && (
          <div className="flex items-center gap-2 justify-start pt-4 border-t border-slate-200 dark:border-slate-700">
            <button
              type="submit"
              className="flex items-center gap-2 px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-700 transition-colors font-medium text-sm"
              disabled={isSubmitting}
            >
              <FaSave size={14} />
              {mode === "edit" ? "Update Customer" : "Create Customer"}
            </button>
            {(inline || onCancel) && (
              <button
                type="button"
                onClick={handleCancel}
                className="flex items-center px-4 py-2 text-slate-700 dark:text-slate-300 bg-slate-200 dark:bg-slate-700 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600 transition-colors font-medium text-sm"
              >
                <FaTimes size={14} className="mr-2" />
                Cancel
              </button>
            )}
          </div>
        )}
      </form>
    </ComponentCard>
  );
}
