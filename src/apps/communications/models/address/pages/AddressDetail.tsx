/**
 * AddressDetail.tsx
 *
 * Standard Address Detail page following the enterprise UI pattern (matches ContactDetail):
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

import { useEffect, useState, useCallback } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { FaEdit, FaMapMarkerAlt, FaPlus, FaTrash } from "react-icons/fa";

// UI primitives
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import { CustTextArea } from "@/components/wrapper";
import { DevBadge } from "@/components/common/DevBadge";

// Tab navigation
import { useColumnCount } from "@/components/common/DetailTabs";

// Toolbar
import TransactionToolbar from "@/apps/common/components/TransactionToolbar";
// Panel Components
//import ContactLinksPanel from "@/apps/transactions/components/ContactPanel";
import { ScalarCard, BaseModelCards } from "@/apps/common/components/detail";
// API & State
import {
  createAddress,
  updateAddress,
  deleteAddress,
} from "../services/addressApi";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { addressSchema } from "../utils/addressSchema";
import { AddressAddProps } from "../types/addressType";
import { withDevIdentifier } from '@/components/common/DevIdentifier';
//import { ColumnSelector } from "@/components/common/DetailTabs";
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
// Main Component
// ---------------------------------------------------------------------------

function AddressDetail({
  modeProp,
  dataProp,
  hideBreadcrumb: _hideBreadcrumb,
  onSaved,
  inline: _inline = false,
  onCancelInline,
}: AddressAddProps) {
  const dispatch = useDispatch();
  const location = useLocation();
  const navigate = useNavigate();
  const routeState = (location.state as any) || {};

  // ---------------------------------------------------------------------------
  // Mode
  // ---------------------------------------------------------------------------

  const initialMode: "add" | "edit" | "view" =
    modeProp || routeState.mode || "add";
  const [effectiveMode, setEffectiveMode] = useState<"add" | "edit" | "view">(
    initialMode,
  );
  const isEditing = effectiveMode === "edit" || effectiveMode === "add";

  // ---------------------------------------------------------------------------
  // Data
  // ---------------------------------------------------------------------------

  const data = dataProp || routeState.data || null;
  const activeAddressId = data?.id || null;

  // ---------------------------------------------------------------------------
  // Form
  // ---------------------------------------------------------------------------

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors, isDirty, isSubmitting },
    reset,
  } = useForm<z.infer<typeof addressSchema>>({
    resolver: zodResolver(addressSchema),
  });

  useEffect(() => {
    if (effectiveMode === "add") {
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
  }, [data, reset, setValue, effectiveMode]);

  // ---------------------------------------------------------------------------
  // Tab Navigation
  // ---------------------------------------------------------------------------
  const { columnCount, setColumnCount } = useColumnCount("address", 3);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const onSubmit = async (formData: z.infer<typeof addressSchema>) => {
    try {
      const res =
        effectiveMode === "add"
          ? await createAddress(formData)
          : await updateAddress({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Address ${
              effectiveMode === "add" ? "created" : "updated"
            } successfully`,
            type: "success",
          }),
        );
        if (onSaved) {
          onSaved();
        }
      }
    } catch (error: any) {
      dispatch(showToast({ message: error.message, type: "error" }));
    }
  };

  const handleCancel = useCallback(() => {
    if (onCancelInline) {
      onCancelInline();
    } else if (initialMode === "add") {
      navigate(-1);
    } else {
      if (data) {
        Object.keys(data).forEach((key: any) => {
          if (data[key] !== undefined) {
            setValue(key, data[key]);
          }
        });
      }
      setEffectiveMode("view");
    }
  }, [onCancelInline, initialMode, navigate, data, setValue]);

  // ---------------------------------------------------------------------------
  // Delete Handler
  // ---------------------------------------------------------------------------

  const handleDeleteAddress = useCallback(async () => {
    const addressId = data?.id;
    if (!addressId) return;
    if (!window.confirm(`Delete address #${addressId}?`)) return;

    try {
      await deleteAddress(addressId);
      dispatch(
        showToast({
          message: `Address #${addressId} deleted`,
          type: "success",
        }),
      );
      if (onSaved) onSaved();
      if (onCancelInline) {
        onCancelInline();
      } else {
        navigate(-1);
      }
    } catch (err) {
      dispatch(
        showToast({
          message: `Failed to delete address: ${err}`,
          type: "error",
        }),
      );
    }
  }, [data?.id, dispatch, onSaved, onCancelInline, navigate]);

  // ---------------------------------------------------------------------------
  // Action Buttons (header)
  // ---------------------------------------------------------------------------

  const getActionButtons = () => {
    const buttons: React.ReactNode[] = [];

    if (effectiveMode === "view") {
      buttons.push(
        <button
          key="edit"
          type="button"
          onClick={() => setEffectiveMode("edit")}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
          title="Edit Address"
        >
          <FaEdit size={14} />
          Edit
        </button>,
      );
    }

    // Delete (view mode with existing record)
    if (effectiveMode === "view" && data?.id) {
      buttons.push(
        <button
          key="delete-address"
          type="button"
          onClick={handleDeleteAddress}
          className="p-2 text-rose-600 hover:bg-rose-50 dark:hover:bg-slate-700 rounded-lg transition-colors"
          title="Delete address"
        >
          <FaTrash size={14} />
        </button>,
      );
    }

    // Close button (when inline)
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

    return buttons;
  };

  // ---------------------------------------------------------------------------
  // Derived display values
  // ---------------------------------------------------------------------------

  const displayName = data
    ? data.name || data.address1 || data.full || `Address #${data.id}`
    : "New Address";

  return (
    <div className="h-full flex flex-col bg-white dark:bg-slate-900">
      {/* ─── HEADER ─── */}
      <div className="shrink-0 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 truncate">
              <DevBadge label="Address" className="mr-2" />
              {displayName}
              {activeAddressId && (
                <span className="ml-2 text-sm font-normal text-slate-500 dark:text-slate-400">
                  #{activeAddressId}
                </span>
              )}
            </h2>
            <div className="flex items-center gap-3 mt-1">
              {data?.address_type && (
                <span className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300">
                  {data.address_type}
                </span>
              )}
              {data?.city && (
                <span className="text-sm text-slate-500 dark:text-slate-400">
                  {data.city}
                  {data.state && `, ${data.state}`}
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
        <div className="sticky top-0 z-20 px-4 py-3 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm border-b border-slate-200 dark:border-slate-700">
          <TransactionToolbar
            transactionType="order"
            transactionId={data?.id}
            isDirty={isDirty}
            isSaving={isSubmitting}
            isEditing
            onSave={() => handleSubmit(onSubmit)()}
            onSaveAndClose={async () => {
              await handleSubmit(async (fd) => {
                await onSubmit(fd);
                handleCancel();
              })();
            }}
            onCancel={handleCancel}
            canClone={false}
            canTransfer={false}
            canDelete={false}
            showTaskButton={false}
          />
        </div>
      )}

      {/* ─── BASIC INFORMATION (PERSISTENT) ─── */}
      <div className="shrink-0 px-4 py-3 border-b border-slate-200 dark:border-slate-700">
        {effectiveMode === "view" && data ? (
          /* ── Read-only view ── */
          <>
            <ScalarCard
              title="Address Info"
              icon={<FaMapMarkerAlt size={14} />}
              fields={[
                { label: "address1", value: data.address1 },
                { label: "address2", value: data.address2 },
                { label: "address_type", value: data.address_type },
                { label: "city", value: data.city },
                { label: "state", value: data.state },
                { label: "zip", value: data.zip },
                { label: "country", value: data.country },
                { label: "full", value: data.full },
                { label: "instructions", value: data.instructions },
              ]}
              columns={columnCount as 1 | 2 | 3}
            />
            <ScalarCard
              title="Geo"
              icon={<FaMapMarkerAlt size={14} />}
              fields={[
                { label: "latitude", value: data.latitude },
                { label: "longitude", value: data.longitude },
              ]}
              columns={2}
              defaultExpanded={false}
            />
            <BaseModelCards data={data as Record<string, unknown>} />
          </>
        ) : (
          /* ── Editable form ── */
          <form id="address-form" onSubmit={handleSubmit(onSubmit)}>
            <div
              className={`grid grid-cols-1 ${
                columnCount === 3 ? "lg:grid-cols-3" : "lg:grid-cols-2"
              } gap-x-6 gap-y-0`}
            >
              <HorizontalField
                label="address1"
                htmlFor="address1"
                error={errors.address1?.message}
              >
                <Input
                  type="text"
                  id="address1"
                  placeholder="Street address"
                  {...register("address1")}
                  error={!!errors.address1?.message}
                />
              </HorizontalField>

              <HorizontalField
                label="address2"
                htmlFor="address2"
                error={errors.address2?.message}
              >
                <Input
                  type="text"
                  id="address2"
                  placeholder="Apt, suite, unit"
                  {...register("address2")}
                  error={!!errors.address2?.message}
                />
              </HorizontalField>

              <HorizontalField
                label="address_type"
                htmlFor="address_type"
                error={errors.address_type?.message}
              >
                <Input
                  type="text"
                  id="address_type"
                  placeholder="Billing, Shipping, etc."
                  {...register("address_type")}
                  error={!!errors.address_type?.message}
                />
              </HorizontalField>

              <HorizontalField
                label="city"
                htmlFor="city"
                error={errors.city?.message}
              >
                <Input
                  type="text"
                  id="city"
                  placeholder="City"
                  {...register("city")}
                  error={!!errors.city?.message}
                />
              </HorizontalField>

              <HorizontalField
                label="state"
                htmlFor="state"
                error={errors.state?.message}
              >
                <Input
                  type="text"
                  id="state"
                  placeholder="State / Province"
                  {...register("state")}
                  error={!!errors.state?.message}
                />
              </HorizontalField>

              <HorizontalField
                label="zip"
                htmlFor="zip"
                error={errors.zip?.message}
              >
                <Input
                  type="text"
                  id="zip"
                  placeholder="ZIP / Postal Code"
                  {...register("zip")}
                  error={!!errors.zip?.message}
                />
              </HorizontalField>

              <HorizontalField
                label="country"
                htmlFor="country"
                error={errors.country?.message}
              >
                <Input
                  type="text"
                  id="country"
                  placeholder="Country"
                  {...register("country")}
                  error={!!errors.country?.message}
                />
              </HorizontalField>

              <HorizontalField
                label="latitude"
                htmlFor="latitude"
                error={errors.latitude?.message}
              >
                <Input
                  type="text"
                  id="latitude"
                  placeholder="e.g. 40.7128"
                  {...register("latitude")}
                  error={!!errors.latitude?.message}
                />
              </HorizontalField>

              <HorizontalField
                label="longitude"
                htmlFor="longitude"
                error={errors.longitude?.message}
              >
                <Input
                  type="text"
                  id="longitude"
                  placeholder="e.g. -74.0060"
                  {...register("longitude")}
                  error={!!errors.longitude?.message}
                />
              </HorizontalField>
            </div>

            {/* Full Address - spans full width */}
            <div className="mt-4">
              <HorizontalField
                label="full"
                htmlFor="full"
                error={errors.full?.message}
              >
                <CustTextArea
                  id="full"
                  placeholder="Complete formatted address"
                  {...register("full")}
                  error={errors.full?.message ? true : false}
                  rows={2}
                />
              </HorizontalField>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default withDevIdentifier(AddressDetail, 'AddressDetail');
