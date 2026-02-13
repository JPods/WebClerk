import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useForm, Controller } from "react-hook-form";
import { Mail, Type, User, BellOff, Star, CheckCircle } from "lucide-react";

import ComponentCard from "../../../../../components/common/ComponentCard";
import HorizontalField from "../../../../../components/form/HorizontalField";
import { useColumnCount, ColumnSelector, getGridClassName } from "../../../../../components/form/useColumnCount";
import { Input, DropDown } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";
import { DetailTabs, useDetailTabs } from "../../../../../components/common/DetailTabs";
import ContactLinksPanel from "../../../../common/components/panels/ContactPanel";
import CommentsPanel from "../../../../common/components/panels/CommentsPanel";
import ActionsPanel from "../../../../common/components/panels/ActionsPanel";
import DocumentsPanel from "../../../../common/components/panels/DocumentsPanel";
import { createEmail, updateEmail } from "../services/emailApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { emailSchema } from "../utils/emailSchema";
import { EmailAddProps } from "../types/emailType";
import Checkbox from "../../../../../components/form/input/Checkbox";

const STORAGE_KEY = "emailDetail_columnCount";

export default function EmailDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: EmailAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
    control,
    watch,
  } = useForm<z.infer<typeof emailSchema>>({
    resolver: zodResolver(emailSchema),
    defaultValues: { is_primary: false, is_verified: false },
  });

  const location = useLocation();
  const navigate = useNavigate();
  const routeState = (location.state as any) || {};
  const [isSaving, setIsSaving] = useState(false);
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  const data = dataProp || routeState.data || null;

  // Tab state - default to contacts since overview is persistent
  const { activeTab, setActiveTab } = useDetailTabs("email", "contacts");
  
  // Column count for responsive layout
  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  useEffect(() => {
    if (currentMode === "add") {
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
  }, [data, reset, setValue, currentMode]);

  const onSubmit = async (formData: z.infer<typeof emailSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createEmail({ ...formData, id: "" })
          : await updateEmail({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Email ${
              currentMode === "add" ? "created" : "updated"
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
    } finally {
      setIsSaving(false);
    }
  };

  const handleEdit = () => {
    setCurrentMode("edit");
  };

  const handleCancel = () => {
    if (inline && onCancelInline) {
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
      setCurrentMode("view");
    }
  };

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
        | undefined
    );
  };

  // Render tab content
  const renderTabContent = () => {
    switch (activeTab) {
      case "contacts":
        return (
          <ContactLinksPanel
            entityType="email"
            entityId={data?.id}
            data={data?.refs?.links?.contact}
            isEditing={currentMode === "edit"}
          />
        );

      case "comments":
        return (
          <CommentsPanel
            entityType="email"
            entityId={data?.id}
            comments={data?.comments}
            isEditing={currentMode === "edit"}
            currentUser="Current User"
          />
        );

      case "actions":
        return (
          <ActionsPanel
            entityType="email"
            entityId={data?.id}
            data={data?.actions?.items}
            isEditing={currentMode === "edit"}
          />
        );

      case "documents":
        return (
          <DocumentsPanel
            parentType="email"
            parentId={data?.id}
            data={data?.refs?.links?.document}
            isEditing={currentMode === "edit"}
          />
        );

      case "history":
        return (
          <div className="text-slate-500 dark:text-slate-400 py-8 text-center">
            <p>History log will appear here</p>
          </div>
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

  return (
    <>
      {/* Breadcrumb */}
      {!hideBreadcrumb && (
        <PageBreadcrumb
          pageTitle={
            currentMode === "edit"
              ? "Edit Email"
              : currentMode === "view"
              ? "View Email"
              : "Email Detail"
          }
        />
      )}

      {/* Header */}
      <SimpleDetailHeader
        entityName="Email"
        recordId={data?.id}
        recordName={data?.email || data?.name}
        mode={currentMode}
        backUrl="/communications/emails"
      />

      {/* Toolbar */}
      <SimpleDetailToolbar
        mode={currentMode}
        isSaving={isSaving}
        onSave={handleSubmit(onSubmit)}
        onCancel={handleCancel}
        onEdit={handleEdit}
      />

      {/* Persistent Overview Form */}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {currentMode === "edit"
                ? "Edit Email"
                : currentMode === "view"
                ? "View Email"
                : "Add New Email"}
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
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="flex justify-end mb-4">
            <ColumnSelector value={columnCount} onChange={setColumnCount} />
          </div>
          <div className={getGridClassName(columnCount)}>
            <HorizontalField label="Email" htmlFor="email" error={errors.email?.message} icon={<Mail size={14} />}>
              <Input
                type="email"
                id="email"
                placeholder="user@example.com"
                {...register("email")}
                error={errors.email?.message ? true : false}
                hint={errors.email?.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Name" htmlFor="name" error={errors.name?.message} icon={<Type size={14} />}>
              <Input
                type="text"
                id="name"
                placeholder="Display Name"
                {...register("name")}
                error={errors.name?.message ? true : false}
                hint={errors.name?.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Attention" htmlFor="attention" error={errors.attention?.message} icon={<User size={14} />}>
              <Input
                type="text"
                id="attention"
                placeholder="Attention"
                {...register("attention")}
                error={errors.attention?.message ? true : false}
                hint={errors.attention?.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Status" htmlFor="opt_out" icon={<BellOff size={14} />}>
              <DropDown
                id="opt_out"
                options={statusOptions}
                placeholder="Select Status"
                value={watch("opt_out")}
                onChange={handleStatusChange}
                className="dark:bg-dark-900"
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Primary" htmlFor="is_primary" icon={<Star size={14} />}>
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
            <HorizontalField label="Verified" htmlFor="is_verified" icon={<CheckCircle size={14} />}>
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
      </ComponentCard>

      {/* Tab Navigation (below persistent overview) */}
      <DetailTabs
        entityType="email"
        activeTab={activeTab}
        onTabChange={setActiveTab}
        standardTabs={["contacts", "comments", "actions", "documents", "history", "raw"]}
      />

      {/* Tab Content */}
      <ComponentCard>
        {renderTabContent()}
      </ComponentCard>
    </>
  );
}
