/**
 * DomainDetail.tsx
 *
 * Standard Domain Detail page following the enterprise UI pattern (matches ContactDetail):
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
import { FaEdit, FaGlobe, FaTrash } from "react-icons/fa";

// UI primitives
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import DropDown from "@/components/form/input/DropDown";
import { DevBadge } from "@/components/common/DevBadge";

// Column count
import { useColumnCount } from "@/components/common/DetailTabs";

// Toolbar
import TransactionToolbar from "@/apps/common/components/TransactionToolbar";
import { ScalarCard, BaseModelCards } from "@/apps/common/components/detail";
// API & State
import {
  createDomain,
  updateDomain,
  deleteDomain,
} from "../services/domainApi";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { domainSchema } from "../utils/domainSchema";
import { DomainAddProps } from "../types/domainType";

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

export default function DomainDetail({
  modeProp,
  dataProp,
  hideBreadcrumb: _hideBreadcrumb,
  onSaved,
  inline: _inline = false,
  onCancelInline,
}: DomainAddProps) {
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
  const activeDomainId = data?.id || null;

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
  } = useForm<z.infer<typeof domainSchema>>({
    resolver: zodResolver(domainSchema),
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
  // Column Count
  // ---------------------------------------------------------------------------
  const { columnCount } = useColumnCount("domain", 3);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const onSubmit = async (formData: z.infer<typeof domainSchema>) => {
    try {
      const res =
        effectiveMode === "add"
          ? await createDomain({ ...formData })
          : await updateDomain({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Domain ${
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

  const handleDeleteDomain = useCallback(async () => {
    const domainId = data?.id;
    if (!domainId) return;
    if (!window.confirm(`Delete domain #${domainId}?`)) return;

    try {
      await deleteDomain(domainId);
      dispatch(
        showToast({
          message: `Domain #${domainId} deleted`,
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
          message: `Failed to delete domain: ${err}`,
          type: "error",
        }),
      );
    }
  }, [data?.id, dispatch, onSaved, onCancelInline, navigate]);

  const typeOptions = [
    { value: "website", label: "Website" },
    { value: "linkedin", label: "LinkedIn" },
    { value: "facebook", label: "Facebook" },
    { value: "twitter", label: "Twitter" },
    { value: "github", label: "GitHub" },
    { value: "other", label: "Other" },
  ];

  const handleTypeChange = (value: string) => {
    setValue(
      "type",
      value as
        | "website"
        | "linkedin"
        | "facebook"
        | "twitter"
        | "github"
        | "other",
    );
  };

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
          title="Edit Domain"
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
          key="delete-domain"
          type="button"
          onClick={handleDeleteDomain}
          className="p-2 text-rose-600 hover:bg-rose-50 dark:hover:bg-slate-700 rounded-lg transition-colors"
          title="Delete domain"
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
    ? data.path || data.name || `Domain #${data.id}`
    : "New Domain";

  const domainType = watch("type") || data?.type;

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
              <DevBadge label="Domain" className="mr-2" />
              {displayName}
              {activeDomainId && (
                <span className="ml-2 text-sm font-normal text-slate-500 dark:text-slate-400">
                  #{activeDomainId}
                </span>
              )}
            </h2>
            <div className="flex items-center gap-3 mt-1">
              {domainType && (
                <span className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300 capitalize">
                  {domainType}
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
            onSaveAndClose={handleSubmit(async (fd) => {
              await onSubmit(fd);
              handleCancel();
            })}
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
              title="Domain Info"
              icon={<FaGlobe size={14} />}
              fields={[
                { label: "path", value: data.path, highlight: true },
                { label: "type", value: data.type },
                { label: "status", value: data.status },
                { label: "comment", value: data.comment },
                { label: "security_level", value: data.security_level },
                { label: "sequence", value: data.sequence },
                { label: "count_accessed", value: data.count_accessed },
              ]}
              columns={columnCount as 1 | 2 | 3}
            />
            <BaseModelCards data={data as Record<string, unknown>} />
          </>
        ) : (
          /* ── Editable form ── */
          <form id="domain-form" onSubmit={handleSubmit(onSubmit)}>
            <div
              className={`grid grid-cols-1 ${
                columnCount === 3 ? "lg:grid-cols-3" : "lg:grid-cols-2"
              } gap-x-6 gap-y-0`}
            >
              <HorizontalField
                label="path"
                htmlFor="path"
                required
                error={errors.path?.message}
              >
                <Input
                  type="text"
                  id="path"
                  placeholder="https://example.com"
                  {...register("path")}
                  error={!!errors.path?.message}
                />
              </HorizontalField>

              <HorizontalField
                label="type"
                htmlFor="type"
                error={errors.type?.message}
              >
                <DropDown
                  id="type"
                  options={typeOptions}
                  placeholder="Select Type"
                  value={watch("type")}
                  onChange={handleTypeChange}
                  className="dark:bg-dark-900"
                />
              </HorizontalField>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
