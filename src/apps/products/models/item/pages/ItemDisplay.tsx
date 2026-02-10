/**
 * ItemDisplay - Follows 3-column standard with tab navigation
 * Tabs: Actions, Comments, Documents, History, Refs, Raw
 */
import { useEffect, useState, useMemo } from "react";
import { getRecord, saveRecord } from "@/api/wcapi";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import {
  Box,
  Link,
  AlignLeft,
  Activity,
  MessageSquare,
  FileIcon,
  History,
  Code,
  CheckSquare,
  Package,
  Tag,
  Ruler,
  Folder,
  DollarSign,
  TrendingUp,
  Archive,
  CheckCircle,
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
import JsonFieldEditor from "@/apps/transactions/components/JsonFieldEditor";

interface ItemDisplayProps {
  inline?: boolean;
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  onSaved?: () => void;
  onCancelInline?: () => void;
}

const STORAGE_KEY = "itemDisplay_columnCount";

export default function ItemDisplay({
  inline = false,
  modeProp,
  dataProp,
  onSaved,
  onCancelInline,
}: ItemDisplayProps) {
  const [data, setData] = useState<any>(dataProp || {});
  const [loading, setLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const dispatch = useDispatch();
  const initialMode: "add" | "edit" | "view" = modeProp || "view";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);

  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  // Tab navigation
  const { activeTab, setActiveTab } = useDetailTabs("item_display", "actions", [
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
          const rec = await getRecord('item', dataProp.id);
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
      await saveRecord('item', data);
      dispatch(showToast({ message: "Item saved successfully", type: "success" }));
      onSaved?.();
      if (currentMode === "add") {
        onCancelInline?.();
      } else {
        setCurrentMode("view");
      }
    } catch (error) {
      console.error("Failed to save", error);
      dispatch(showToast({ message: "Failed to save item", type: "error" }));
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

  // Helper for nested values
  const getNestedValue = (obj: any, path: string) => {
    return path.split('.').reduce((acc, part) => acc?.[part], obj);
  };

  const setNestedValue = (field: string, value: any) => {
    const parts = field.split('.');
    if (parts.length === 1) {
      setData({ ...data, [field]: value });
    } else {
      const newData = { ...data };
      let current = newData;
      for (let i = 0; i < parts.length - 1; i++) {
        current[parts[i]] = { ...current[parts[i]] };
        current = current[parts[i]];
      }
      current[parts[parts.length - 1]] = value;
      setData(newData);
    }
  };

  return (
    <>
      {/* Header */}
      <SimpleDetailHeader
        entityName="Item"
        recordId={data?.id}
        recordName={data?.name || data?.sku}
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
            <HorizontalField label="Name" htmlFor="name" icon={<Box size={14} />}>
              <Input
                type="text"
                id="name"
                placeholder="Item Name"
                value={data?.name || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("name", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="SKU" htmlFor="sku" icon={<Tag size={14} />}>
              <Input
                type="text"
                id="sku"
                placeholder="Stock Keeping Unit"
                value={data?.sku || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("sku", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Kind" htmlFor="kind" icon={<Package size={14} />}>
              <Input
                type="text"
                id="kind"
                placeholder="Item kind/type"
                value={data?.kind || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("kind", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="UOM" htmlFor="uom" icon={<Ruler size={14} />}>
              <Input
                type="text"
                id="uom"
                placeholder="Unit of Measure"
                value={data?.uom || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("uom", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Category" htmlFor="category" icon={<Folder size={14} />}>
              <Input
                type="text"
                id="category"
                placeholder="Item category"
                value={data?.category || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange("category", e.target.value)}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Active" htmlFor="is_active" icon={<CheckCircle size={14} />}>
              <Input
                type="text"
                id="is_active"
                value={data?.is_active ? "Yes" : "No"}
                disabled={true}
              />
            </HorizontalField>
            <HorizontalField label="Base Price" htmlFor="price_base" icon={<DollarSign size={14} />}>
              <Input
                type="number"
                id="price_base"
                placeholder="Base price"
                value={getNestedValue(data, 'price.base') ?? data?.price ?? ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                  const val = parseFloat(e.target.value) || 0;
                  if (typeof data?.price === 'object') {
                    setNestedValue('price.base', val);
                  } else {
                    handleFieldChange("price", val);
                  }
                }}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Avg Cost" htmlFor="cost_average" icon={<TrendingUp size={14} />}>
              <Input
                type="number"
                id="cost_average"
                value={getNestedValue(data, 'cost.average') ?? ""}
                disabled={true}
              />
            </HorizontalField>
            <HorizontalField label="On Hand" htmlFor="qty_on_hand" icon={<Archive size={14} />}>
              <Input
                type="number"
                id="qty_on_hand"
                value={getNestedValue(data, 'quantity.on_hand') ?? ""}
                disabled={true}
              />
            </HorizontalField>
            <HorizontalField label="Available" htmlFor="qty_available" icon={<Activity size={14} />}>
              <Input
                type="number"
                id="qty_available"
                value={getNestedValue(data, 'quantity.available') ?? ""}
                disabled={true}
              />
            </HorizontalField>
          </div>
          {/* Full-width fields */}
          <div className="mt-4 space-y-4">
            <HorizontalField label="Description" htmlFor="description" icon={<AlignLeft size={14} />}>
              <textarea
                id="description"
                placeholder="Item description"
                value={data?.description || ""}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleFieldChange("description", e.target.value)}
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
            entityType="item_display"
            activeTab={activeTab}
            onTabChange={setActiveTab}
            standardTabs={[]}
            additionalTabs={tabs}
          />

          {/* Tab Content */}
          <div className="mt-4">
            {activeTab === "actions" && (
              <ActionsPanel
                entityType="item"
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
                entityType="item"
                entityId={data?.id}
              />
            )}

            {activeTab === "documents" && (
              <DocumentsPanel
                parentType="item"
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
                entityType="item"
                entityId={data?.id}
                data={data?.refs}
                isEditing={currentMode !== "view"}
                onChange={(refs) => console.log("Refs updated:", refs)}
              />
            )}

            {activeTab === "raw" && (
              <JsonFieldEditor
                label="Full Item JSON"
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