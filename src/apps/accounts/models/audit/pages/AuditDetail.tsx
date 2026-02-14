import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CheckSquare, MessageSquare, FileIcon, History, Link, Code, FileText, SlidersHorizontal } from "lucide-react";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input, CustTextArea } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";
import { createAudit, updateAudit } from "../services/auditApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { auditSchema } from "../utils/auditSchema";
import { AuditAddProps } from "../types/auditType";

// Tab navigation
import { DetailTabs, useDetailTabs, TabConfig } from "@/components/common/DetailTabs";

// Panels
import { ActionsPanel, CommentsPanel, DocumentsPanel, MetadataPanel, PrefsPanel, RefsPanel } from "@/apps/common/components/panels";
import JsonFieldEditor from "@/apps/common/components/JsonFieldEditor";

export default function AuditDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: AuditAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof auditSchema>>({
    resolver: zodResolver(auditSchema),
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  const [isSaving, setIsSaving] = useState(false);
  const data = dataProp || routeState.data || null;

  // Full record data for panels
  const [recordData, setRecordData] = useState<any>(data || {});

  // Tab navigation
  const { activeTab, setActiveTab } = useDetailTabs("audit_detail", "actions", [
    "actions", "comments", "documents", "history", "metadata", "prefs", "raw", "refs",
  ]);

  const tabs: TabConfig[] = useMemo(
    () => [
      { id: "actions", label: "Actions", icon: <CheckSquare size={14} /> },
      { id: "comments", label: "Comments", icon: <MessageSquare size={14} />, badge: recordData?.comments?.length },
      { id: "documents", label: "Documents", icon: <FileIcon size={14} />, badge: recordData?.refs?.links?.document?.length },
      { id: "history", label: "History", icon: <History size={14} /> },
      { id: "metadata", label: "Metadata", icon: <FileText size={14} /> },
      { id: "prefs", label: "Prefs", icon: <SlidersHorizontal size={14} /> },
      { id: "raw", label: "Raw", icon: <Code size={14} /> },
      { id: "refs", label: "Refs", icon: <Link size={14} /> },
    ],
    [recordData],
  );

  const handleEdit = () => setCurrentMode("edit");
  const handleCancel = () => {
    if (inline && onCancelInline) {
      onCancelInline();
    } else if (initialMode === "add") {
      // Navigate back or reset
    } else {
      setCurrentMode("view");
    }
  };
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

  const onSubmit = async (formData: z.infer<typeof auditSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createAudit(formData)
          : await updateAudit({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Audit ${
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

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            currentMode === "edit"
              ? "Edit Audit"
              : currentMode === "view"
              ? "View Audit"
              : "Audit Detail"
          }
        />
      )}

      <SimpleDetailHeader
        entityName="Audit"
        recordId={data?.id}
        recordName={data?.action || data?.description}
        mode={currentMode}
        backUrl={inline ? undefined : "/accounts/audits"}
        onClose={inline ? onCancelInline : undefined}
      />

      <SimpleDetailToolbar
        mode={currentMode}
        isSaving={isSaving}
        onSave={handleSubmit(onSubmit)}
        onCancel={handleCancel}
        onEdit={handleEdit}
      />

      <ComponentCard>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="date">date</Label>
              <Input
                type="date"
                id="date"
                placeholder="Audit Date"
                {...register("date")}
                error={errors.date && errors.date.message ? true : false}
                hint={errors.date && errors.date.message}
                disabled={currentMode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="action">action</Label>
              <Input
                type="text"
                id="action"
                placeholder="Audit Action"
                {...register("action")}
                error={errors.action && errors.action.message ? true : false}
                hint={errors.action && errors.action.message}
                disabled={currentMode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="user">user</Label>
              <Input
                type="text"
                id="user"
                placeholder="User"
                {...register("user")}
                error={errors.user && errors.user.message ? true : false}
                hint={errors.user && errors.user.message}
                disabled={currentMode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4">
            <div>
              <Label htmlFor="description">description</Label>
              <CustTextArea
                id="description"
                placeholder="Audit Description"
                {...register("description")}
                error={errors.description && errors.description.message ? true : false}
                hint={errors.description && errors.description.message}
                disabled={currentMode === "view"}
              />
            </div>
          </div>
        </form>
      </ComponentCard>

      {/* Tab Navigation */}
      {recordData?.id && (
        <>
          <DetailTabs
            entityType="audit_detail"
            activeTab={activeTab}
            onTabChange={setActiveTab}
            standardTabs={[]}
            additionalTabs={tabs}
          />
          <div className="mt-4">
            {activeTab === "actions" && (
              <ActionsPanel entityType="audit" entityId={recordData.id} data={recordData?.actions?.items} actionIds={recordData?.actions?.ids} isEditing={currentMode !== "view"} onChange={(actions: any) => setRecordData({ ...recordData, actions: { ...recordData.actions, items: actions } })} />
            )}
            {activeTab === "comments" && (
              <CommentsPanel comments={recordData?.comments} isEditing={currentMode !== "view"} entityType="audit" entityId={recordData.id} onChange={(comments: any) => setRecordData({ ...recordData, comments })} />
            )}
            {activeTab === "documents" && (
              <DocumentsPanel parent_model="audit" parentId={recordData.id} data={recordData?.refs?.links?.document} isEditing={currentMode !== "view"} onChange={(docs: any) => setRecordData({ ...recordData, refs: { ...recordData.refs, links: { ...recordData.refs?.links, document: docs } } })} />
            )}
            {activeTab === "history" && (
              <MetadataPanel entityType="audit" entityId={recordData.id} data={recordData?.metadata} />
            )}
            {activeTab === "metadata" && (
              <MetadataPanel entityType="audit" entityId={recordData.id} data={recordData?.metadata} />
            )}
            {activeTab === "prefs" && (
              <PrefsPanel entityType="audit" entityId={recordData.id} data={recordData?.prefs} />
            )}
            {activeTab === "raw" && (
              <JsonFieldEditor label="Full Audit JSON" value={recordData} readonly defaultExpanded maxHeight="600px" />
            )}
            {activeTab === "refs" && (
              <RefsPanel entityType="audit" entityId={recordData.id} data={recordData?.refs} isEditing={currentMode !== "view"} onChange={(refs: any) => setRecordData({ ...recordData, refs })} />
            )}
          </div>
        </>
      )}
    </>
  );
}