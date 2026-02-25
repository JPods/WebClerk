/**
 * EmailDetail.tsx
 *
 * Standard Email Detail page following the enterprise UI pattern (matches ContactDetail):
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
import { useForm, Controller } from "react-hook-form";
import { FaEdit, FaEnvelope } from "react-icons/fa";

// UI primitives
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import DropDown from "@/components/form/input/DropDown";
import { DevBadge } from '@/components/common/DevBadge';
import Checkbox from "@/components/form/input/Checkbox";

// Column count
import {
  DetailTabs,
  useDetailTabs,
  useColumnCount,
} from "@/components/common/DetailTabs";

// Toolbar
import TransactionToolbar from "@/apps/common/components/TransactionToolbar";
// Panel Components
//import ContactLinksPanel from "@/apps/transactions/components/ContactPanel";
import CommentsPanel from "@/apps/common/components/panels/CommentsPanel";
import ActionsPanel from "@/apps/common/components/panels/ActionsPanel";
import DocumentsPanel from "@/apps/common/components/panels/DocumentsPanel";
import { ScalarCard, BaseModelCards } from "@/apps/common/components/detail";
// API & State
import { createEmail, updateEmail } from "../services/emailApi";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { emailSchema } from "../utils/emailSchema";
import { EmailAddProps } from "../types/emailType";
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

export default function EmailDetail({
  modeProp,
  dataProp,
  hideBreadcrumb: _hideBreadcrumb,
  onSaved,
  inline: _inline = false,
  onCancelInline,
}: EmailAddProps) {
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
  const activeEmailId = data?.id || null;

  // ---------------------------------------------------------------------------
  // Form
  // ---------------------------------------------------------------------------

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors, isDirty, isSubmitting },
    reset,
    control,
    watch,
  } = useForm<z.infer<typeof emailSchema>>({
    resolver: zodResolver(emailSchema),
    defaultValues: {
      email: "",
      name: "",
      is_primary: false,
      is_verified: false,
      attention: "",
      opt_out: undefined,
    },
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

  const { activeTab, setActiveTab } = useDetailTabs("email", "comments");

  // ---------------------------------------------------------------------------
  // Column Count
  // ---------------------------------------------------------------------------

  const { columnCount, setColumnCount } = useColumnCount("email", 3);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const onSubmit = async (formData: z.infer<typeof emailSchema>) => {
    try {
      const res =
        effectiveMode === "add"
          ? await createEmail({ ...formData, id: "" })
          : await updateEmail({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Email ${
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

  const statusOptions = [
    { value: "active", label: "Active" },
    { value: "opted_out", label: "Opted Out" },
    { value: "bounced", label: "Bounced" },
    { value: "invalid", label: "Invalid" },
    { value: "spam_complaint", label: "Spam Complaint" },
  ];

  const handleStatusChange = (value: string) => {
    setValue(
      "opt_out",
      value as
        | "bounced"
        | "opted_out"
        | "invalid"
        | "spam_complaint"
        | undefined,
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
          title="Edit Email"
        >
          <FaEdit size={14} />
          Edit
        </button>,
      );
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
    }

    return buttons;
  };

  // ---------------------------------------------------------------------------
  // Derived display values
  // ---------------------------------------------------------------------------

  const displayName = data
    ? data.email || data.name || `Email #${data.id}`
    : "New Email";

  const statusLabel = watch("opt_out") || "active";

  // ---------------------------------------------------------------------------
  // Render Tab Content
  // ---------------------------------------------------------------------------

  const renderTabContent = () => {
    switch (activeTab) {
      case "comments":
        return (
          <CommentsPanel
            entityType="email"
            entityId={data?.id}
            comments={data?.comments}
            isEditing={isEditing}
            currentUser="Current User"
          />
        );

      case "actions":
        return (
          <ActionsPanel
            entityType="email"
            entityId={data?.id}
            data={data?.actions?.items}
            isEditing={isEditing}
          />
        );

      case "documents":
        return (
          <DocumentsPanel
            parent_model="email"
            parentId={data?.id}
            data={data?.refs?.links?.document}
            isEditing={isEditing}
          />
        );

      case "raw":
        return (
          <pre className="text-xs font-mono bg-slate-100 dark:bg-slate-800 p-4 rounded overflow-auto">
            {JSON.stringify(data, null, 2)}
          </pre>
        );

      default:
        return null;
    }
  };

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
              <DevBadge label="Email" className="mr-2" />
              {displayName}
              {activeEmailId && (
                <span className="ml-2 text-sm font-normal text-slate-500 dark:text-slate-400">
                  #{activeEmailId}
                </span>
              )}
            </h2>
            <div className="flex items-center gap-3 mt-1">
              <span
                className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${
                  statusLabel === "active"
                    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400"
                    : "bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400"
                }`}
              >
                {statusLabel === "active"
                  ? "Active"
                  : statusLabel.replace("_", " ")}
              </span>
              {data?.is_primary && (
                <span className="text-sm text-slate-500 dark:text-slate-400">
                  Primary
                </span>
              )}
              {data?.is_verified && (
                <span className="text-sm text-emerald-600 dark:text-emerald-400">
                  Verified
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
              title="Email Info"
              icon={<FaEnvelope size={14} />}
              fields={[
                { label: "email", value: data.email, highlight: true },
                { label: "name", value: data.name },
                { label: "attention", value: data.attention },
                { label: "opt_out", value: data.opt_out },
                { label: "is_primary", value: data.is_primary },
                { label: "is_verified", value: data.is_verified },
                { label: "status_display", value: data.status_display },
              ]}
              columns={columnCount as 1 | 2 | 3}
            />
            <BaseModelCards data={data as Record<string, unknown>} />
          </>
        ) : (
          /* ── Editable form ── */
          <form id="email-form" onSubmit={handleSubmit(onSubmit)}>
            <div
              className={`grid grid-cols-1 ${
                columnCount === 3 ? "lg:grid-cols-3" : "lg:grid-cols-2"
              } gap-x-6 gap-y-0`}
            >
              <HorizontalField
                label="email"
                htmlFor="email"
                required
                error={errors.email?.message}
              >
                <Input
                  type="email"
                  id="email"
                  placeholder="user@example.com"
                  {...register("email")}
                  error={!!errors.email?.message}
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
                  placeholder="Display Name"
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

              <HorizontalField label="status" htmlFor="opt_out">
                <DropDown
                  id="opt_out"
                  options={statusOptions}
                  placeholder="Select Status"
                  value={watch("opt_out")}
                  onChange={handleStatusChange}
                  className="dark:bg-dark-900"
                />
              </HorizontalField>

              <HorizontalField label="is_primary" htmlFor="is_primary">
                <Controller
                  name="is_primary"
                  control={control}
                  render={({ field }) => (
                    <Checkbox
                      id="is_primary"
                      checked={field.value ?? false}
                      onChange={field.onChange}
                      label=""
                    />
                  )}
                />
              </HorizontalField>

              <HorizontalField label="is_verified" htmlFor="is_verified">
                <Controller
                  name="is_verified"
                  control={control}
                  render={({ field }) => (
                    <Checkbox
                      id="is_verified"
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
      {/* <ColumnSelector value={columnCount} onChange={setColumnCount} /> */}
      {/* ─── TAB NAVIGATION ─── */}
      {activeEmailId && data?.id && (
        <>
          <DetailTabs
            entityType="email"
            activeTab={activeTab}
            onTabChange={setActiveTab}
            standardTabs={["comments", "actions", "documents", "raw"]}
            showColumnSelector
            columnCount={columnCount}
            onColumnCountChange={setColumnCount}
          />

          {/* ─── TAB CONTENT (scrollable) ─── */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-4">{renderTabContent()}</div>
          </div>
        </>
      )}
    </div>
  );
}
