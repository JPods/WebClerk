import { useCallback, useEffect, useMemo, useState, type ComponentProps } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import DetailTabs from "@/components/common/DetailTabs";
import { createVendor, updateVendor } from "../services/vendorApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import {
  FaAddressCard,
  FaDollarSign,
  FaFileAlt,
  FaLink,
  FaQuestionCircle,
  FaSlidersH,
} from "react-icons/fa";
import { vendorSchema } from "../utils/vendorSchema";
import { VendorAddProps } from "../types/vendorType";
import Checkbox from "@/components/form/input/Checkbox";
import TransactionToolbar from "@/apps/common/components/TransactionToolbar";
import {
  ActionsPanel,
  CommentsPanel,
  DocumentsPanel,
  MetadataPanel,
  PrefsPanel,
  QAPanel,
  RawDataPanel,
  ContactPanel,
  RefsPanel,
  normalizeRefsLinksContact,
} from "@/apps/common/components/panels";
import { FinancialsPanel } from "@/apps/common/components/panels";
import { getRecord, saveRecord } from "@/api/wcapi";
import { useAppSelector } from "@/store/hooks";

export default function VendorDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: VendorAddProps) {
  const dispatch = useDispatch();
  const { user } = useAppSelector((state) => state.auth);
  const currentUser = useMemo(() => {
    if (!user) return "You";
    return `${user.name_first ?? ""}${user.name_last ?? ""}`.trim() || "You";
  }, [user]);

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors, isDirty, isSubmitting },
    reset,
    control,
    watch,
  } = useForm<z.infer<typeof vendorSchema>>({
    resolver: zodResolver(vendorSchema),
    defaultValues: { is_active: false, version: 1, org_type: "Vendor" },
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const baseMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";

  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [columnCount, setColumnCount] = useState<2 | 3>(3);

  const mode: "add" | "edit" | "view" = (baseMode === "view" && isEditing) ? "edit" : baseMode;
  const data = dataProp || routeState.data || null;
  const vendorData = data ?? {};

  const [panelRecord, setPanelRecord] = useState<any>(data ?? {});
  useEffect(() => {
    if (mode === "add") {
      reset();
      setPanelRecord({});
    } else if (data) {
      Object.keys(data).forEach((key: any) => {
        if (data[key] !== undefined) {
          setValue(key, data[key]);
        }
      });
      setPanelRecord(data);
    } else {
      reset({});
      setPanelRecord({});
    }
  }, [data, reset, setValue, mode]);

  const onSubmit = async (formData: z.infer<typeof vendorSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createVendor(formData)
          : await updateVendor({ ...formData, id: data && data.id });
      if (res) {
        const maybeRecord = (res as any)?.record ?? res;
        if (maybeRecord && typeof maybeRecord === "object") {
          setPanelRecord((prev: any) => ({ ...prev, ...maybeRecord }));
        }
        dispatch(
          showToast({
            message: `Vendor ${
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
    // If we're in local edit mode, just go back to view
    if (isEditing) {
      setIsEditing(false);
      if (data) reset(data);
      return;
    }
    if (inline && onCancelInline) {
      onCancelInline();
      return;
    }
    if (mode === "add") {
      reset();
    } else if (data) {
      reset(data);
    }
  };

  const headerDisplayName =
    watch("display_name") || data?.display_name || "New Vendor";
  const headerIsActive = Boolean(watch("is_active") ?? data?.is_active);
  const headerOrgType = watch("org_type") || data?.org_type || "Vendor";
  const headerVersion = watch("version") ?? data?.version ?? 1;

  const vendorId: number | undefined = panelRecord?.id ?? data?.id;
  const canEditPanels = mode !== "view" && !!vendorId;

  const handleVendorCommentsSave: NonNullable<
    ComponentProps<typeof CommentsPanel>["onSave"]
  > = async (newComments) => {
    if (!vendorId) return;

    const payload = {
      id: vendorId,
      comments: {
        ...(panelRecord?.comments ?? {}),
        ...newComments,
      },
    };

    const apiResult = await saveRecord("vendor", payload);
    const saved = (apiResult as any)?.record ?? apiResult;
    if (saved) setPanelRecord((prev: any) => ({ ...prev, ...saved }));
  };

  const handleVendorDocumentsChange = async (nextDocs: any[]) => {
    if (!vendorId) return;
    const nextRefs = {
      ...(panelRecord?.refs ?? {}),
      links: {
        ...(panelRecord?.refs?.links ?? {}),
        document: nextDocs,
      },
    };

    // Optimistic local update for snappy UI
    setPanelRecord((prev: any) => ({ ...prev, refs: nextRefs }));

    const apiResult = await saveRecord("vendor", {
      id: vendorId,
      refs: nextRefs,
    });
    const saved = (apiResult as any)?.record ?? apiResult;
    if (saved) setPanelRecord((prev: any) => ({ ...prev, ...saved }));
  };

  const handleVendorContactsRefresh = async () => {
    if (!vendorId) return;
    const apiResult = await getRecord("vendor", vendorId);
    const saved = (apiResult as any)?.record ?? apiResult;
    if (saved) setPanelRecord((prev: any) => ({ ...prev, ...saved }));
  };

  const handleVendorContactsChange = (nextContacts: any[]) => {
    // Convert RefContact[] (panel shape) -> refs.links.contact (API shape)
    const asArray = Array.isArray(nextContacts) ? nextContacts : [];
    const contactLinks = asArray
      .map((c: any) => {
        const normalizeField = (field: any) => {
          if (Array.isArray(field)) {
            return field.map((item: any, idx: number) => ({
              id: item?.id ?? idx,
              name: item?.name ?? "",
              value: item?.value ?? "",
            }));
          }
          if (typeof field === "string") {
            return field
              .split(",")
              .map((val, idx) => ({ id: idx, name: "", value: val.trim() }))
              .filter((x) => x.value);
          }
          return [];
        };

        const id = Number(c?.contact_id ?? c?.contact?.id ?? c?.id ?? 0);
        const purpose = String(c?.purpose ?? "");
        if (!id || !purpose) return null;

        const address = Array.isArray(c?.address)
          ? c.address.map((a: any, idx: number) => ({
              id: a?.id ?? idx,
              name: a?.name ?? "",
              full: a?.full ?? "",
            }))
          : typeof c?.full === "string" && c.full.trim()
            ? [{ id: 0, name: "", full: c.full }]
            : [];

        return {
          purpose,
          contact: {
            id,
            email: normalizeField(c?.email),
            phone: normalizeField(c?.phone),
            domain: normalizeField(c?.domain),
            address,
          },
        };
      })
      .filter(Boolean);

    setPanelRecord((prev: any) => ({
      ...prev,
      refs: {
        ...(prev?.refs ?? {}),
        links: {
          ...(prev?.refs?.links ?? {}),
          contact: contactLinks,
        },
      },
    }));
  };

  const handleVendorContactRemove = async (contactId: number) => {
    if (!vendorId) return;
    const existing = panelRecord?.refs?.links?.contact;
    const existingArray = Array.isArray(existing) ? existing : [];
    const filtered = existingArray.filter(
      (c: any) => Number(c?.contact?.id ?? c?.id ?? 0) !== Number(contactId),
    );

    const nextRefs = {
      ...(panelRecord?.refs ?? {}),
      links: {
        ...(panelRecord?.refs?.links ?? {}),
        contact: filtered,
      },
    };

    setPanelRecord((prev: any) => ({ ...prev, refs: nextRefs }));

    const apiResult = await saveRecord("vendor", {
      id: vendorId,
      refs: nextRefs,
    });
    const saved = (apiResult as any)?.record ?? apiResult;
    if (saved) setPanelRecord((prev: any) => ({ ...prev, ...saved }));
  };

  const handleTabChange = useCallback((tab: string) => setActiveTab(tab), []);
  const handleColumnChange = useCallback((c: 2 | 3) => setColumnCount(c), []);

  // Additional tabs (alphabetized) matching CustomerDetail pattern
  const additionalTabs = useMemo(
    () => [
      { id: "contacts", label: "Contacts", icon: <FaAddressCard size={14} /> },
      { id: "financial", label: "Financial", icon: <FaDollarSign size={14} /> },
      { id: "qa", label: "Q&A", icon: <FaQuestionCircle size={14} /> },
    ],
    [],
  );

  const tabBadges = useMemo(() => {
    const badges: Record<string, number> = {};
    const commentCount = Object.keys(panelRecord?.comments?.items ?? {}).length;
    if (commentCount) badges.comments = commentCount;
    const contactCount = (panelRecord?.refs?.links?.contact ?? []).length;
    if (contactCount) badges.contacts = contactCount;
    return badges;
  }, [panelRecord]);

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Vendor"
              : mode === "view"
              ? "View Vendor"
              : "Vendor Detail"
          }
        />
      )}

      <div className="h-full flex flex-col bg-white dark:bg-slate-900">
        {/* Header */}
        <div className="shrink-0 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="min-w-0 flex-1">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 truncate">
                <span className="mr-2 px-1.5 py-0.5 text-[10px] font-mono font-normal tracking-wide uppercase bg-indigo-100 text-indigo-600 dark:bg-indigo-900/40 dark:text-indigo-300 rounded">VendorDetail</span>
                {headerDisplayName}
                {data?.id && <span className="ml-2 text-sm font-normal text-slate-500 dark:text-slate-400">#{data.id}</span>}
              </h2>
              <div className="flex items-center gap-3 mt-1">
                <span
                  className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${
                    headerIsActive
                      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400"
                      : "bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400"
                  }`}
                >
                  {headerIsActive ? "Active" : "Inactive"}
                </span>
                <span className="text-sm text-slate-500 dark:text-slate-400">
                  {headerOrgType} • v{headerVersion}
                </span>
                {(mode === "edit" || mode === "add") && isDirty && (
                  <span className="px-3 py-1 text-xs font-medium text-amber-700 dark:text-amber-300 bg-amber-100 dark:bg-amber-900/30 rounded-full">
                    Unsaved changes
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 ml-4">
              {baseMode === "view" && !isEditing && (
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                >
                  Edit
                </button>
              )}
              {inline && onCancelInline && (
                <button
                  type="button"
                  onClick={onCancelInline}
                  className="px-3 py-2 text-sm font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600 rounded-lg transition-colors"
                  title="Close"
                >
                  Close
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Toolbar (edit/add mode) */}
        {(mode === "edit" || mode === "add") && (
          <div className="sticky top-0 z-20 mx-0 px-4 py-3 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm border-b border-slate-200 dark:border-slate-700">
            <TransactionToolbar
              transactionType="order"
              transactionId={data?.id}
              isDirty={isDirty}
              isSaving={isSubmitting}
              isEditing
              onSave={handleSubmit(async (fd) => {
                await onSubmit(fd);
                if (isEditing) setIsEditing(false);
              })}
              onSaveAndClose={
                (inline ? !!onCancelInline : false)
                  ? handleSubmit(async (fd) => {
                      await onSubmit(fd);
                      if (onCancelInline) onCancelInline();
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

        {/* Basic Information Panel (persistent) */}
        <div className="shrink-0 px-4 py-3 border-b border-slate-200 dark:border-slate-700">
          {mode === "view" ? (
            <div className={`grid grid-cols-1 ${columnCount === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2'} gap-4`}>
              <div><span className="text-sm text-slate-500">Name:</span> <span className="font-medium">{vendorData.display_name}</span></div>
              <div><span className="text-sm text-slate-500">Email:</span> <span className="font-medium">{vendorData.email || '—'}</span></div>
              <div><span className="text-sm text-slate-500">Phone:</span> <span className="font-medium">{vendorData.phone || '—'}</span></div>
            </div>
          ) : (
            <div className={`grid grid-cols-1 ${columnCount === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2'} gap-4`}>
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
                <Label htmlFor="email">Email</Label>
                <Input
                  type="email"
                  id="email"
                  placeholder="Primary email"
                  {...register("email")}
                  error={!!errors.email}
                  hint={errors.email?.message}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="phone">Phone</Label>
                <Input
                  type="tel"
                  id="phone"
                  placeholder="Primary phone"
                  {...register("phone")}
                  error={!!errors.phone}
                  hint={errors.phone?.message}
                  className="mt-1"
                />
              </div>
            </div>
          )}
        </div>

        {/* Tab Navigation */}
        <DetailTabs
          entityType="vendor"
          activeTab={activeTab}
          onTabChange={handleTabChange}
          standardTabs={['actions', 'comments', 'documents', 'overview', 'raw']}
          additionalTabs={additionalTabs}
          badges={tabBadges}
          showColumnSelector={true}
          columnCount={columnCount}
          onColumnCountChange={handleColumnChange}
        />

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto">
          <form onSubmit={handleSubmit(onSubmit)} className="h-full">
            <div className="p-4">
              {/* Overview Tab - Additional fields */}
              {activeTab === "overview" && (
                <div className={`grid grid-cols-1 ${columnCount === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2'} gap-4`}>
                  <div>
                    <Label htmlFor="attention">Attention</Label>
                    <Input
                      type="text"
                      id="attention"
                      placeholder="Attn: line for mailing"
                      {...register("attention")}
                      error={!!errors.attention}
                      hint={errors.attention?.message}
                      disabled={mode === "view"}
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
                      error={!!errors.status}
                      hint={errors.status?.message}
                      disabled={mode === "view"}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="price_level">Price Level</Label>
                    <Input
                      type="text"
                      id="price_level"
                      placeholder="e.g. retail, wholesale"
                      {...register("price_level")}
                      error={!!errors.price_level}
                      hint={errors.price_level?.message}
                      disabled={mode === "view"}
                      className="mt-1"
                    />
                  </div>
                  <div className="flex items-center pt-6">
                    <Controller
                      name="is_active"
                      control={control}
                      render={({ field }) => (
                        <Checkbox
                          id="is_active"
                          checked={field.value ?? false}
                          onChange={field.onChange}
                          label="Active"
                          disabled={mode === "view"}
                        />
                      )}
                    />
                  </div>
                </div>
              )}

              {/* Actions Tab */}
              {activeTab === "actions" && data?.id && (
                <ActionsPanel
                  entityType="vendor"
                  entityId={data.id}
                  data={data.actions?.items}
                  actionIds={data.actions?.ids}
                  isEditing={mode !== "view" || isEditing}
                  onChange={(actions: any) => console.log('Actions updated:', actions)}
                />
              )}

              {/* Comments Tab */}
              {activeTab === "comments" && (
                <CommentsPanel
                  entityType="vendor"
                  entityId={vendorId ?? 0}
                  comments={panelRecord?.comments}
                  isEditing={canEditPanels}
                  onChange={(next) =>
                    setPanelRecord((prev: any) => ({ ...prev, comments: next }))
                  }
                  onSave={canEditPanels ? handleVendorCommentsSave : undefined}
                  currentUser={currentUser}
                  currentUserId={user?.id}
                  message={!vendorId ? "Save vendor to add comments" : undefined}
                />
              )}

              {/* Contacts Tab */}
              {activeTab === "contacts" && (
                <>
                  {!vendorId && (
                    <div className="text-sm text-slate-500 dark:text-slate-400 italic mb-4">
                      Save vendor to manage linked contacts
                    </div>
                  )}
                  <ContactPanel
                    parent_model="vendor"
                    parentId={vendorId}
                    contacts={normalizeRefsLinksContact(
                      panelRecord?.refs?.links?.contact ?? [],
                    )}
                    isEditing={canEditPanels}
                    onChange={handleVendorContactsChange}
                    onRemove={canEditPanels ? handleVendorContactRemove : undefined}
                    onSaveSuccess={handleVendorContactsRefresh}
                  />
                </>
              )}

              {/* Documents Tab */}
              {activeTab === "documents" && (
                <DocumentsPanel
                  parent_model="vendor"
                  parentId={vendorId}
                  data={panelRecord?.refs?.links?.document ?? []}
                  readOnly={!canEditPanels}
                  onChange={canEditPanels ? handleVendorDocumentsChange : undefined}
                />
              )}

              {/* Financial Tab */}
              {activeTab === "financial" && data?.financial && (
                <FinancialsPanel
                  totals={data.financial?.totals}
                  cost={data.financial?.cost}
                  sell={data.financial?.sell}
                  currency="USD"
                />
              )}

              {/* Q&A Tab */}
              {activeTab === "qa" && (
                <QAPanel
                  parent_model="vendor"
                  parentId={Number(vendorId ?? 0)}
                  data={panelRecord?.data}
                />
              )}

              {/* Raw Tab */}
              {activeTab === "raw" && data?.id && (
                <RawDataPanel
                  entityType="vendor"
                  entityId={data.id}
                  data={data}
                />
              )}

              {/* Empty state for tabs without data */}
              {!data?.id && activeTab !== "overview" && (
                <div className="text-center py-8 text-slate-500 dark:text-slate-400">
                  Save the vendor first to access {activeTab} features.
                </div>
              )}
            </div>
          </form>
        </div>
      </div>
    </>
  );
}