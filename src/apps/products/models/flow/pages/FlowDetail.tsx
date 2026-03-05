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
import { createFlow, updateFlow } from "../services/flowApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { flowSchema } from "../utils/flowSchema";
import { FlowAddProps } from "../types/flowType";
import { GitBranch, FileText, ListOrdered, CheckSquare, MessageSquare, FileIcon, History, Link, Code } from "lucide-react";

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

const STORAGE_KEY = "flowDetail_columnCount";

function FlowDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: FlowAddProps) {
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
  const { activeTab, setActiveTab } = useDetailTabs("flow_detail", "actions", [
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
  } = useForm<z.infer<typeof flowSchema>>({
    resolver: zodResolver(flowSchema),
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

  const onSubmit = async (formData: z.infer<typeof flowSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createFlow(formData)
          : await updateFlow({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Flow ${
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
              ? "Edit Flow"
              : currentMode === "view"
              ? "View Flow"
              : "Flow Detail"
          }
        />
      )}
      
      {/* Header with entity name, ID, and mode indicator */}
      <SimpleDetailHeader
        entityName="Flow"
        recordId={data?.id}
        recordName={data?.name}
        mode={currentMode}
        backUrl={inline ? undefined : "/products/flows"}
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
              label="Name"
              htmlFor="name"
              required
              icon={<GitBranch size={14} />}
              error={errors.name?.message}
            >
              <Input
                type="text"
                id="name"
                placeholder="Flow Name"
                {...register("name")}
                disabled={currentMode === "view"}
              />
            </HorizontalField>

            <HorizontalField
              label="Steps"
              htmlFor="steps"
              icon={<ListOrdered size={14} />}
              error={errors.steps?.message}
            >
              <Input
                type="text"
                id="steps"
                placeholder="Steps (JSON)"
                {...register("steps")}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
          </div>

          <HorizontalField
            label="Description"
            htmlFor="description"
            icon={<FileText size={14} />}
            error={errors.description?.message}
          >
            <Input
              type="text"
              id="description"
              placeholder="Description"
              {...register("description")}
                disabled={currentMode === "view"}
            />
          </HorizontalField>

        </form>
      </ComponentCard>

      {currentMode === "view" && data && (
        <div className="mt-4 space-y-0">
          <ScalarCard
            title="Flow Fields"
            icon={<GitBranch size={14} />}
            fields={[
              { label: "name", value: data.name },
              { label: "steps", value: data.steps },
              { label: "description", value: data.description },
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
        <ActionsPanel entityType="flow" recordId={data?.id} />
      )}
      {activeTab === "comments" && (
        <CommentsPanel entityType="flow" recordId={data?.id} />
      )}
      {activeTab === "documents" && (
        <DocumentsPanel entityType="flow" recordId={data?.id} />
      )}
      {activeTab === "history" && (
        <ComponentCard title="History">
          <p className="text-gray-500 dark:text-gray-400">History coming soon...</p>
        </ComponentCard>
      )}
      {activeTab === "refs" && (
        <RefsPanel entityType="flow" recordId={data?.id} />
      )}
      {activeTab === "raw" && (
        <JsonFieldEditor
          label="Full Flow JSON"
          value={recordData}
          readOnly={true}
        />
      )}
    </>
  );
}

export default withDevIdentifier(FlowDetail, 'FlowDetail');
