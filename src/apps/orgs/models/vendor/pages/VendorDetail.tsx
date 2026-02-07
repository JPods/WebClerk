import { useEffect } from "react";
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
import { vendorSchema } from "../utils/vendorSchema";
import { VendorAddProps } from "../types/vendorType";
import Checkbox from "@/components/form/input/Checkbox";
import TransactionToolbar from "@/apps/transactions/components/TransactionToolbar";

export default function VendorDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: VendorAddProps) {
  const dispatch = useDispatch();

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
  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;
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
        <div className="shrink-0 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="min-w-0 flex-1">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 truncate">
                {headerDisplayName}
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
            {inline && onCancelInline && (
              <button
                type="button"
                onClick={onCancelInline}
                className="ml-4 px-3 py-2 text-sm font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600 rounded-lg transition-colors"
                title="Close"
              >
                Close
              </button>
            )}
          </div>
        </div>

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
              })}
              onSaveAndClose={
                inline && onCancelInline
                  ? handleSubmit(async (fd) => {
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

        <div className="flex-1 overflow-y-auto">
          <form onSubmit={handleSubmit(onSubmit)} className="h-full">
            <div className="p-4 space-y-4">
              <div>
                <Label htmlFor="display_name">Display Name</Label>
                <Input
                  type="text"
                  id="display_name"
                  placeholder="Display Name"
                  {...register("display_name")}
                  error={!!errors.display_name}
                  hint={errors.display_name?.message}
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

              <div className="flex items-center">
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
          </form>
        </div>
      </div>
    </>
  );
}
