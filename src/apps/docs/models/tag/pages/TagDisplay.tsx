/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * TagDisplay - Follows 3-column standard with tab navigation
 * Tabs: Actions, Comments, Documents, History, Refs, Raw
 */
import { useEffect, useState, useMemo } from "react";
import { getRecord, saveRecord } from "@/api/wcapi";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import {
  Tag,
  CheckSquare,
  MessageSquare,
  FileIcon,
  History,
  Code,
  Link,
  Target,
  Activity,
  Hash,
  ListOrdered,
  Eye,
  Database,
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
import { DetailToolbar } from "@/components/common/DetailToolbar";
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

interface TagDisplayProps {
  inline?: boolean;
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  onSaved?: () => void;
  onCancelInline?: () => void;
}

const STORAGE_KEY = "tagDisplay_columnCount";

export default function TagDisplay({
  inline = false,
  modeProp,
  dataProp,
  onSaved,
  onCancelInline,
}: TagDisplayProps) {
  const [data, setData] = useState<any>(dataProp || {});
  const [loading, setLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const dispatch = useDispatch();
  const initialMode: "add" | "edit" | "view" = modeProp || "view";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);

  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  // Tab navigation
  const { activeTab, setActiveTab } = useDetailTabs("tag", "actions", [
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
          const rec = await getRecord('tag', dataProp.id);
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
      await saveRecord('tag', data);
      dispatch(showToast({ message: "Tag saved successfully", type: "success" }));
      onSaved?.();
      if (currentMode === "add") {
        onCancelInline?.();
      } else {
        setCurrentMode("view");
      }
    } catch (error) {
      console.error("Failed to save", error);
      dispatch(showToast({ message: "Failed to save tag", type: "error" }));
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

  const handleFieldChange = (field: string, value: string) => {
    setData({ ...data, [field]: value });
  };

  return (
    <>
      {/* Header */}
      <SimpleDetailHeader
        entityName="Tag"
        recordId={data?.id}
        recordName={data?.name}
        mode={currentMode}
        backUrl=""
        showBackButton={false}
      />

      {/* Toolbar */}
      <DetailToolbar
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
            <HorizontalField label="Name" htmlFor="name" icon={<Tag size={14} />}>
              <Input
                type="text"
                id="name"
                placeholder="Tag Name"
                value={data?.name || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("name", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Purpose" htmlFor="purpose" icon={<Target size={14} />}>
              <Input
                type="text"
                id="purpose"
                placeholder="Purpose"
                value={data?.purpose || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("purpose", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Status" htmlFor="status" icon={<Activity size={14} />}>
              <Input
                type="text"
                id="status"
                placeholder="Status"
                value={data?.status || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("status", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Model Name" htmlFor="model_name" icon={<Database size={14} />}>
              <Input
                type="text"
                id="model_name"
                placeholder="Source model (e.g. order, item)"
                value={data?.model_name || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("model_name", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Record ID" htmlFor="record_id" icon={<Hash size={14} />}>
              <Input
                type="number"
                id="record_id"
                placeholder="ID in source table"
                value={data?.record_id ?? ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("record_id", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Sequence" htmlFor="sequence" icon={<ListOrdered size={14} />}>
              <Input
                type="number"
                id="sequence"
                placeholder="0"
                value={data?.sequence ?? 0}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("sequence", e.target.value)}
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
        </ComponentCard>
      )}

      {/* Data Payload Panel */}
      {!loading && (
        <ComponentCard>
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <Database size={16} /> Tag Data Payload
          </h3>
          <JsonFieldEditor
            label=""
            value={data?.data || {}}
            readonly={currentMode === "view"}
            defaultExpanded
            maxHeight="300px"
            onChange={(newData) => setData({ ...data, data: newData })}
          />
        </ComponentCard>
      )}

      {/* Tab Navigation - only show when viewing/editing existing record */}
      {!loading && data?.id && (
        <>
          <DetailTabs
            entityType="tag"
            activeTab={activeTab}
            onTabChange={setActiveTab}
            standardTabs={[]}
            additionalTabs={tabs}
          />

          <div className="mt-4">
            {activeTab === "actions" && (
              <ActionsPanel
                entityType="tag"
                entityId={data?.id}
                data={data?.actions?.items}
                actionIds={data?.actions?.ids}
                isEditing={currentMode !== "view"}
                onChange={(actions) => console.log("Actions updated:", actions)}
              />
            )}

            {activeTab === "comments" && (
              <CommentsPanel
                comments={data?.comments}
                isEditing={currentMode !== "view"}
                entityType="tag"
                entityId={data?.id}
              />
            )}

            {activeTab === "documents" && (
              <DocumentsPanel
                parent_model="tag"
                parentId={data?.id}
                data={data?.refs?.links?.document}
                isEditing={currentMode !== "view"}
                onChange={(docs) => console.log("Documents updated:", docs)}
              />
            )}

            {activeTab === "history" && (
              <ComponentCard>
                <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Change History</h3>
                {data?.metadata?.history?.length > 0 ? (
                  <div className="space-y-3">
                    {data.metadata.history.map((entry: any, idx: number) => (
                      <div key={idx} className="flex items-start gap-3 p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                        <History size={16} className="text-slate-400 mt-0.5" />
                        <div className="flex-1 text-sm">
                          <div className="text-slate-900 dark:text-white">{entry.action || entry.description || "Change"}</div>
                          <div className="text-slate-500 text-xs">
                            {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : entry.dt_created ? new Date(entry.dt_created * 1000).toLocaleString() : "--"}
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
                entityType="tag"
                entityId={data?.id}
                data={data?.refs}
                isEditing={currentMode !== "view"}
                onChange={(refs) => console.log("Refs updated:", refs)}
              />
            )}

            {activeTab === "raw" && (
              <JsonFieldEditor label="Full Record JSON" value={data} readonly defaultExpanded maxHeight="600px" />
            )}
          </div>
        </>
      )}
    </>
  );
}