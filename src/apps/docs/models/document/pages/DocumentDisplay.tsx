/**
 * DocumentDisplay - Follows 3-column standard with tab navigation
 * Tabs: Actions, Comments, Documents, History, Refs, Raw
 */
import { useEffect, useState, useMemo } from "react";
import { getRecord, saveRecord } from "@/api/wcapi";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import {
  FileText,
  Link,
  AlignLeft,
  FileCode,
  Activity,
  MessageSquare,
  FileIcon,
  History,
  Code,
  CheckSquare,
  Database,
  Shield,
  File,
  Lock,
  HardDrive,
  Clock,
  ListOrdered,
  Eye,
} from "lucide-react";

import ComponentCard from "@/components/common/ComponentCard";
import HorizontalField from "@/components/form/HorizontalField";
import {
  useColumnCount,
  ColumnSelector,
  getGridClassName,
} from "@/components/form/useColumnCount";
import { Input } from "@/components/wrapper";
import { SimpleDetailHeader } from "@/components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "@/components/common/SimpleDetailToolbar";
import {
  DetailTabs,
  useDetailTabs,
  TabConfig,
} from "@/components/common/DetailTabs";

// Panels
import CommentsPanel from "@/apps/common/components/panels/CommentsPanel";
import DocumentsPanel from "@/apps/common/components/panels/DocumentsPanel";
import ActionsPanel from "@/apps/common/components/panels/ActionsPanel";
import RefsPanel from "@/apps/common/components/panels/RefsPanel";
import JsonFieldEditor from "@/apps/common/components/JsonFieldEditor";

interface DocumentDisplayProps {
  inline?: boolean;
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  onSaved?: () => void;
  onCancelInline?: () => void;
}

const STORAGE_KEY = "documentDisplay_columnCount";

export default function DocumentDisplay({
  inline = false,
  modeProp,
  dataProp,
  onSaved,
  onCancelInline,
}: DocumentDisplayProps) {
  const [data, setData] = useState<any>(dataProp || {});
  const [loading, setLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const dispatch = useDispatch();
  const initialMode: "add" | "edit" | "view" = modeProp || "view";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);

  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  // Tab navigation
  const { activeTab, setActiveTab } = useDetailTabs("document_display", "actions", [
    "actions", "comments", "documents", "history", "refs", "raw",
  ]);

  // Tab configuration
  const tabs: TabConfig[] = useMemo(
    () => [
      { id: "actions", label: "Actions", icon: <CheckSquare size={14} /> },
      { id: "comments", label: "Comments", icon: <MessageSquare size={14} />, badge: data?.comments?.length },
      { id: "documents", label: "Documents", icon: <FileIcon size={14} />, badge: data?.refs?.links?.document?.length },
      { id: "history", label: "History", icon: <History size={14} /> },
      { id: "refs", label: "Refs", icon: <Link size={14} />, badge: data?.refs?.links ? Object.keys(data.refs.links).length : undefined },
      { id: "raw", label: "Raw", icon: <Code size={14} /> },
    ],
    [data]
  );

  useEffect(() => {
    if (modeProp === "edit" && dataProp?.id) {
      const fetchData = async () => {
        try {
          setLoading(true);
          const rec = await getRecord('document', dataProp.id);
          setData(rec.record || rec);
        } catch (error) {
          console.error("Failed to fetch record", error);
        } finally {
          setLoading(false);
        }
      };
      fetchData();
    } else if (modeProp === "add") {
      setData({});
    } else if (dataProp) {
      setData(dataProp);
    }
  }, [modeProp, dataProp]);

  const handleSave = async () => {
    try {
      setIsSaving(true);
      await saveRecord('document', data);
      dispatch(showToast({ message: "Document saved successfully", type: "success" }));
      onSaved?.();
      if (currentMode === "add") {
        onCancelInline?.();
      } else {
        setCurrentMode("view");
      }
    } catch (error) {
      console.error("Failed to save", error);
      dispatch(showToast({ message: "Failed to save document", type: "error" }));
    } finally {
      setIsSaving(false);
    }
  };

  const handleEdit = () => setCurrentMode("edit");

  const handleCancel = () => {
    if (inline && onCancelInline) {
      onCancelInline();
    } else if (initialMode === "add") {
      onCancelInline?.();
    } else {
      if (dataProp) setData(dataProp);
      setCurrentMode("view");
    }
  };

  const handleFieldChange = (field: string, value: string | number) => {
    setData({ ...data, [field]: value });
  };

  return (
    <>
      {/* Header */}
      <SimpleDetailHeader
        entityName="Document"
        recordId={data?.id}
        recordName={data?.name}
        mode={currentMode}
        backUrl=""
        showBackButton={false}
      />

      {/* Toolbar */}
      <SimpleDetailToolbar
        mode={currentMode}
        isSaving={isSaving}
        onSave={handleSave}
        onCancel={handleCancel}
        onEdit={handleEdit}
      />

      {/* Loading state */}
      {loading && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500"></div>
          <span className="ml-3 text-slate-600 dark:text-slate-400">Loading...</span>
        </div>
      )}

      {/* Basic Information Panel */}
      {!loading && (
        <ComponentCard>
          <div className="flex justify-end mb-4">
            <ColumnSelector value={columnCount} onChange={setColumnCount} />
          </div>
          <div className={getGridClassName(columnCount)}>
            <HorizontalField label="Name" htmlFor="name" icon={<FileText size={14} />}>
              <Input
                type="text"
                id="name"
                placeholder="Document Name"
                value={data?.name || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("name", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Slug" htmlFor="slug" icon={<Link size={14} />}>
              <Input
                type="text"
                id="slug"
                placeholder="URL-friendly identifier"
                value={data?.slug || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("slug", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Status" htmlFor="status" icon={<Activity size={14} />}>
              <Input
                type="text"
                id="status"
                placeholder="Document Status"
                value={data?.status || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("status", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Model Name" htmlFor="model_name" icon={<Database size={14} />}>
              <Input
                type="text"
                id="model_name"
                placeholder="Source model type"
                value={data?.model_name || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("model_name", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Confidential" htmlFor="confidential" icon={<Shield size={14} />}>
              <Input
                type="text"
                id="confidential"
                placeholder="Confidentiality level"
                value={data?.confidential || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("confidential", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="MIME Type" htmlFor="mime_type" icon={<File size={14} />}>
              <Input
                type="text"
                id="mime_type"
                placeholder="e.g. application/pdf"
                value={data?.mime_type || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("mime_type", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Checksum" htmlFor="checksum" icon={<Lock size={14} />}>
              <Input
                type="text"
                id="checksum"
                placeholder="File checksum"
                value={data?.checksum || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("checksum", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Size (bytes)" htmlFor="size_bytes" icon={<HardDrive size={14} />}>
              <Input
                type="number"
                id="size_bytes"
                placeholder="File size"
                value={data?.size_bytes ?? ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("size_bytes", parseInt(e.target.value) || 0)}
                disabled={true}
              />
            </HorizontalField>
            <HorizontalField label="Retention (days)" htmlFor="retention_period" icon={<Clock size={14} />}>
              <Input
                type="number"
                id="retention_period"
                placeholder="Retention period"
                value={data?.retention_period ?? ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("retention_period", parseInt(e.target.value) || 0)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Sequence" htmlFor="sequence" icon={<ListOrdered size={14} />}>
              <Input
                type="number"
                id="sequence"
                placeholder="Display order"
                value={data?.sequence ?? 0}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("sequence", parseInt(e.target.value) || 0)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Access Count" htmlFor="count_accessed" icon={<Eye size={14} />}>
              <Input
                type="number"
                id="count_accessed"
                value={data?.count_accessed ?? 0}
                disabled={true}
              />
            </HorizontalField>
          </div>
          {/* Full-width fields */}
          <div className="mt-4 space-y-4">
            <HorizontalField label="Description" htmlFor="description" icon={<AlignLeft size={14} />}>
              <Input
                type="text"
                id="description"
                placeholder="Short description"
                value={data?.description || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("description", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Body" htmlFor="body" icon={<FileCode size={14} />}>
              <textarea
                id="body"
                placeholder="Document body/content"
                value={data?.body || ""}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleFieldChange("body", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                rows={6}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Comment" htmlFor="comment" icon={<MessageSquare size={14} />}>
              <textarea
                id="comment"
                placeholder="General notes"
                value={data?.comment || ""}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleFieldChange("comment", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                rows={3}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
          </div>
        </ComponentCard>
      )}

      {/* Tab Navigation - only show when viewing/editing existing record */}
      {!loading && data?.id && (
        <>
          <DetailTabs
            entityType="document_display"
            activeTab={activeTab}
            onTabChange={setActiveTab}
            standardTabs={[]}
            additionalTabs={tabs}
          />

          {/* Tab Content */}
          <div className="mt-4">
            {activeTab === "actions" && (
              <ActionsPanel
                entityType="document"
                entityId={data?.id}
                data={data?.actions?.items}
                actionIds={data?.actions?.ids}
                isEditing={currentMode !== "view"}
                onChange={(actions) =>
                  console.log("Actions updated:", actions)
                }
              />
            )}

            {activeTab === "comments" && (
              <CommentsPanel
                comments={data?.comments}
                isEditing={currentMode !== "view"}
                entityType="document"
                entityId={data?.id}
              />
            )}

            {activeTab === "documents" && (
              <DocumentsPanel
                parentType="document"
                parentId={data?.id}
                data={data?.refs?.links?.document}
                isEditing={currentMode !== "view"}
                onChange={(docs) => console.log("Documents updated:", docs)}
              />
            )}

            {activeTab === "history" && (
              <ComponentCard>
                <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
                  Change History
                </h3>
                {data?.metadata?.history?.length > 0 ? (
                  <div className="space-y-3">
                    {data.metadata.history.map((entry: any, idx: number) => (
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
                entityType="document"
                entityId={data?.id}
                data={data?.refs}
                isEditing={currentMode !== "view"}
                onChange={(refs) => console.log("Refs updated:", refs)}
              />
            )}

            {activeTab === "raw" && (
              <JsonFieldEditor
                label="Full Document JSON"
                value={data}
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