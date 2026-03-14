/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Package, Tag, AlignLeft, Database } from "lucide-react";

import ComponentCard from "../../../../../components/common/ComponentCard";
import HorizontalField from "../../../../../components/form/HorizontalField";
import { useColumnCount, ColumnSelector, getGridClassName } from "../../../../../components/form/useColumnCount";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";
import { createBundle, updateBundle } from "../services/bundleApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { bundleSchema } from "../utils/bundleSchema";
import { BundleAddProps } from "../types/bundleType";
import { ScalarCard, JsonCard, BaseModelCards } from "@/apps/common/components/detail";

// Tab navigation
import { DetailTabs, useDetailTabs } from "@/components/common/DetailTabs";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

const STORAGE_KEY = "bundleDetail_columnCount";

function BundleDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: BundleAddProps) {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof bundleSchema>>({
    resolver: zodResolver(bundleSchema),
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const data = dataProp || routeState.data || null;
  const [isSaving, setIsSaving] = useState(false);
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);

  // Full record data for panels
  const [recordData, setRecordData] = useState<any>(data || {});

  // Tab navigation
  const { activeTab, setActiveTab } = useDetailTabs("bundle_detail", "actions", [
    "actions", "comments", "documents", "raw",
  ]);

  useEffect(() => {
    if (currentMode === "add") {
      reset();
      setRecordData({});
    } else if (data) {
      const formKeys = Object.keys(bundleSchema.shape) as (keyof z.infer<typeof bundleSchema>)[];
      formKeys.forEach((key) => {
        if (data[key] !== undefined) {
          setValue(key, data[key]);
        }
      });
      setRecordData(data);
    } else {
      reset({});
      setRecordData({});
    }
  }, [data, reset, setValue, currentMode]);

  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  const onSubmit = async (formData: z.infer<typeof bundleSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createBundle(formData)
          : await updateBundle({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Bundle ${
              currentMode === "add" ? "created" : "updated"
            } successfully`,
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        }
        if (currentMode === "add") {
          navigate(-1);
        } else {
          setCurrentMode("view");
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

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            currentMode === "edit"
              ? "Edit Bundle"
              : currentMode === "view"
              ? "View Bundle"
              : "Bundle Detail"
          }
        />
      )}

      {!inline && (
        <SimpleDetailHeader
          entityName="Bundle"
          recordId={data?.id}
          recordName={data?.name}
          mode={currentMode}
          backUrl="/sync/bundles"
        />
      )}

      {!inline && (
        <SimpleDetailToolbar
          mode={currentMode}
          isSaving={isSaving}
          onSave={handleSubmit(onSubmit)}
          onCancel={handleCancel}
          onEdit={handleEdit}
        />
      )}

      {currentMode === "view" && data && (
        <div className="space-y-4 py-2">
          <ScalarCard
            title="Bundle Details"
            fields={[
              { label: "connection_id", value: data.connection_id ?? data.connection },
              { label: "direction", value: data.direction },
              { label: "status", value: data.status },
              { label: "alert", value: data.alert },
              { label: "duration", value: data.duration },
              { label: "size", value: data.size },
            ]}
            columns={3}
          />
          <JsonCard title="Config" fieldName="config" data={data.config as Record<string, unknown>} columns={2} />
          <JsonCard title="Response" fieldName="response" data={data.response as Record<string, unknown>} columns={2} />
          <JsonCard title="Payload" fieldName="payload" data={data.payload as Record<string, unknown>} columns={2} />
          <JsonCard title="Maps" fieldName="maps" data={data.maps as Record<string, unknown>} columns={2} />
          <JsonCard title="Encryption" fieldName="encryption" data={data.encryption as Record<string, unknown>} columns={2} />
          <JsonCard title="Rules" fieldName="rules" data={data.rules as Record<string, unknown>} columns={2} />
          <JsonCard title="Conflicts" fieldName="conflicts" data={data.conflicts as Record<string, unknown>} columns={2} />
          <BaseModelCards data={data} />
        </div>
      )}

      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {currentMode === "edit"
                ? "Edit Bundle"
                : currentMode === "view"
                ? "View Bundle"
                : "Add New Bundle"}
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
            <HorizontalField label="Name" htmlFor="name" error={errors.name?.message} icon={Package}>
              <Input
                type="text"
                id="name"
                placeholder="Bundle Name"
                {...register("name")}
                error={!!errors.name}
                hint={errors.name && errors.name.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Version" htmlFor="version" error={errors.version?.message} icon={Tag}>
              <Input
                type="text"
                id="version"
                placeholder="Version"
                {...register("version")}
                error={!!errors.version}
                hint={errors.version && errors.version.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Description" htmlFor="description" error={errors.description?.message} icon={AlignLeft}>
              <Input
                type="text"
                id="description"
                placeholder="Description"
                {...register("description")}
                error={!!errors.description}
                hint={errors.description && errors.description.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Data" htmlFor="data" error={errors.data?.message} icon={Database}>
              <Input
                type="text"
                id="data"
                placeholder="Data"
                {...register("data")}
                error={!!errors.data}
                hint={errors.data && errors.data.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
          </div>
          {currentMode !== "view" && inline && (
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4 flex items-center gap-2">
              <button
                type="submit"
                className="flex items-center px-4 py-2 text-white bg-brand-500 rounded-md hover:bg-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
              >
                {currentMode === "edit" ? "Update" : "Submit"}
              </button>
              {inline && onCancelInline && (
                <button
                  type="button"
                  onClick={onCancelInline}
                  className="flex items-center px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
                >
                  Cancel
                </button>
              )}
            </div>
          )}
        </form>
      </ComponentCard>

      {/* Tab Navigation */}
      {recordData?.id && (
        <>
          <DetailTabs
            entityType="bundle_detail"
            activeTab={activeTab}
            onTabChange={setActiveTab}
            standardTabs={["actions", "comments", "documents", "raw"]}
            badges={{
              comments: recordData?.comments?.length,
              documents: recordData?.refs?.links?.document?.length,
            }}
            panelEntityType="bundle"
            entityId={recordData.id}
            recordData={recordData}
            isEditing={currentMode !== "view"}
            onRecordChange={setRecordData}
          />
        </>
      )}
    </>
  );
}

export default withDevIdentifier(BundleDetail, 'BundleDetail');
