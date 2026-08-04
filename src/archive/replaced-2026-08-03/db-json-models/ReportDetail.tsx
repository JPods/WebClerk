/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { FileText, List, AlignLeft, Settings } from "lucide-react";

import ComponentCard from "../../../../../components/common/ComponentCard";
import HorizontalField from "../../../../../components/form/HorizontalField";
import { useColumnCount, ColumnSelector, getGridClassName } from "../../../../../components/form/useColumnCount";
import { Input, DropDown } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createReport, updateReport } from "../services/reportApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";

// Tab navigation
import { DetailTabs, useDetailTabs } from "@/components/common/DetailTabs";

import { useLocation, useNavigate } from "react-router";
import { reportSchema } from "../utils/reportSchema";
import { ReportAddProps } from "../types/reportType";
import Checkbox from "../../../../../components/form/input/Checkbox";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";
import { ScalarCard, BaseModelCards } from "@/apps/common/components/detail";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

const STORAGE_KEY = "reportDetail_columnCount";

function ReportDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ReportAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<z.infer<typeof reportSchema>>({
    resolver: zodResolver(reportSchema),
    defaultValues: { is_active: false },
  });

  const location = useLocation();
  const navigate = useNavigate();
  const routeState = (location.state as any) || {};
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  const [isSaving, setIsSaving] = useState(false);
  const data = dataProp || routeState.data || null;

  // Full record data for panels
  const [recordData, setRecordData] = useState<any>(data || {});

  // Tab navigation
  const { activeTab, setActiveTab } = useDetailTabs("report_detail", "actions", [
    "actions", "comments", "documents", "raw",
  ]);

  useEffect(() => {
    if (initialMode === "add") {
      reset();
      setRecordData({});
    } else if (data) {
      Object.keys(data).forEach((key: any) => {
        if (data[key] !== undefined) {
          setValue(key, data[key]);
        }
      });
      setRecordData(data);
    } else {
      reset({});
      setRecordData({});
    }
  }, [data, reset, setValue, initialMode]);

  const onSubmit = async (formData: z.infer<typeof reportSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createReport(formData)
          : await updateReport({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Report ${
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

  const reportTypes = [
    { value: "sales", label: "Sales Report" },
    { value: "inventory", label: "Inventory Report" },
    { value: "financial", label: "Financial Report" },
    { value: "user", label: "User Report" },
  ];

  const handleTypeChange = (value: string) => {
    setValue("type", value);
  };

  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            currentMode === "edit"
              ? "Edit Report"
              : currentMode === "view"
              ? "View Report"
              : "Report Detail"
          }
        />
      )}

      {!inline && (
        <SimpleDetailHeader
          entityName="Report"
          recordId={data?.id}
          recordName={data?.title}
          mode={currentMode}
          backUrl="/core/reports"
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

      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {currentMode === "edit"
                ? "Edit Report"
                : currentMode === "view"
                ? "View Report"
                : "Add New Report"}
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
            <HorizontalField label="Title" htmlFor="title" error={errors.title?.message} icon={FileText}>
              <Input
                type="text"
                id="title"
                placeholder="Report Title"
                {...register("title")}
                error={errors.title && errors.title.message ? true : false}
                hint={errors.title && errors.title.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Type" htmlFor="type" icon={List}>
              <DropDown
                id="type"
                options={reportTypes}
                placeholder="Select Report Type"
                value={watch("type")}
                onChange={handleTypeChange}
                className="dark:bg-dark-900"
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Description" htmlFor="description" error={errors.description?.message} icon={AlignLeft}>
              <Input
                type="text"
                id="description"
                placeholder="Report Description"
                {...register("description")}
                error={
                  errors.description && errors.description.message ? true : false
                }
                hint={errors.description && errors.description.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Parameters" htmlFor="parameters" error={errors.parameters?.message} icon={Settings}>
              <Input
                type="text"
                id="parameters"
                placeholder="Report Parameters"
                {...register("parameters")}
                error={
                  errors.parameters && errors.parameters.message ? true : false
                }
                hint={errors.parameters && errors.parameters.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Active" htmlFor="is_active" icon={CheckSquare}>
              <Checkbox
                id="is_active"
                checked={watch("is_active")}
                onChange={(checked) => setValue("is_active", checked)}
                label=""
              />
            </HorizontalField>
          </div>
          {currentMode !== "view" && (
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

      {currentMode === "view" && data && (
        <div className="mt-4 space-y-0">
          <ScalarCard
            title="Report Fields"
            icon={<FileText size={14} />}
            fields={[
              { label: "title", value: data.title },
              { label: "type", value: data.type },
              { label: "description", value: data.description },
              { label: "parameters", value: data.parameters },
              { label: "is_active", value: data.is_active },
            ]}
            columns={2}
          />
          <BaseModelCards data={data as Record<string, unknown>} />
        </div>
      )}

      {/* Tab Navigation */}
      {recordData?.id && (
        <>
          <DetailTabs
            entityType="report_detail"
            activeTab={activeTab}
            onTabChange={setActiveTab}
            standardTabs={["actions", "comments", "documents", "raw"]}
            badges={{
              comments: recordData?.comments?.length,
              documents: recordData?.refs?.links?.document?.length,
            }}
            panelEntityType="report"
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

export default withDevIdentifier(ReportDetail, 'ReportDetail');
