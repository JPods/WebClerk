import { useEffect, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createVendor, updateVendor } from "../services/vendorApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { FaDollarSign, FaPhone, FaUsers } from "react-icons/fa";
import { vendorSchema } from "../utils/vendorSchema";
import { VendorAddProps } from "../types/vendorType";
import Checkbox from "@/components/form/input/Checkbox";
import TransactionToolbar from "@/apps/transactions/components/TransactionToolbar";
import { 
  CommentsPanel,
  ActionsPanel,
  DocumentsPanel,
  MetadataPanel,
  RawDataPanel,
  CommunicationsPanel,
  FinancialSummaryPanel,
} from "@/apps/common/components/panels";
import { DetailTabs, useDetailTabs, useColumnCount, type TabConfig } from "@/components/common/DetailTabs";
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
  const currentUser = useAppSelector((state) => state.auth.user);
  const { activeTab, setActiveTab: handleTabChange } = useDetailTabs('vendor', 'overview');
  const { columnCount, setColumnCount: handleColumnChange } = useColumnCount('vendor', 3);
  const [isEditing, setIsEditing] = useState(false);

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
  const mode: "add" | "edit" | "view" = (baseMode === "view" && isEditing) ? "edit" : baseMode;
  const data = dataProp || routeState.data || null;

  // Additional tabs specific to Vendor
  const additionalTabs: TabConfig[] = [
    { id: 'communication', label: 'Contact', icon: <FaPhone size={14} /> },
    { id: 'financial', label: 'Financial', icon: <FaDollarSign size={14} /> },
    { id: 'relations', label: 'Relations', icon: <FaUsers size={14} /> },
  ];

  // Count badges for tabs
  const getCommentCount = () => {
    if (!data?.comments) return 0;
    const c = data.comments;
    return (c.public?.length || 0) + (c.process?.length || 0) + (c.partner?.length || 0) + (c.notes?.length || 0);
  };
  const getActionCount = () => data?.actions?.items?.filter((a: any) => a.status === 'pending').length || 0;
  const getDocumentCount = () => data?.refs?.links?.document?.length || 0;

  const tabBadges = {
    comments: getCommentCount(),
    actions: getActionCount(),
    documents: getDocumentCount(),
  };

  useEffect(() => {
    if (mode === "add") {
      reset();
    } else if (data) {
      Object.keys(data).forEach((key: any) => {
        if (data[key] !== undefined) {
          setValue(key, data[key]);
        }
      });
    } else {
      reset({});
    }
  }, [data, reset, setValue, mode]);

  const onSubmit = async (formData: z.infer<typeof vendorSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createVendor(formData)
          : await updateVendor({ ...formData, id: data && data.id });
      if (res) {
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

  // Vendor data for panels
  const vendorData = {
    ...data,
    id: data?.id,
    display_name: headerDisplayName,
    email: watch("email") || data?.email,
    phone: watch("phone") || data?.phone,
    status: watch("status") || data?.status,
    is_active: headerIsActive,
  };

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
          standardTabs={['overview', 'comments', 'actions', 'documents', 'history', 'raw']}
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

              {/* Comments Tab */}
              {activeTab === "comments" && data?.id && (
                <CommentsPanel
                  entityType="vendor"
                  entityId={data.id}
                  comments={data.comments}
                  isEditing={mode !== "view" || isEditing}
                  onChange={(comments) => console.log('Comments updated:', comments)}
                  currentUser={currentUser?.display_name || currentUser?.username}
                  currentUserId={currentUser?.id}
                />
              )}

              {/* Actions Tab */}
              {activeTab === "actions" && data?.id && (
                <ActionsPanel
                  entityType="vendor"
                  entityId={data.id}
                  data={data.actions?.items}
                  actionIds={data.actions?.ids}
                  isEditing={mode !== "view" || isEditing}
                  onChange={(actions) => console.log('Actions updated:', actions)}
                />
              )}

              {/* Documents Tab */}
              {activeTab === "documents" && data?.id && (
                <DocumentsPanel
                  parentType="vendor"
                  parentId={data.id}
                  data={data.refs?.links?.document}
                  isEditing={mode !== "view" || isEditing}
                  onChange={(docs) => console.log('Documents updated:', docs)}
                />
              )}

              {/* Communication Tab */}
              {activeTab === "communication" && data?.id && (
                <CommunicationsPanel
                  entityType="vendor"
                  entityId={data.id}
                  data={{
                    emails: data.refs?.links?.email || [],
                    phones: data.refs?.links?.phone || [],
                    addresses: data.refs?.links?.address || [],
                    domains: data.refs?.links?.domain || [],
                  }}
                  onChange={(comms) => console.log('Communications updated:', comms)}
                />
              )}

              {/* Financial Tab */}
              {activeTab === "financial" && data?.financial && (
                <FinancialSummaryPanel
                  customer={data.financial?.customer}
                  common={data.financial?.common}
                  currency="USD"
                  columns={columnCount}
                />
              )}

              {/* History Tab (Admin) */}
              {activeTab === "history" && data?.id && (
                <MetadataPanel
                  entityType="vendor"
                  entityId={data.id}
                  data={data.metadata}
                  isEditing={false}
                />
              )}

              {/* Raw Tab (Admin) */}
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
