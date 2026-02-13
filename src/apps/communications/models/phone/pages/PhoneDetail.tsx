import { useEffect, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Phone, Globe, Hash, Type, User, BellOff } from "lucide-react";

import ComponentCard from "../../../../../components/common/ComponentCard";
import HorizontalField from "../../../../../components/form/HorizontalField";
import { useColumnCount, ColumnSelector, getGridClassName } from "../../../../../components/form/useColumnCount";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";
import { DetailTabs, useDetailTabs } from "../../../../../components/common/DetailTabs";
import ContactLinksPanel from "../../../../common/components/panels/ContactPanel";
import CommentsPanel from "../../../../common/components/panels/CommentsPanel";
import ActionsPanel from "../../../../common/components/panels/ActionsPanel";
import DocumentsPanel from "../../../../common/components/panels/DocumentsPanel";
import { createPhone, updatePhone } from "../services/phoneApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { phoneSchema } from "../utils/phoneSchema";
import { PhoneAddProps } from "../types/phoneType";
import Checkbox from "../../../../../components/form/input/Checkbox";

const STORAGE_KEY = "phoneDetail_columnCount";

export default function PhoneDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: PhoneAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
    control,
  } = useForm({
    resolver: zodResolver(phoneSchema),
    defaultValues: { opt_out: false },
  });

  const location = useLocation();
  const navigate = useNavigate();
  const routeState = (location.state as any) || {};
  const [isSaving, setIsSaving] = useState(false);
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  const data = dataProp || routeState.data || null;

  // Tab state - default to contacts since overview is persistent
  const { activeTab, setActiveTab } = useDetailTabs("phone", "contacts");
  
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

  const onSubmit = async (formData: z.infer<typeof phoneSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createPhone(formData)
          : await updatePhone({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Phone ${
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

  // Render tab content
  const renderTabContent = () => {
    switch (activeTab) {
      case "contacts":
        return (
          <ContactLinksPanel
            entityType="phone"
            entityId={data?.id}
            data={data?.refs?.links?.contact}
            isEditing={currentMode === "edit"}
          />
        );

      case "comments":
        return (
          <CommentsPanel
            entityType="phone"
            entityId={data?.id}
            comments={data?.comments}
            isEditing={currentMode === "edit"}
            currentUser="Current User"
          />
        );

      case "actions":
        return (
          <ActionsPanel
            entityType="phone"
            entityId={data?.id}
            data={data?.actions?.items}
            isEditing={currentMode === "edit"}
          />
        );

      case "documents":
        return (
          <DocumentsPanel
            parentType="phone"
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
              ? "Edit Phone"
              : currentMode === "view"
              ? "View Phone"
              : "Phone Detail"
          }
        />
      )}

      {/* Header */}
      <SimpleDetailHeader
        entityName="Phone"
        recordId={data?.id}
        recordName={data?.number || data?.name}
        mode={currentMode}
        backUrl="/communications/phones"
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
                ? "Edit Phone"
                : currentMode === "view"
                ? "View Phone"
                : "Add New Phone"}
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
            <HorizontalField label="Number" htmlFor="number" error={errors.number?.message} icon={<Phone size={14} />}>
              <Input
                type="text"
                id="number"
                placeholder="Phone Number"
                {...register("number")}
                error={errors.number?.message ? true : false}
                hint={errors.number?.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Country" htmlFor="country_code" error={errors.country_code?.message} icon={<Globe size={14} />}>
              <Input
                type="text"
                id="country_code"
                placeholder="+1"
                {...register("country_code")}
                error={errors.country_code?.message ? true : false}
                hint={errors.country_code?.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Format" htmlFor="format" error={errors.format?.message} icon={<Hash size={14} />}>
              <Input
                type="text"
                id="format"
                placeholder="(###) ###-####"
                {...register("format")}
                error={errors.format?.message ? true : false}
                hint={errors.format?.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Name" htmlFor="name" error={errors.name?.message} icon={<Type size={14} />}>
              <Input
                type="text"
                id="name"
                placeholder="Phone Label (e.g., Main Office)"
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
            <HorizontalField label="Opt Out" htmlFor="opt_out" icon={<BellOff size={14} />}>
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
      </ComponentCard>

      {/* Tab Navigation (below persistent overview) */}
      <DetailTabs
        entityType="phone"
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
