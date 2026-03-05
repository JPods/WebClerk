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
import { createSerial, updateSerial } from "../services/serialApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { serialSchema } from "../utils/serialSchema";
import { SerialAddProps } from "../types/serialType";
import { Hash, Package, Activity, FileText, CheckSquare, MessageSquare, FileIcon, History, Link, Code } from "lucide-react";

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

const STORAGE_KEY = "serialDetail_columnCount";

function SerialDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: SerialAddProps) {
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
  const { activeTab, setActiveTab } = useDetailTabs("serial_detail", "actions", [
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
  } = useForm<z.infer<typeof serialSchema>>({
    resolver: zodResolver(serialSchema),
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

  const onSubmit = async (formData: z.infer<typeof serialSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createSerial(formData)
          : await updateSerial({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Serial ${
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
              ? "Edit Serial"
              : currentMode === "view"
              ? "View Serial"
              : "Serial Detail"
          }
        />
      )}
      
      {/* Header with entity name, ID, and mode indicator */}
      <SimpleDetailHeader
        entityName="Serial"
        recordId={data?.id}
        recordName={data?.serial_number}
        mode={currentMode}
        backUrl={inline ? undefined : "/products/serials"}
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
              label="Serial Number"
              htmlFor="serial_number"
              required
              icon={<Hash size={14} />}
              error={errors.serial_number?.message}
            >
              <Input
                type="text"
                id="serial_number"
                placeholder="Serial Number"
                {...register("serial_number")}
                disabled={currentMode === "view"}
              />
            </HorizontalField>

            <HorizontalField
              label="Item ID"
              htmlFor="item_id"
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
              label="Status"
              htmlFor="status"
              icon={<Activity size={14} />}
              error={errors.status?.message}
            >
              <Input
                type="text"
                id="status"
                placeholder="Status"
                {...register("status")}
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
            title="Serial Fields"
            icon={<Hash size={14} />}
            fields={[
              { label: "serial_number", value: data.serial_number },
              { label: "item_id", value: data.item_id },
              { label: "status", value: data.status },
              { label: "description", value: data.description },
            ]}
            columns={columnCount as 1 | 2 | 3}
          />
          <BaseModelCards data={data as Record<string, unknown>} />
        </div>
      )}

      {/* Tab Navigation - only show when viewing/editing existing record */}
      {recordData?.id && (
        <>
          <DetailTabs
            entityType="serial_detail"
            activeTab={activeTab}
            onTabChange={setActiveTab}
            standardTabs={[]}
            additionalTabs={tabs}
          />

          {/* Tab Content */}
          <div className="mt-4">
            {activeTab === "actions" && (
              <ActionsPanel
                entityType="serial"
                entityId={recordData?.id}
                data={recordData?.actions?.items}
                actionIds={recordData?.actions?.ids}
                isEditing={currentMode !== "view"}
                onChange={(actions) =>
                  setRecordData({ ...recordData, actions: { ...recordData.actions, items: actions } })
                }
              />
            )}

            {activeTab === "comments" && (
              <CommentsPanel
                comments={recordData?.comments}
                isEditing={currentMode !== "view"}
                entityType="serial"
                entityId={recordData?.id}
                onChange={(comments) => setRecordData({ ...recordData, comments })}
              />
            )}

            {activeTab === "documents" && (
              <DocumentsPanel
                parent_model="serial"
                parentId={recordData?.id}
                data={recordData?.refs?.links?.document}
                isEditing={currentMode !== "view"}
                onChange={(docs) =>
                  setRecordData({
                    ...recordData,
                    refs: { ...recordData.refs, links: { ...recordData.refs?.links, document: docs } },
                  })
                }
              />
            )}

            {activeTab === "history" && (
              <ComponentCard>
                <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
                  Change History
                </h3>
                {recordData?.metadata?.history?.length > 0 ? (
                  <div className="space-y-3">
                    {recordData.metadata.history.map((entry: any, idx: number) => (
                      <div
                        key={idx}
                        className="flex items-start gap-3 p-3 bg-slate-50 dark:bg-slate-800 rounded-lg"
                      >
                        <History size={16} className="text-slate-400 mt-0.5" />
                        <div className="flex-1 text-sm">
                          <div className="text-slate-900 dark:text-white">
                            {entry.action || entry.description || "Change"}
                          </div>
                          <div className="text-slate-500 text-xs">
                            {entry.timestamp
                              ? new Date(entry.timestamp).toLocaleString()
                              : entry.dt_created
                              ? new Date(entry.dt_created * 1000).toLocaleString()
                              : "--"}
                            {entry.user && ` by ${entry.user}`}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-500 text-sm">No history available</p>
                )}
              </ComponentCard>
            )}

            {activeTab === "refs" && (
              <RefsPanel
                entityType="serial"
                entityId={recordData?.id}
                data={recordData?.refs}
                isEditing={currentMode !== "view"}
                onChange={(refs) => setRecordData({ ...recordData, refs })}
              />
            )}

            {activeTab === "raw" && (
              <JsonFieldEditor
                label="Full Serial JSON"
                value={recordData}
                readonly
                defaultExpanded
                maxHeight="600px"
              />
            )}
          </div>
        </>
      )}
    </>
  );
}

export default withDevIdentifier(SerialDetail, 'SerialDetail');
