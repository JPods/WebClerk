/**
 * MatricsDisplay - Follows 3-column standard with tab navigation
 * Tabs: Actions, Comments, Documents, History, Raw
 */
import { useEffect, useState, useMemo } from "react";
import { getRecord, saveRecord } from "@/api/wcapi";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import {
  BarChart3,
  Ruler,
  Hash,
  FileText,
  CheckSquare,
  MessageSquare,
  FileIcon,
  History,
  Code,
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
import JsonFieldEditor from "@/apps/common/components/JsonFieldEditor";

interface MatricsDisplayProps {
  inline?: boolean;
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  onSaved?: () => void;
  onCancelInline?: () => void;
}

const STORAGE_KEY = "matricsDisplay_columnCount";

export default function MatricsDisplay({
  inline = false,
  modeProp,
  dataProp,
  onSaved,
  onCancelInline,
}: MatricsDisplayProps) {
  const [data, setData] = useState<any>(dataProp || {});
  const [loading, setLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const dispatch = useDispatch();
  const initialMode: "add" | "edit" | "view" = modeProp || "view";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);

  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  // Tab navigation
  const { activeTab, setActiveTab } = useDetailTabs("matrics_display", "actions", [
    "actions", "comments", "documents", "history", "raw",
  ]);

  // Tab configuration
  const tabs: TabConfig[] = useMemo(
    () => [
      { id: "actions", label: "Actions", icon: <CheckSquare size={14} /> },
      { id: "comments", label: "Comments", icon: <MessageSquare size={14} />, badge: data?.comments?.length },
      { id: "documents", label: "Documents", icon: <FileIcon size={14} />, badge: data?.refs?.links?.document?.length },
      { id: "history", label: "History", icon: <History size={14} /> },
      { id: "raw", label: "Raw", icon: <Code size={14} /> },
    ],
    [data]
  );

  useEffect(() => {
    if (modeProp === "edit" && dataProp?.id) {
      const fetchData = async () => {
        try {
          setLoading(true);
          const rec = await getRecord('matrics', dataProp.id);
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
      await saveRecord('matrics', data);
      dispatch(showToast({ message: "Matrics saved successfully", type: "success" }));
      onSaved?.();
      if (currentMode === "add") {
        onCancelInline?.();
      } else {
        setCurrentMode("view");
      }
    } catch (error) {
      console.error("Failed to save", error);
      dispatch(showToast({ message: "Failed to save matrics", type: "error" }));
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
        entityName="Matrics"
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
            <ColumnSelector columnCount={columnCount} setColumnCount={setColumnCount} />
          </div>
          <div className={getGridClassName(columnCount)}>
            <HorizontalField label="Name" htmlFor="name" icon={<BarChart3 size={14} />}>
              <Input
                type="text"
                id="name"
                placeholder="Matrics Name"
                value={data?.name || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("name", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Unit" htmlFor="unit" icon={<Ruler size={14} />}>
              <Input
                type="text"
                id="unit"
                placeholder="Unit"
                value={data?.unit || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("unit", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Value" htmlFor="value" icon={<Hash size={14} />}>
              <Input
                type="number"
                id="value"
                placeholder="Value"
                value={data?.value ?? ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("value", Number(e.target.value))}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
          </div>
          <div className="mt-4">
            <HorizontalField label="Description" htmlFor="description" icon={<FileText size={14} />}>
              <Input
                type="text"
                id="description"
                placeholder="Description"
                value={data?.description || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("description", e.target.value)}
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
            entityType="matrics"
            activeTab={activeTab}
            onTabChange={setActiveTab}
            standardTabs={[]}
            additionalTabs={tabs}
          />

          <div className="mt-4">
            {activeTab === "actions" && (
              <ActionsPanel
                entityType="matrics"
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
                entityType="matrics"
                entityId={data?.id}
              />
            )}

            {activeTab === "documents" && (
              <DocumentsPanel
                parent_model="matrics"
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

            {activeTab === "raw" && (
              <JsonFieldEditor label="Full Record JSON" value={data} readonly defaultExpanded maxHeight="600px" />
            )}
          </div>
        </>
      )}
    </>
  );
}
