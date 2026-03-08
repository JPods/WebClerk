/**
 * PhoneDetail.tsx
 *
 * Standard Phone Detail page following the enterprise UI pattern (matches ContactDetail):
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
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { FaEdit, FaPhone, FaTrash } from "react-icons/fa";

// UI primitives
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import Checkbox from "@/components/form/input/Checkbox";
import { DevBadge } from "@/components/common/DevBadge";

// Column count
import { useColumnCount } from "@/components/common/DetailTabs";

// Toolbar
import TransactionToolbar from "@/apps/common/components/TransactionToolbar";
import { ScalarCard, BaseModelCards } from "@/apps/common/components/detail";
// API & State
import { createPhone, updatePhone, deletePhone } from "../services/phoneApi";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { phoneSchema } from "../utils/phoneSchema";
import { PhoneAddProps } from "../types/phoneType";
import { withDevIdentifier } from "@/components/common/DevIdentifier";

/**
 * Format phone number as (123) 456-7890
 * Strips non-digits, then formats with parentheses
 */
const formatPhoneNumber = (value: string): string => {
  const digits = value.replace(/\D/g, "").slice(0, 10);
  if (digits.length === 0) return "";
  if (digits.length <= 3) return `(${digits}`;
  if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
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
// InfoRow — read-only horizontal label/value pair
// ---------------------------------------------------------------------------

const InfoRow: React.FC<{ label: string; value: React.ReactNode }> = ({
  label,
  value,
}) => (
  <div className="flex items-center gap-2">
    <dt className="w-32 shrink-0 text-right text-sm text-slate-500 dark:text-slate-400">
      {label}
    </dt>
    <dd className="font-medium text-sm text-slate-900 dark:text-slate-100">
      {value || "—"}
    </dd>
  </div>
);

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

function PhoneDetail({
  modeProp,
  dataProp,
  hideBreadcrumb: _hideBreadcrumb,
  onSaved,
  inline: _inline = false,
  onCancelInline,
}: PhoneAddProps) {
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
  const activePhoneId = data?.id || null;

  // ---------------------------------------------------------------------------
  // Form
  // ---------------------------------------------------------------------------

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors, isDirty, isSubmitting },
    reset,
    watch,
    control,
  } = useForm<z.infer<typeof phoneSchema>>({
    resolver: zodResolver(phoneSchema),
    defaultValues: { opt_out: false },
  });

  // Strongly type handleSubmit to use the correct form data type
  const typedHandleSubmit = handleSubmit as unknown as (
    onValid: (data: z.infer<typeof phoneSchema>) => void | Promise<void>,
  ) => (e?: React.BaseSyntheticEvent) => Promise<void>;

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
  // Column Count
  // ---------------------------------------------------------------------------
  const { columnCount } = useColumnCount("phone", 3);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const onSubmit = async (formData: z.infer<typeof phoneSchema>) => {
    try {
      const res =
        effectiveMode === "add"
          ? await createPhone(formData)
          : await updatePhone({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Phone ${
              effectiveMode === "add" ? "created" : "updated"
            } successfully`,
            type: "success",
          }),
        );
        // NOTE: onSaved() is intentionally NOT called here.
        // It should only be invoked by "Save & Close" flow via TransactionToolbar.
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

  const handleDeletePhone = useCallback(async () => {
    const phoneId = data?.id;
    if (!phoneId) return;
    if (!window.confirm(`Delete phone #${phoneId}?`)) return;

    try {
      await deletePhone(phoneId);
      dispatch(
        showToast({
          message: `Phone #${phoneId} deleted`,
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
          message: `Failed to delete phone: ${err}`,
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
          title="Edit Phone"
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
          key="delete-phone"
          type="button"
          onClick={handleDeletePhone}
          className="p-2 text-rose-600 hover:bg-rose-50 dark:hover:bg-slate-700 rounded-lg transition-colors"
          title="Delete phone"
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
    ? data.number || data.name || `Phone #${data.id}`
    : "New Phone";

  const optOut = watch("opt_out") ?? data?.opt_out;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="h-full flex flex-col bg-white dark:bg-slate-900">
      {/* ─── HEADER ─── */}
      <div className="shrink-0 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 truncate">
              <DevBadge label="Phone" variant="teal" className="mr-2" />
              {displayName}
              {activePhoneId && (
                <span className="ml-2 text-sm font-normal text-slate-500 dark:text-slate-400">
                  #{activePhoneId}
                </span>
              )}
            </h2>
            <div className="flex items-center gap-3 mt-1">
              {optOut && (
                <span className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300">
                  Opted Out
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
            onSave={handleSubmit(onSubmit)}
            onSaved={onSaved}
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
              title="Phone Info"
              icon={<FaPhone size={14} />}
              fields={[
                { label: "number", value: data.number, highlight: true },
                { label: "country_code", value: data.country_code },
                { label: "format", value: data.format },
                { label: "name", value: data.name },
                { label: "attention", value: data.attention },
                { label: "opt_out", value: data.opt_out },
              ]}
              columns={columnCount as 1 | 2 | 3}
            />
            <BaseModelCards data={data as Record<string, unknown>} />
          </>
        ) : (
          /* ── Editable form ── */
          <form id="phone-form" onSubmit={typedHandleSubmit(onSubmit)}>
            <div
              className={`grid grid-cols-1 ${
                columnCount === 3 ? "lg:grid-cols-3" : "lg:grid-cols-2"
              } gap-x-6 gap-y-0`}
            >
              <HorizontalField
                label="number"
                htmlFor="number"
                required
                error={errors.number?.message}
              >
                <Controller
                  name="number"
                  control={control}
                  render={({ field }) => (
                    <Input
                      type="tel"
                      id="number"
                      placeholder="(123) 456-7890"
                      value={field.value ?? ""}
                      onChange={(e) =>
                        field.onChange(formatPhoneNumber(e.target.value))
                      }
                      error={!!errors.number?.message}
                    />
                  )}
                />
              </HorizontalField>

              <HorizontalField
                label="country_code"
                htmlFor="country_code"
                error={errors.country_code?.message}
              >
                <Input
                  type="text"
                  id="country_code"
                  placeholder="+1"
                  {...register("country_code")}
                  error={!!errors.country_code?.message}
                />
              </HorizontalField>

              <HorizontalField
                label="format"
                htmlFor="format"
                error={errors.format?.message}
              >
                <Input
                  type="text"
                  id="format"
                  placeholder="(###) ###-####"
                  value={"(###) ###-####"}
                  {...register("format")}
                  error={!!errors.format?.message}
                />
              </HorizontalField>

              <HorizontalField
                label="name"
                htmlFor="name"
                error={errors.name?.message}
              >
                <Input
                  type="text"
                  id="name"
                  placeholder="Phone Label (e.g., Main Office)"
                  {...register("name")}
                  error={!!errors.name?.message}
                />
              </HorizontalField>

              <HorizontalField
                label="attention"
                htmlFor="attention"
                error={errors.attention?.message}
              >
                <Input
                  type="text"
                  id="attention"
                  placeholder="Attention"
                  {...register("attention")}
                  error={!!errors.attention?.message}
                />
              </HorizontalField>

              <HorizontalField label="opt_out" htmlFor="opt_out">
                <Controller
                  name="opt_out"
                  control={control}
                  render={({ field }) => (
                    <Checkbox
                      id="opt_out"
                      checked={field.value ?? false}
                      onChange={field.onChange}
                      label=""
                    />
                  )}
                />
              </HorizontalField>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default withDevIdentifier(PhoneDetail, "PhoneDetail");
