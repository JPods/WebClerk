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
import { FaChevronLeft, FaChevronRight, FaSave, FaTimes, FaEdit, FaTrash } from "react-icons/fa";
import { customerSchema } from "../utils/customerSchema";
import { CustomerAddProps } from "../types/customerType";
import Checkbox from "@/components/form/input/Checkbox";


// Dashboard-style containers for modular customer view
type CustomerFormValues = z.infer<typeof customerSchema>;

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

function CustomerDataPanel({ data }: { data: any }) {
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
  const [activeTab, setActiveTab] = useState("overview");
  const [commOpen, setCommOpen] = useState(false);

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

  return (
    <>
      <ComponentCard>
        {!inline && (
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-xs font-semibold uppercase tracking-widest text-slate-400">Customer</div>
              <div className="text-lg font-semibold text-slate-800 dark:text-slate-100">
                {watch("display_name") || data?.display_name || "New Customer"}
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-full bg-white shadow border border-slate-200 px-2 py-1">
              <button
                type="button"
                onClick={handleCancel}
                className="p-2 rounded-full hover:bg-slate-100"
                title="Cancel"
              >
                <FaTimes className="text-slate-600" />
              </button>
              {mode === "view" ? (
                <>
                  <button
                    type="button"
                    onClick={onEdit}
                    className="p-2 rounded-full hover:bg-slate-100"
                    title="Edit"
                    disabled={!onEdit}
                  >
                    <FaEdit className="text-slate-600" />
                  </button>
                  <button
                    type="button"
                    onClick={onDelete}
                    className="p-2 rounded-full hover:bg-slate-100"
                    title="Delete"
                    disabled={!onDelete}
                  >
                    <FaTrash className="text-rose-600" />
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={handleSubmit(onSubmit)}
                  className="p-2 rounded-full hover:bg-slate-100"
                  title="Save"
                  disabled={isSubmitting}
                >
                  <FaSave className="text-slate-600" />
                </button>
              )}
              <button
                type="button"
                onClick={onPrev}
                className="p-2 rounded-full hover:bg-slate-100"
                title="Previous"
                disabled={!onPrev}
              >
                <FaChevronLeft className="text-slate-600" />
              </button>
              <button
                type="button"
                onClick={onNext}
                className="p-2 rounded-full hover:bg-slate-100"
                title="Next"
                disabled={!onNext}
              >
                <FaChevronRight className="text-slate-600" />
              </button>
            </div>
          </div>
        )}
        <div className="flex items-center gap-2 py-2">
          <div className="flex-1 overflow-x-auto h-14">
            <div className="flex min-w-max items-center gap-6">
              {[
                { id: "overview", label: "Overview" },
                { id: "snapshot", label: "Snapshot" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`relative pb-2 text-sm font-semibold transition ${
                    activeTab === tab.id
                      ? "text-indigo-600"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  {tab.label}
                  {activeTab === tab.id && (
                    <span className="absolute -bottom-2.5 left-0 right-0 h-0.5 rounded-full bg-indigo-600" />
                  )}
                </button>
              ))}

              {/* Communications grouped menu */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setCommOpen((v) => !v)}
                  className={`relative pb-2 text-sm font-semibold transition ${
                    ["contacts", "phones", "emails", "locations", "domains"].includes(activeTab)
                      ? "text-indigo-600"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  Communications
                  <span className="ml-2 text-xs">▾</span>
                  {commOpen && (
                    <div className="absolute left-0 top-full mt-2 w-40 rounded-md bg-white border border-gray-200 shadow-lg z-20 py-1">
                      {[
                        { id: "contacts", label: "Contacts" },
                        { id: "phones", label: "Phones" },
                        { id: "emails", label: "Emails" },
                        { id: "locations", label: "Addresses" },
                        { id: "domains", label: "Domains" },
                      ].map((sub) => (
                        <button
                          key={sub.id}
                          onClick={() => {
                            setActiveTab(sub.id);
                            setCommOpen(false);
                          }}
                          className={`w-full text-left px-3 py-2 text-sm ${activeTab === sub.id ? "bg-gray-100 text-indigo-600" : "text-gray-700 hover:bg-gray-50"}`}
                        >
                          {sub.label}
                        </button>
                      ))}
                    </div>
                  )}
                </button>
              </div>

              {/* Remaining tabs (collapsed to conserve space) */}
              {[
                { id: "relations", label: "Relations" },
                { id: "financial", label: "Financial" },
                { id: "documents", label: "Documents" },
                { id: "connections", label: "Connections" },
                { id: "data", label: "Data" },
                { id: "metrics", label: "Metrics" },
                { id: "gl_accounts", label: "GL Accounts" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`relative pb-2 text-sm font-semibold transition ${
                    activeTab === tab.id
                      ? "text-indigo-600"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  {tab.label}
                  {activeTab === tab.id && (
                    <span className="absolute -bottom-2.5 left-0 right-0 h-0.5 rounded-full bg-indigo-600" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="text-sm font-semibold text-slate-700 dark:text-slate-200">Snapshot</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">ID: {data?.id ?? "—"}</div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                {watch("status") || data?.status || "Unknown"}
              </span>
              <span className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-600 dark:border-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-200">
                {watch("org_type") || data?.org_type || "customer"}
              </span>
              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold ${watch("is_active") ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-rose-50 text-rose-700 border border-rose-200"}`}
              >
                {watch("is_active") ? "Active" : "Inactive"}
              </span>
              <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                v{watch("version") ?? data?.version ?? 1}
              </span>
            </div>
          </div>
        </div>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Customer"
                : mode === "view"
                ? "View Customer"
                : "Add New Customer"}
            </h3>
            {onCancelInline && (
              <button
                type="button"
                onClick={onCancelInline}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                &times;
              </button>
            )}
          </div>
        )}
        {/* ...existing customer form and logic... */}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {activeTab === "overview" && (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <h3 className="mb-4 text-sm font-semibold text-slate-700 dark:text-slate-200">General Information</h3>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <Label htmlFor="display_name">Company</Label>
                  <Input
                    type="text"
                    id="display_name"
                    placeholder="Company"
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
                    placeholder="Status"
                    {...register("status")}
                    error={errors.status && errors.status.message ? true : false}
                    hint={errors.status && errors.status.message}
                    disabled={mode === "view"}
                  />
                </div>
                <div>
                  <Label htmlFor="org_type">Org Type</Label>
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
              <div className="mt-4">
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
          {activeTab === "snapshot" && <CustomerDataPanel data={data} />}
          {activeTab !== "overview" && activeTab !== "snapshot" && (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
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
                  <p className="text-xs text-slate-400">JSON format expected.</p>
                </div>
              ))}
            </div>
          )}
          {mode !== "view" && (
            <div className="flex items-center gap-2">
              <button
                type="submit"
                className="flex items-center px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
              >
                {mode === "edit" ? "Update" : "Submit"}
              </button>
              {inline && onCancelInline && (
                <button
                  type="button"
                  onClick={onCancelInline}
                  className="flex items-center px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
                >
                  Cancel
                </button>
              )}
            </div>
          )}
        </form>
      </ComponentCard>
    </>
  );
}
