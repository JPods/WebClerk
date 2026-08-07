/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";
import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { DevBadge } from "@/components/common/DevBadge";
import {
  createManufacturer,
  updateManufacturer,
} from "../services/manufacturerApi";
import {
  getRecord,
  getRecords,
  getContactOptions,
  getProjectOptions,
} from "@/api/wcapi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { FaAddressCard, FaQuestionCircle } from "react-icons/fa";
import { manufacturerSchema } from "../utils/manufacturerSchema";
import { ManufacturerAddProps } from "../types/manufacturerType";
import Checkbox from "@/components/form/input/Checkbox";
import TransactionToolbar from "@/apps/common/components/TransactionToolbar";
import {
  BasicInformationPanel,
  normalizeRefsLinksContact,
  CoreTabPanel,
} from "@/apps/common/components/panels";
import {
  useDetailTabs,
  useColumnCount,
  ColumnSelector,
} from "@/components/common/DetailTabs";
import { useAppSelector } from "@/store/hooks";
import { PageRoutes } from "../../../../../routes/Routes";
import { dynamicData } from "../../../../../type/dynamicData";
import { withDevIdentifier } from "@/components/common/DevIdentifier";

type ManufacturerFormValues = z.infer<typeof manufacturerSchema>;

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

const VALID_TABS = [
  "actions",
  "comments",
  "contacts",
  "documents",
  "qa",
  "raw",
];

export const MANUFACTURER_STANDARD_TABS = [
  "actions",
  "comments",
  "documents",
  "raw",
];

export const MANUFACTURER_ADDITIONAL_TABS = [
  { id: "contacts", label: "Contacts", icon: <FaAddressCard size={14} /> },
  { id: "qa", label: "Q&A", icon: <FaQuestionCircle size={14} /> },
];

export const buildManufacturerTabBadges = (
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
  const getDocumentCount = () =>
    data?.refs?.links?.document?.length || 0;
  return {
    comments: getCommentCount(),
    actions: getActionCount(),
    documents: getDocumentCount(),
    contacts: fkContacts.length,
  };
};

function ManufacturerDetail({
  modeProp,
  dataProp,
  hideBreadcrumb: _hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ManufacturerAddProps) {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const currentUser = useAppSelector((state) => state.auth.user);

  const { activeTab, setActiveTab: handleTabChange } = useDetailTabs(
    "manufacturer",
    "actions",
    VALID_TABS,
  );
  const { columnCount, setColumnCount: handleColumnChange } = useColumnCount(
    "manufacturer",
    3,
  );

  const [isEditing, setIsEditing] = useState(false);
  const [fetchedRecord, setFetchedRecord] = useState<dynamicData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fkContacts, setFkContacts] = useState<
    ReturnType<typeof normalizeRefsLinksContact>
  >([]);
  const [fkContactsLoading, setFkContactsLoading] = useState(false);
  const [fkRefreshTrigger, setFkRefreshTrigger] = useState(0);
  const [contactOptions, setContactOptions] = useState<
    Array<{ id: string; label: string }>
  >([]);
  const [projectOptions, setProjectOptions] = useState<
    Array<{ id: string; name?: string; intent?: string }>
  >([]);

  const routeMode = useMemo(() => {
    const path = location.pathname;
    if (path.includes("/manufacturer/add")) return "add";
    if (path.includes("/manufacturer/edit/")) return "edit";
    if (path.includes("/manufacturer/detail/")) return "view";
    return "view";
  }, [location.pathname]);

  const manufacturerId = Number(id);

  const resolvedManufacturerId = useMemo(() => {
    if (Number.isFinite(manufacturerId) && manufacturerId > 0)
      return manufacturerId;
    const fromData = dataProp?.id ?? fetchedRecord?.id;
    return fromData ? Number(fromData) : 0;
  }, [manufacturerId, dataProp, fetchedRecord]);

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors, isDirty, isSubmitting },
    reset,
    control,
    watch,
  } = useForm<ManufacturerFormValues>({
    resolver: zodResolver(manufacturerSchema) as any,
    defaultValues: { is_active: false, version: 1, org_type: "manufacturer" },
  });

  const formData = watch();
  const routeState = (location.state as any) || {};
  const baseMode: "add" | "edit" | "view" =
    modeProp ||
    routeMode ||
    (routeState.mode as "add" | "edit" | "view") ||
    "add";
  const mode: "add" | "edit" | "view" =
    baseMode === "view" && isEditing ? "edit" : baseMode;

  const data = useMemo(() => {
    if (fetchedRecord) return fetchedRecord as any;
    if (dataProp) return dataProp as any;
    return routeState.data || null;
  }, [dataProp, fetchedRecord, routeState.data]);

  const tabBadges = useMemo(
    () => buildManufacturerTabBadges(data, fkContacts),
    [data, fkContacts],
  );

  // ── Data loading ──────────────────────────────────────────────────────────

  useEffect(() => {
    if (dataProp) return;
    if (modeProp === "add" || routeMode === "add") return;
    if (!Number.isFinite(manufacturerId) || manufacturerId <= 0) return;
    setLoading(true);
    setError(null);
    getRecord("manufacturer", manufacturerId)
      .then((res: any) => {
        const record = res?.record ?? res;
        setFetchedRecord(record || null);
      })
      .catch((err) =>
        setError(err?.message || "Failed to load manufacturer."),
      )
      .finally(() => setLoading(false));
  }, [manufacturerId, dataProp, routeMode, modeProp]);

  useEffect(() => {
    getContactOptions()
      .then((opts) => setContactOptions(opts as any))
      .catch(() => {});
  }, []);

  useEffect(() => {
    getProjectOptions()
      .then((opts) => setProjectOptions(opts as any))
      .catch(() => {});
  }, []);

  // ── FK contacts ───────────────────────────────────────────────────────────

  const fetchFkContacts = useCallback(async (mId: number) => {
    if (!Number.isFinite(mId) || mId <= 0) return;
    setFkContactsLoading(true);
    try {
      const res = await getRecords("contact", { manufacturer: mId });
      const mapped = (res?.results ?? []).map((r: any) => ({
        contact_id: r.id,
        purpose: r.purpose || "",
        attention: r.attention || "",
        email: r.email || "",
        phone: r.phone || "",
        full: r.display_name || r.full || "",
      }));
      setFkContacts(mapped);
    } catch (err) {
      console.error("[ManufacturerDetail] FK contact fetch failed:", err);
    } finally {
      setFkContactsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (modeProp === "add" || routeMode === "add") return;
    fetchFkContacts(resolvedManufacturerId);
  }, [
    resolvedManufacturerId,
    routeMode,
    fetchFkContacts,
    fkRefreshTrigger,
    modeProp,
  ]);

  // ── Form sync ─────────────────────────────────────────────────────────────

  useEffect(() => {
    if (mode === "add") {
      reset({
        is_active: false,
        version: 1,
        org_type: "manufacturer",
        ...Object.fromEntries(
          Object.entries(JSON_DEFAULTS).map(([k, v]) => [k, JSON.stringify(v)]),
        ),
      });
      return;
    }
    if (data) {
      Object.keys(data).forEach((key) => {
        if (key in JSON_DEFAULTS) {
          setValue(
            key as keyof ManufacturerFormValues,
            JSON.stringify(
              data[key] ?? JSON_DEFAULTS[key],
              null,
              2,
            ) as any,
          );
        } else if (data[key] !== undefined) {
          setValue(key as keyof ManufacturerFormValues, data[key]);
        }
      });
    } else {
      reset({ is_active: false, version: 1, org_type: "manufacturer" });
    }
  }, [data, mode, reset, setValue]);

  // ── Save ──────────────────────────────────────────────────────────────────

  const onSubmit = async (fd: ManufacturerFormValues) => {
    try {
      const payload: any = { ...fd };
      Object.keys(JSON_DEFAULTS).forEach((key) => {
        if (key in payload && typeof payload[key] === "string") {
          try {
            payload[key] = JSON.parse(payload[key]);
          } catch {
            payload[key] = JSON_DEFAULTS[key];
          }
        }
      });
      if (mode === "add") {
        await createManufacturer(payload);
        dispatch(
          showToast({ message: "Manufacturer created", type: "success" }),
        );
        if (onSaved) onSaved();
        if (!inline) navigate(PageRoutes.manufacturerList);
      } else {
        await updateManufacturer({ ...payload, id: data?.id });
        const refreshed = await getRecord("manufacturer", data.id);
        const next = (refreshed as any)?.record ?? refreshed;
        if (next) setFetchedRecord(next as any);
        dispatch(
          showToast({ message: "Manufacturer saved", type: "success" }),
        );
        if (onSaved) onSaved();
        setIsEditing(false);
      }
    } catch (err: any) {
      dispatch(
        showToast({ message: err.message || "Save failed", type: "error" }),
      );
    }
  };

  const handleCancel = () => {
    if (inline && onCancelInline) {
      onCancelInline();
      return;
    }
    if (isEditing) {
      setIsEditing(false);
      return;
    }
    if (mode === "add") reset();
    else if (data) reset(data);
  };

  // ── Set primary contact ───────────────────────────────────────────────────

  const handleSetPrimary = useCallback(
    async (contact: {
      contact_id: number;
      attention?: string;
      email?: string | any[];
      phone?: string | any[];
    }) => {
      const recId = data?.id;
      if (!recId) return;
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
        await updateManufacturer({
          id: recId,
          contact_id: contact.contact_id,
          attention: contact.attention || null,
          email: emailStr || null,
          phone: phoneStr || null,
        } as any);
        setValue(
          "contact_id" as keyof ManufacturerFormValues,
          contact.contact_id,
        );
        if (contact.attention)
          setValue(
            "attention" as keyof ManufacturerFormValues,
            contact.attention as any,
          );
        if (emailStr)
          setValue(
            "email" as keyof ManufacturerFormValues,
            emailStr as any,
          );
        if (phoneStr)
          setValue(
            "phone" as keyof ManufacturerFormValues,
            phoneStr as any,
          );
        const res = await getRecord("manufacturer", recId);
        const rec = (res as any)?.record ?? res;
        if (rec) setFetchedRecord(rec);
        dispatch(
          showToast({
            message: `Contact #${contact.contact_id} set as primary`,
            type: "success",
          }),
        );
      } catch (err) {
        console.error("[ManufacturerDetail.handleSetPrimary] failed:", err);
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

  // ── Display data ─────────────────────────────────────────────────────────

  const manufacturerData = useMemo(() => {
    if (mode === "view" && data) return data;
    return {
      id: data?.id,
      display_name: formData.display_name ?? data?.display_name,
      status: formData.status ?? data?.status,
      org_type: formData.org_type ?? data?.org_type ?? "manufacturer",
      version: formData.version ?? data?.version ?? 1,
      is_active: formData.is_active ?? data?.is_active ?? false,
      attention: (formData as any).attention ?? data?.attention,
      email: formData.email ?? data?.email,
      phone: (formData as any).phone ?? data?.phone,
      price_level: (formData as any).price_level ?? data?.price_level,
      contact_id: (formData as any).contact_id ?? data?.contact_id,
    };
  }, [mode, data, formData]);

  if (loading && !dataProp) {
    return (
      <div className="flex items-center justify-center h-32 text-slate-500">
        Loading…
      </div>
    );
  }
  if (error && !data) {
    return (
      <div className="flex items-center justify-center h-32 text-red-500">
        {error}
      </div>
    );
  }
  if (mode !== "add" && !data && !dataProp) {
    return (
      <div className="flex items-center justify-center h-32 text-slate-400">
        No manufacturer data found.
      </div>
    );
  }

  return (
    <>
      {!_hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Manufacturer"
              : mode === "view"
                ? "View Manufacturer"
                : "New Manufacturer"
          }
        />
      )}

      <div className="h-full flex flex-col bg-white dark:bg-slate-900">
        {/* ── Header ──────────────────────────────────────────────────── */}
        <div className="shrink-0 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="min-w-0 flex-1">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 truncate">
                <DevBadge label="ManufacturerDetail" className="mr-2" />
                {manufacturerData.display_name || "New Manufacturer"}
              </h2>
              <div className="flex items-center gap-3 mt-1">
                <span
                  className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${
                    manufacturerData.is_active
                      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400"
                      : "bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400"
                  }`}
                >
                  {manufacturerData.is_active ? "Active" : "Inactive"}
                </span>
                <span className="text-sm text-slate-500 dark:text-slate-400">
                  {manufacturerData.org_type || "manufacturer"} • v
                  {manufacturerData.version ?? 1}
                </span>
                {(mode === "edit" || mode === "add") && isDirty && (
                  <span className="px-3 py-1 text-xs font-medium text-amber-700 dark:text-amber-300 bg-amber-100 dark:bg-amber-900/30 rounded-full">
                    Unsaved changes
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 ml-4">
              {mode === "view" && !isEditing && data?.id && (
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  className="px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400 rounded-lg transition-colors"
                >
                  Edit
                </button>
              )}
              {inline && onCancelInline && (
                <button
                  type="button"
                  onClick={onCancelInline}
                  className="px-3 py-2 text-sm font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600 rounded-lg transition-colors"
                >
                  Close
                </button>
              )}
            </div>
          </div>
        </div>

        {/* ── Toolbar ──────────────────────────────────────────────────── */}
        {(mode === "edit" || mode === "add") && (
          <div className="sticky top-0 z-20 px-4 py-3 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm border-b border-slate-200 dark:border-slate-700">
            <TransactionToolbar
              transactionType="order"
              transactionId={data?.id}
              isDirty={isDirty}
              isSaving={isSubmitting}
              isEditing
              onSave={handleSubmit(onSubmit as any)}
              onSaveAndClose={
                inline && onCancelInline
                  ? handleSubmit(async (fd: any) => {
                      await onSubmit(fd);
                      onCancelInline();
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

        {/* ── Basic Information Panel ───────────────────────────────────── */}
        <div className="shrink-0">
          <BasicInformationPanel
            data={manufacturerData}
            columns={columnCount}
          />
        </div>

        {/* ── Form fields (edit / add) ─────────────────────────────────── */}
        {(mode === "edit" || mode === "add") && (
          <div className="shrink-0 border-b border-slate-200 dark:border-slate-700 px-4 py-3">
            <form className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              <div>
                <Label htmlFor="display_name">Display Name *</Label>
                <Input
                  type="text"
                  id="display_name"
                  placeholder="Display Name"
                  {...register("display_name")}
                  error={!!errors.display_name}
                  hint={errors.display_name?.message}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="status">Status</Label>
                <Input
                  type="text"
                  id="status"
                  placeholder="Status"
                  {...register("status")}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="attention">Attention</Label>
                <Input
                  type="text"
                  id="attention"
                  placeholder="Attention"
                  {...register("attention")}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="email">Email</Label>
                <Input
                  type="email"
                  id="email"
                  placeholder="Email"
                  {...register("email")}
                  error={!!errors.email}
                  hint={errors.email?.message}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="phone">Phone</Label>
                <Input
                  type="text"
                  id="phone"
                  placeholder="Phone"
                  {...register("phone")}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="price_level">Price Level</Label>
                <Input
                  type="text"
                  id="price_level"
                  placeholder="Price Level"
                  {...register("price_level")}
                  className="mt-1"
                />
              </div>
              <div className="flex items-center mt-4">
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
            </form>
          </div>
        )}

        {/* ── Column selector ───────────────────────────────────────────── */}
        <div className="flex items-center py-2 px-4 gap-4">
          <ColumnSelector value={columnCount} onChange={handleColumnChange} />
        </div>

        {/* ── Related Tabs ─────────────────────────────────────────────── */}
        {mode !== "add" && (
          <div className="space-y-2 px-4 py-2">
            <CoreTabPanel
              entityType="manufacturer"
              activeTab={activeTab}
              onTabChange={handleTabChange}
              standardTabs={MANUFACTURER_STANDARD_TABS as Array<
                "actions" | "comments" | "documents" | "raw"
              >}
              additionalTabs={MANUFACTURER_ADDITIONAL_TABS}
              tabBadges={tabBadges}
              showColumnSelector
              columnCount={columnCount}
              onColumnCountChange={(count) => handleColumnChange(count as 2 | 3)}
              data={data}
              entityId={data?.id || 0}
              mode={mode}
              isEditing={isEditing}
              onSaveComments={async (comments) => {
                if (!data?.id) return;
                await updateManufacturer({
                  id: data.id,
                  comments: { mode: "update", value: comments },
                } as any);
              }}
              onSaveActions={async (actions) => {
                if (!data?.id) return;
                await updateManufacturer({
                  id: data.id,
                  actions,
                } as any);
              }}
              onRefreshRecord={async () => {
                if (!data?.id) return;
                const refreshed = await getRecord("manufacturer", data.id);
                const next = (refreshed as any)?.record ?? refreshed;
                if (next) setFetchedRecord(next as any);
              }}
              onRecordChange={(patch) =>
                setFetchedRecord(
                  (prev) =>
                    ({ ...(prev || data || {}), ...patch } as any),
                )
              }
              fkContacts={fkContacts}
              fkContactsLoading={fkContactsLoading}
              orgDisplayName={manufacturerData.display_name}
              primaryContactId={data?.contact_id}
              onSetPrimary={handleSetPrimary}
              onRefreshContacts={() => setFkRefreshTrigger((n) => n + 1)}
              onContactsChange={() => {
                /* Contacts linked via FK; refs not tracked in form */
              }}
              onContactSaveSuccess={() => {
                setFkRefreshTrigger((n) => n + 1);
                if (data?.id) {
                  getRecord("manufacturer", data.id)
                    .then((res: any) => {
                      const rec = res?.record ?? res;
                      if (rec) setFetchedRecord(rec);
                    })
                    .catch(() => {});
                }
              }}
              contactOptions={contactOptions}
              projectOptions={projectOptions}
              currentUser={
                currentUser
                  ? {
                      id:
                        typeof currentUser.id === "number"
                          ? currentUser.id
                          : Number(currentUser.id) || undefined,
                      name_first: currentUser.name_first,
                      name_last: currentUser.name_last,
                    }
                  : undefined
              }
            />
          </div>
        )}
      </div>
    </>
  );
}

export function ManufacturerDetailPage() {
  return <ManufacturerDetail />;
}

export default withDevIdentifier(ManufacturerDetail, "ManufacturerDetail", 'indigo', 'apps/orgs/models/manufacturer/pages/ManufacturerDisplay.tsx');
