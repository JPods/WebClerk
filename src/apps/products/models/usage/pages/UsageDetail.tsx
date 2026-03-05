import { useEffect, useState, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import { HorizontalField } from "../../../../../components/form/HorizontalField";
import { useColumnCount, ColumnSelector, getGridClassName } from "../../../../../components/form/useColumnCount";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";
import { createUsage, updateUsage } from "../services/usageApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { usageSchema } from "../utils/usageSchema";
import { UsageAddProps } from "../types/usageType";
import { Package, User, Hash, Calendar, FileText, CheckSquare, MessageSquare, FileIcon, History, Link, Code } from "lucide-react";

// Tab navigation
import { DetailTabs, useDetailTabs, TabConfig } from "@/components/common/DetailTabs";

// Panels
import CommentsPanel from "@/apps/common/components/panels/CommentsPanel";
import DocumentsPanel from "@/apps/common/components/panels/DocumentsPanel";
import ActionsPanel from "@/apps/common/components/panels/ActionsPanel";
import RefsPanel from "@/apps/common/components/panels/RefsPanel";
import JsonFieldEditor from "@/apps/common/components/JsonFieldEditor";
import { ScalarCard, BaseModelCards } from "@/apps/common/components/detail";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

const STORAGE_KEY = "usageDetail_columnCount";

function UsageDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: UsageAddProps) {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);
  const [isSaving, setIsSaving] = useState(false);

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;
  
  // Mode state for switching between view/edit
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);

  // Full record data for panels (needed for tabs)
  const [recordData, setRecordData] = useState<any>(data || {});

  // Tab navigation
  const { activeTab, setActiveTab } = useDetailTabs("usage_detail", "actions", [
    "actions", "comments", "documents", "history", "refs", "raw",
  ]);

  // Tab configuration
  const tabs: TabConfig[] = useMemo(
    () => [
      { id: "actions", label: "Actions", icon: <CheckSquare size={14} /> },
      { id: "comments", label: "Comments", icon: <MessageSquare size={14} />, badge: recordData?.comments?.length },
      { id: "documents", label: "Documents", icon: <FileIcon size={14} />, badge: recordData?.refs?.links?.document?.length },
      { id: "history", label: "History", icon: <History size={14} /> },
      { id: "refs", label: "Refs", icon: <Link size={14} /> },
      { id: "raw", label: "Raw", icon: <Code size={14} /> },
    ],
    [recordData]
  );

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof usageSchema>>({
    resolver: zodResolver(usageSchema),
  });

  useEffect(() => {
    if (currentMode === "add") {
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
  }, [data, reset, setValue, currentMode]);

  const onSubmit = async (formData: z.infer<typeof usageSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createUsage(formData)
          : await updateUsage({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Usage ${
              currentMode === "add" ? "created" : "updated"
            } successfully`,
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        } else {
          // Switch to view mode after save
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
      // Reset form and go back to view mode
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
              ? "Edit Usage"
              : currentMode === "view"
              ? "View Usage"
              : "Usage Detail"
          }
        />
      )}
      
      {/* Header with entity name, ID, and mode indicator */}
      <SimpleDetailHeader
        entityName="Usage"
        recordId={data?.id}
        recordName={data?.item_id}
        mode={currentMode}
        backUrl={inline ? undefined : "/products/usages"}
      />

      {/* Toolbar with action buttons */}
      <SimpleDetailToolbar
        mode={currentMode}
        isSaving={isSaving}
        onSave={handleSubmit(onSubmit)}
        onCancel={handleCancel}
        onEdit={handleEdit}
      />

      <ComponentCard>
        <div className="flex justify-end mb-4">
          <ColumnSelector columnCount={columnCount} setColumnCount={setColumnCount} />
        </div>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className={getGridClassName(columnCount)}>
            <HorizontalField
              label="Item ID"
              htmlFor="item_id"
              required
              icon={<Package size={14} />}
              error={errors.item_id?.message}
            >
              <Input
                type="text"
                id="item_id"
                placeholder="Item ID"
                {...register("item_id")}
                disabled={currentMode === "view"}
              />
            </HorizontalField>

            <HorizontalField
              label="User ID"
              htmlFor="user_id"
              icon={<User size={14} />}
              error={errors.user_id?.message}
            >
              <Input
                type="text"
                id="user_id"
                placeholder="User ID"
                {...register("user_id")}
                disabled={currentMode === "view"}
              />
            </HorizontalField>

            <HorizontalField
              label="Quantity"
              htmlFor="quantity_used"
              icon={<Hash size={14} />}
              error={errors.quantity_used?.message}
            >
              <Input
                type="number"
                id="quantity_used"
                placeholder="Quantity Used"
                {...register("quantity_used", { valueAsNumber: true })}
                disabled={currentMode === "view"}
              />
            </HorizontalField>

            <HorizontalField
              label="Date Used"
              htmlFor="date_used"
              icon={<Calendar size={14} />}
              error={errors.date_used?.message}
            >
              <Input
                type="date"
                id="date_used"
                placeholder="Date Used"
                {...register("date_used")}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
          </div>

          <HorizontalField
            label="Notes"
            htmlFor="notes"
            icon={<FileText size={14} />}
            error={errors.notes?.message}
          >
            <Input
              type="text"
              id="notes"
              placeholder="Notes"
              {...register("notes")}
              disabled={currentMode === "view"}
            />
          </HorizontalField>
        </form>
      </ComponentCard>

      {currentMode === "view" && data && (
        <div className="mt-4 space-y-0">
          <ScalarCard
            title="Usage Fields"
            icon={<Package size={14} />}
            fields={[
              { label: "item_id", value: data.item_id },
              { label: "user_id", value: data.user_id },
              { label: "quantity_used", value: data.quantity_used },
              { label: "date_used", value: data.date_used },
              { label: "notes", value: data.notes },
            ]}
            columns={columnCount as 1 | 2 | 3}
          />
          <BaseModelCards data={data as Record<string, unknown>} />
        </div>
      )}

      {/* Tab Navigation */}
      <DetailTabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Tab Content */}
      {activeTab === "actions" && (
        <ActionsPanel entityType="usage" entityId={data?.id} />
      )}
      {activeTab === "comments" && (
        <CommentsPanel entityType="usage" entityId={data?.id} />
      )}
      {activeTab === "documents" && (
        <DocumentsPanel entityType="usage" entityId={data?.id} />
      )}
      {activeTab === "history" && (
        <ComponentCard title="History">
          <p className="text-gray-500 dark:text-gray-400">History panel coming soon...</p>
        </ComponentCard>
      )}
      {activeTab === "refs" && (
        <RefsPanel entityType="usage" entityId={data?.id} refs={recordData?.refs} />
      )}
      {activeTab === "raw" && (
        <ComponentCard title="Full Usage JSON">
          <JsonFieldEditor value={recordData} label="Full Usage JSON" />
        </ComponentCard>
      )}
    </>
  );
}

export default withDevIdentifier(UsageDetail, 'UsageDetail');
