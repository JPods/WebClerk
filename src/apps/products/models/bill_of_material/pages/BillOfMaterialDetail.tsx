/**
 * BillOfMaterialDetail - Follows 3-column standard with tab navigation
 * Tabs: Actions, Comments, Documents, History, Raw
 */
import { useEffect, useState, useMemo } from "react";
import { getRecord, saveRecord } from "@/api/wcapi";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import {
  ClipboardList,
  Package,
  Layers,
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
import { ScalarCard, BaseModelCards } from "@/apps/common/components/detail";

interface BillOfMaterialDetailProps {
  inline?: boolean;
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  onSaved?: () => void;
  onCancelInline?: () => void;
}

const STORAGE_KEY = "billOfMaterialDetail_columnCount";

export default function BillOfMaterialDetail({
  inline = false,
  modeProp,
  dataProp,
  onSaved,
  onCancelInline,
}: BillOfMaterialDetailProps) {
  const [data, setData] = useState<any>(dataProp || {});
  const [loading, setLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const dispatch = useDispatch();
  // Detail pages always open in edit mode — switch to read-only only when needed.
  const initialMode: "add" | "edit" | "view" = modeProp || "edit";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);

  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  // Tab navigation
  const { activeTab, setActiveTab } = useDetailTabs("bill_of_material_detail", "actions", [
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
          const rec = await getRecord('bill_of_material', dataProp.id);
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
      await saveRecord('bill_of_material', data);
      dispatch(showToast({ message: "Bill of Material saved successfully", type: "success" }));
      onSaved?.();
      if (currentMode === "add") {
        onCancelInline?.();
      } else {
        setCurrentMode("view");
      }
    } catch (error) {
      console.error("Failed to save", error);
      dispatch(showToast({ message: "Failed to save bill of material", type: "error" }));
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

  const handleFieldChange = (field: string, value: string | number | boolean) => {
    setData({ ...data, [field]: value });
  };

  return (
    <>
      {/* Header */}
      <SimpleDetailHeader
        entityName="Bill of Material"
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
            <HorizontalField label="Name" htmlFor="name" icon={<ClipboardList size={14} />}>
              <Input
                type="text"
                id="name"
                placeholder="BOM Name"
                value={data?.name || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("name", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Product ID" htmlFor="product_id" icon={<Package size={14} />}> 
              <Input
                type="text"
                id="product_id"
                placeholder="Product ID"
                value={data?.product_id || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("product_id", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Components" htmlFor="components" icon={<Layers size={14} />}>
              <Input
                type="text"
                id="components"
                placeholder="Components (JSON)"
                value={data?.components || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("components", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Parent ID" htmlFor="parent_id" icon={<Package size={14} />}> 
              <Input
                type="text"
                id="parent_id"
                value={data?.parent_id || ""}
                onChange={(e) => handleFieldChange("parent_id", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Child ID" htmlFor="child_id" icon={<Package size={14} />}> 
              <Input
                type="text"
                id="child_id"
                value={data?.child_id || ""}
                onChange={(e) => handleFieldChange("child_id", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Revision" htmlFor="revision" icon={<Layers size={14} />}> 
              <Input
                type="text"
                id="revision"
                value={data?.revision || ""}
                onChange={(e) => handleFieldChange("revision", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Effective From" htmlFor="dt_effective_from" icon={<Layers size={14} />}> 
              <Input
                type="date"
                id="dt_effective_from"
                value={data?.dt_effective_from || ""}
                onChange={(e) => handleFieldChange("dt_effective_from", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Effective To" htmlFor="dt_effective_to" icon={<Layers size={14} />}> 
              <Input
                type="date"
                id="dt_effective_to"
                value={data?.dt_effective_to || ""}
                onChange={(e) => handleFieldChange("dt_effective_to", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Quantity" htmlFor="quantity" icon={<Layers size={14} />}> 
              <Input
                type="number"
                id="quantity"
                value={data?.quantity || ""}
                onChange={(e) => handleFieldChange("quantity", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Scrap Factor" htmlFor="scrap_factor" icon={<Layers size={14} />}> 
              <Input
                type="number"
                id="scrap_factor"
                value={data?.scrap_factor || ""}
                onChange={(e) => handleFieldChange("scrap_factor", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Yield %" htmlFor="yield_pct" icon={<Layers size={14} />}> 
              <Input
                type="number"
                id="yield_pct"
                value={data?.yield_pct || ""}
                onChange={(e) => handleFieldChange("yield_pct", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Sequence" htmlFor="sequence" icon={<Layers size={14} />}> 
              <Input
                type="number"
                id="sequence"
                value={data?.sequence || ""}
                onChange={(e) => handleFieldChange("sequence", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Is Alternate" htmlFor="is_alternate" icon={<Layers size={14} />}> 
              <Input
                type="checkbox"
                id="is_alternate"
                checked={data?.is_alternate || false}
                onChange={(e) => handleFieldChange("is_alternate", e.target.checked)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Alternate Group" htmlFor="alternate_group" icon={<Layers size={14} />}> 
              <Input
                type="text"
                id="alternate_group"
                value={data?.alternate_group || ""}
                onChange={(e) => handleFieldChange("alternate_group", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Is Optional" htmlFor="is_optional" icon={<Layers size={14} />}> 
              <Input
                type="checkbox"
                id="is_optional"
                checked={data?.is_optional || false}
                onChange={(e) => handleFieldChange("is_optional", e.target.checked)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Cost Snapshot" htmlFor="cost_snapshot" icon={<Layers size={14} />}> 
              <Input
                type="number"
                id="cost_snapshot"
                value={data?.cost_snapshot || ""}
                onChange={(e) => handleFieldChange("cost_snapshot", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Change Reason" htmlFor="change_reason" icon={<Layers size={14} />}> 
              <Input
                type="text"
                id="change_reason"
                value={data?.change_reason || ""}
                onChange={(e) => handleFieldChange("change_reason", e.target.value)}
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

      {currentMode === "view" && data && (
        <div className="mt-4 space-y-0">
          <ScalarCard
            title="BOM Fields"
            icon={<ClipboardList size={14} />}
            fields={[
              { label: "name", value: data.name },
              { label: "product_id", value: data.product_id },
              { label: "parent_id", value: data.parent_id },
              { label: "child_id", value: data.child_id },
              { label: "revision", value: data.revision },
              { label: "quantity", value: data.quantity },
              { label: "scrap_factor", value: data.scrap_factor },
              { label: "yield_pct", value: data.yield_pct },
              { label: "sequence", value: data.sequence },
              { label: "is_alternate", value: data.is_alternate },
              { label: "alternate_group", value: data.alternate_group },
              { label: "is_optional", value: data.is_optional },
              { label: "cost_snapshot", value: data.cost_snapshot, isCurrency: true },
              { label: "dt_effective_from", value: data.dt_effective_from },
              { label: "dt_effective_to", value: data.dt_effective_to },
              { label: "change_reason", value: data.change_reason },
              { label: "description", value: data.description },
            ]}
            columns={3}
          />
          <BaseModelCards data={data as Record<string, unknown>} />
        </div>
      )}

      {/* Tab Navigation - only show when viewing/editing existing record */}
      {!loading && data?.id && (
        <>
          <DetailTabs
            entityType="bill_of_material"
            activeTab={activeTab}
            onTabChange={setActiveTab}
            standardTabs={[]}
            additionalTabs={tabs}
          />

          <div className="mt-4">
            {activeTab === "actions" && (
              <ActionsPanel
                entityType="bill_of_material"
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
                entityType="bill_of_material"
                entityId={data?.id}
              />
            )}

            {activeTab === "documents" && (
              <DocumentsPanel
                parent_model="bill_of_material"
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
