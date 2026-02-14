import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { Globe, Link, Hash } from "lucide-react";

import ComponentCard from "../../../../../components/common/ComponentCard";
import HorizontalField from "../../../../../components/form/HorizontalField";
import { useColumnCount, ColumnSelector, getGridClassName } from "../../../../../components/form/useColumnCount";
import { Input, DropDown } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";
import { DetailTabs, useDetailTabs } from "../../../../../components/common/DetailTabs";
import ContactLinksPanel from "../../../../transactions/components/ContactPanel";
import CommentsPanel from "../../../../common/components/panels/CommentsPanel";
import ActionsPanel from "../../../../common/components/panels/ActionsPanel";
import DocumentsPanel from "../../../../common/components/panels/DocumentsPanel";
import { createDomain, updateDomain } from "../services/domainApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { domainSchema } from "../utils/domainSchema";
import { DomainAddProps } from "../types/domainType";

const STORAGE_KEY = "domainDetail_columnCount";

export default function DomainDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: DomainAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<z.infer<typeof domainSchema>>({
    resolver: zodResolver(domainSchema),
  });

  const location = useLocation();
  const navigate = useNavigate();
  const routeState = (location.state as any) || {};
  const [isSaving, setIsSaving] = useState(false);
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  const data = dataProp || routeState.data || null;

  // Tab state - default to contacts since overview is persistent
  const { activeTab, setActiveTab } = useDetailTabs("domain", "contacts");
  
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

  const onSubmit = async (formData: z.infer<typeof domainSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createDomain({ ...formData })
          : await updateDomain({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Domain ${
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
        | "other"
    );
  };

  // Render tab content
  const renderTabContent = () => {
    switch (activeTab) {
      case "contacts":
        return (
          <ContactLinksPanel
            entityType="domain"
            entityId={data?.id}
            data={data?.refs?.links?.contact}
            isEditing={currentMode === "edit"}
          />
        );

      case "comments":
        return (
          <CommentsPanel
            entityType="domain"
            entityId={data?.id}
            comments={data?.comments}
            isEditing={currentMode === "edit"}
            currentUser="Current User"
          />
        );

      case "actions":
        return (
          <ActionsPanel
            entityType="domain"
            entityId={data?.id}
            data={data?.actions?.items}
            isEditing={currentMode === "edit"}
          />
        );

      case "documents":
        return (
          <DocumentsPanel
            parent_model="domain"
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
              ? "Edit Domain"
              : currentMode === "view"
              ? "View Domain"
              : "Domain Detail"
          }
        />
      )}

      {/* Header */}
      <SimpleDetailHeader
        entityName="Domain"
        recordId={data?.id}
        recordName={data?.path || data?.name}
        mode={currentMode}
        backUrl="/communications/domains"
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
                ? "Edit Domain"
                : currentMode === "view"
                ? "View Domain"
                : "Add New Domain"}
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
            <HorizontalField label="Path / URL" htmlFor="path" error={errors.path?.message} icon={<Link size={14} />}>
              <Input
                type="text"
                id="path"
                placeholder="https://example.com"
                {...register("path")}
                error={errors.path?.message ? true : false}
                hint={errors.path?.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Type" htmlFor="type" error={errors.type?.message} icon={<Hash size={14} />}>
              <DropDown
                id="type"
                options={typeOptions}
                placeholder="Select Type"
                value={watch("type")}
                onChange={handleTypeChange}
                className="dark:bg-dark-900"
                disabled={currentMode === "view"}
              />
            </HorizontalField>
          </div>
        </form>
      </ComponentCard>

      {/* Tab Navigation (below persistent overview) */}
      <DetailTabs
        entityType="domain"
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
