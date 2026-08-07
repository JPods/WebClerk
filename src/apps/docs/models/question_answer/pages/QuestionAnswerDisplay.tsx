/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * QuestionAnswerDisplay - Follows 3-column standard with tab navigation
 * Tabs: Actions, Comments, Documents, History, Refs, Raw
 */
import { useEffect, useState, useMemo } from "react";
import { getRecord, saveRecord } from "@/api/wcapi";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import {
  HelpCircle,
  MessageCircle,
  Activity,
  MessageSquare,
  FileIcon,
  History,
  Code,
  CheckSquare,
  Link,
  Image,
  Hash,
  User,
  ListOrdered,
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

interface QuestionAnswerDisplayProps {
  inline?: boolean;
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  onSaved?: () => void;
  onCancelInline?: () => void;
}

const STORAGE_KEY = "questionAnswerDisplay_columnCount";

export default function QuestionAnswerDisplay({
  inline = false,
  modeProp,
  dataProp,
  onSaved,
  onCancelInline,
}: QuestionAnswerDisplayProps) {
  const [data, setData] = useState<any>(dataProp || {});
  const [loading, setLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const dispatch = useDispatch();
  const initialMode: "add" | "edit" | "view" = modeProp || "view";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);

  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  // Tab navigation
  const { activeTab, setActiveTab } = useDetailTabs("question_answer", "actions", [
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
          const rec = await getRecord('question_answer', dataProp.id);
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
      await saveRecord('question_answer', data);
      dispatch(showToast({ message: "Question Answer saved successfully", type: "success" }));
      onSaved?.();
      if (currentMode === "add") {
        onCancelInline?.();
      } else {
        setCurrentMode("view");
      }
    } catch (error) {
      console.error("Failed to save", error);
      dispatch(showToast({ message: "Failed to save question answer", type: "error" }));
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

  const handleNestedFieldChange = (path: string[], value: string) => {
    const newData = { ...data };
    let current = newData;
    for (let i = 0; i < path.length - 1; i++) {
      if (!current[path[i]]) current[path[i]] = {};
      current = current[path[i]];
    }
    current[path[path.length - 1]] = value;
    setData(newData);
  };

  return (
    <>
      {/* Header */}
      <SimpleDetailHeader
        entityName="Question & Answer"
        recordId={data?.id}
        recordName={data?.question?.substring(0, 50) || data?.name}
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
            <HorizontalField label="Question" htmlFor="question" icon={<HelpCircle size={14} />}>
              <Input
                type="text"
                id="question"
                placeholder="Question"
                value={data?.question || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("question", e.target.value)}
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
            <HorizontalField label="Sequence" htmlFor="sequence" icon={<ListOrdered size={14} />}>
              <Input
                type="number"
                id="sequence"
                placeholder="0"
                value={data?.sequence ?? ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("sequence", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Parent Model" htmlFor="parent_model" icon={<Hash size={14} />}>
              <Input
                type="text"
                id="parent_model"
                placeholder="e.g. order, customer"
                value={data?.parent_model || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("parent_model", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Parent ID" htmlFor="parent_id" icon={<Hash size={14} />}>
              <Input
                type="number"
                id="parent_id"
                placeholder="Parent Record ID"
                value={data?.parent_id ?? ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("parent_id", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Answered By" htmlFor="answered_by" icon={<User size={14} />}>
              <Input
                type="text"
                id="answered_by"
                placeholder="Contact who answered"
                value={data?.answered_by?.attention || data?.answered_by?.id || ""}
                disabled={true}
              />
            </HorizontalField>
          </div>
          <div className="mt-4">
            <HorizontalField label="Answer" htmlFor="answer" icon={<MessageCircle size={14} />}>
              <textarea
                id="answer"
                placeholder="Answer"
                value={data?.answer || ""}
                onChange={(e) => handleFieldChange("answer", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                rows={4}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
          </div>
        </ComponentCard>
      )}

      {/* Image Paths Panel */}
      {!loading && (
        <ComponentCard>
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <Image size={16} /> Image Paths
          </h3>
          <div className={getGridClassName(columnCount)}>
            <HorizontalField label="Primary Image" htmlFor="image_primary" icon={<Image size={14} />}>
              <Input
                type="text"
                id="image_primary"
                placeholder="/path/to/image.jpg"
                value={data?.metadata?.images?.primary || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleNestedFieldChange(["metadata", "images", "primary"], e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Thumbnail" htmlFor="image_thumbnail" icon={<Image size={14} />}>
              <Input
                type="text"
                id="image_thumbnail"
                placeholder="/path/to/thumbnail.jpg"
                value={data?.metadata?.images?.thumbnail || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleNestedFieldChange(["metadata", "images", "thumbnail"], e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
          </div>
          {/* Image Preview */}
          {(data?.metadata?.images?.primary || data?.metadata?.images?.thumbnail) && (
            <div className="mt-4 flex gap-4">
              {data?.metadata?.images?.primary && (
                <div className="text-center">
                  <p className="text-xs text-slate-500 mb-1">Primary</p>
                  <img
                    src={data.metadata.images.primary}
                    alt="Primary"
                    className="max-h-32 rounded border border-gray-200 dark:border-gray-700"
                    onError={(e) => (e.currentTarget.style.display = 'none')}
                  />
                </div>
              )}
              {data?.metadata?.images?.thumbnail && (
                <div className="text-center">
                  <p className="text-xs text-slate-500 mb-1">Thumbnail</p>
                  <img
                    src={data.metadata.images.thumbnail}
                    alt="Thumbnail"
                    className="max-h-32 rounded border border-gray-200 dark:border-gray-700"
                    onError={(e) => (e.currentTarget.style.display = 'none')}
                  />
                </div>
              )}
            </div>
          )}
        </ComponentCard>
      )}

      {/* Tab Navigation - only show when viewing/editing existing record */}
      {!loading && data?.id && (
        <>
          <DetailTabs
            entityType="question_answer"
            activeTab={activeTab}
            onTabChange={setActiveTab}
            standardTabs={[]}
            additionalTabs={tabs}
          />

          <div className="mt-4">
            {activeTab === "actions" && (
              <ActionsPanel
                entityType="question_answer"
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
                entityType="question_answer"
                entityId={data?.id}
              />
            )}

            {activeTab === "documents" && (
              <DocumentsPanel
                parent_model="question_answer"
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
                entityType="question_answer"
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