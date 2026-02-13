/**
 * DocumentDetail - Follows 3-column standard with tab navigation
 * Tabs: Actions, Comments, Documents, History, Raw
 */
import { useEffect, useState, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
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
  Hash,
  Clock,
  ListOrdered,
  Eye,
  File,
  Lock,
  HardDrive,
} from "lucide-react";

import ComponentCard from "../../../../../components/common/ComponentCard";
import HorizontalField from "../../../../../components/form/HorizontalField";
import {
  useColumnCount,
  ColumnSelector,
  getGridClassName,
} from "../../../../../components/form/useColumnCount";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";
import {
  DetailTabs,
  useDetailTabs,
  TabConfig,
} from "../../../../../components/common/DetailTabs";

// Panels
import CommentsPanel from "../../../../common/components/panels/CommentsPanel";
import DocumentsPanel from "../../../../common/components/panels/DocumentsPanel";
import ActionsPanel from "../../../../common/components/panels/ActionsPanel";
import RefsPanel from "../../../../common/components/panels/RefsPanel";
import JsonFieldEditor from "@/apps/common/components/JsonFieldEditor";

import { createDocument, updateDocument, fetchDocumentById } from "../services/documentApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate, useParams } from "react-router";
import { documentSchema } from "../utils/documentSchema";
import { DocumentAddProps } from "../types/documentType";

const STORAGE_KEY = "documentDetail_columnCount";

export default function DocumentDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: DocumentAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof documentSchema>>({
    resolver: zodResolver(documentSchema),
  });

  const location = useLocation();
  const navigate = useNavigate();
  const { id } = useParams<{ id?: string }>();
  const routeState = (location.state as any) || {};
  
  // Document data - from props, route state, or fetched via API
  const [data, setData] = useState<any>(dataProp || routeState.data || null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);

  // Fetch document by ID if navigating from list (wcapi/get/?model_name=document&id=X)
  useEffect(() => {
    const loadDocument = async () => {
      if (id && !dataProp && !routeState.data) {
        setIsLoading(true);
        try {
          const res = await fetchDocumentById(id);
          if (res.status === 200) {
            // API returns { data: { results: [...] } } envelope - get first result
            const items = res.data?.data?.results || res.data?.results || res.data?.items || [];
            const doc = Array.isArray(items) ? items[0] : items;
            if (doc) {
              setData(doc);
              // Set initial mode to view if not explicitly set
              if (!routeState.mode) {
                setCurrentMode("view");
              }
            } else {
              dispatch(showToast({ message: "Document not found", type: "error" }));
            }
          } else {
            dispatch(showToast({ message: "Failed to load document", type: "error" }));
          }
        } catch (error) {
          console.error("Failed to fetch document:", error);
          dispatch(showToast({ message: "Failed to load document", type: "error" }));
        } finally {
          setIsLoading(false);
        }
      }
    };
    loadDocument();
  }, [id, dataProp, routeState.data, routeState.mode, dispatch]);

  // Tab navigation - Actions, Comments, Documents, History, Refs, Raw
  const { activeTab, setActiveTab } = useDetailTabs("document", "actions", [
    "actions",
    "comments",
    "documents",
    "history",
    "refs",
    "raw",
  ]);

  // Tab configuration
  const tabs: TabConfig[] = useMemo(
    () => [
      {
        id: "actions",
        label: "Actions",
        icon: <CheckSquare size={14} />,
        badge: data?.actions?.items?.filter(
          (a: any) => a.status === "pending"
        )?.length,
      },
      {
        id: "comments",
        label: "Comments",
        icon: <MessageSquare size={14} />,
        badge: data?.comments?.length,
      },
      {
        id: "documents",
        label: "Documents",
        icon: <FileIcon size={14} />,
        badge: data?.refs?.links?.document?.length,
      },
      {
        id: "history",
        label: "History",
        icon: <History size={14} />,
      },
      {
        id: "refs",
        label: "Refs",
        icon: <Link size={14} />,
        badge: data?.refs?.links ? Object.keys(data.refs.links).length : undefined,
      },
      {
        id: "raw",
        label: "Raw",
        icon: <Code size={14} />,
      },
    ],
    [data]
  );

  useEffect(() => {
    if (currentMode === "add") {
      reset();
    } else if (data) {
      Object.keys(data).forEach((key: any) => {
        if (data[key] !== undefined) {
          setValue(key, data[key]);
        }
      });
    } else {
      reset({});
    }
  }, [data, reset, setValue, currentMode]);

  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  const onSubmit = async (formData: z.infer<typeof documentSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createDocument(formData)
          : await updateDocument({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Document ${
              currentMode === "add" ? "created" : "updated"
            } successfully`,
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        }
        if (currentMode === "add") {
          navigate(-1);
        } else {
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
              ? "Edit Document"
              : currentMode === "view"
              ? "View Document"
              : "Document Detail"
          }
        />
      )}

      {/* Header - shown for both inline and standalone */}
      {inline && (
        <SimpleDetailHeader
          entityName="Document"
          recordId={data?.id}
          recordName={data?.name}
          mode={currentMode}
          backUrl=""
          showBackButton={false}
        />
      )}

      {!inline && (
        <SimpleDetailHeader
          entityName="Document"
          recordId={data?.id}
          recordName={data?.name}
          mode={currentMode}
          backUrl="/docs/document/list"
        />
      )}

      {/* Toolbar - shown for both inline and standalone */}
      <SimpleDetailToolbar
        mode={currentMode}
        isSaving={isSaving}
        onSave={handleSubmit(onSubmit)}
        onCancel={inline ? onCancelInline || handleCancel : handleCancel}
        onEdit={handleEdit}
      />

      {/* Loading state */}
      {isLoading && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500"></div>
          <span className="ml-3 text-slate-600 dark:text-slate-400">Loading document...</span>
        </div>
      )}

      {/* Basic Information Panel */}
      {!isLoading && (
      <ComponentCard>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="flex justify-end mb-4">
            <ColumnSelector value={columnCount} onChange={setColumnCount} />
          </div>
          <div className={getGridClassName(columnCount)}>
            <HorizontalField label="Name" htmlFor="name" error={errors.name?.message} icon={<FileText size={14} />}>
              <Input
                type="text"
                id="name"
                placeholder="Document Name"
                {...register("name")}
                error={errors.name && errors.name.message ? true : false}
                hint={errors.name && errors.name.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Slug" htmlFor="slug" error={errors.slug?.message} icon={<Link size={14} />}>
              <Input
                type="text"
                id="slug"
                placeholder="URL-friendly identifier"
                {...register("slug")}
                error={errors.slug && errors.slug.message ? true : false}
                hint={errors.slug && errors.slug.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Status" htmlFor="status" error={errors.status?.message} icon={<Activity size={14} />}>
              <Input
                type="text"
                id="status"
                placeholder="Document Status"
                {...register("status")}
                error={errors.status && errors.status.message ? true : false}
                hint={errors.status && errors.status.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Model Name" htmlFor="model_name" icon={<Database size={14} />}>
              <Input
                type="text"
                id="model_name"
                placeholder="Source model type"
                {...register("model_name")}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Confidential" htmlFor="confidential" icon={<Shield size={14} />}>
              <Input
                type="text"
                id="confidential"
                placeholder="Confidentiality level"
                {...register("confidential")}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="MIME Type" htmlFor="mime_type" icon={<File size={14} />}>
              <Input
                type="text"
                id="mime_type"
                placeholder="e.g. application/pdf"
                {...register("mime_type")}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Checksum" htmlFor="checksum" icon={<Lock size={14} />}>
              <Input
                type="text"
                id="checksum"
                placeholder="File checksum"
                {...register("checksum")}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Size (bytes)" htmlFor="size_bytes" icon={<HardDrive size={14} />}>
              <Input
                type="number"
                id="size_bytes"
                placeholder="File size"
                {...register("size_bytes", { valueAsNumber: true })}
                disabled={true}
              />
            </HorizontalField>
            <HorizontalField label="Retention (days)" htmlFor="retention_period" icon={<Clock size={14} />}>
              <Input
                type="number"
                id="retention_period"
                placeholder="Retention period"
                {...register("retention_period", { valueAsNumber: true })}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Sequence" htmlFor="sequence" icon={<ListOrdered size={14} />}>
              <Input
                type="number"
                id="sequence"
                placeholder="Display order"
                {...register("sequence", { valueAsNumber: true })}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Access Count" htmlFor="count_accessed" icon={<Eye size={14} />}>
              <Input
                type="number"
                id="count_accessed"
                {...register("count_accessed", { valueAsNumber: true })}
                disabled={true}
              />
            </HorizontalField>
          </div>
          <div>
            <HorizontalField label="Description" htmlFor="description" icon={<AlignLeft size={14} />}>
              <Input
                type="text"
                id="description"
                placeholder="Short description"
                {...register("description")}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
          </div>
          <div>
            <HorizontalField label="Body" htmlFor="body" icon={<FileCode size={14} />}>
              <textarea
                id="body"
                placeholder="Document body/content"
                {...register("body")}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                rows={6}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
          </div>
          <div>
            <HorizontalField label="Comment" htmlFor="comment" icon={<MessageSquare size={14} />}>
              <textarea
                id="comment"
                placeholder="General notes"
                {...register("comment")}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                rows={3}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
          </div>
        </form>
      </ComponentCard>
      )}

      {/* Data Payload Panel */}
      {!isLoading && (
        <ComponentCard>
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <Database size={16} /> Document Data
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

      {/* Path & Copyright Panel */}
      {!isLoading && (data?.path || data?.copyright) && (
        <ComponentCard>
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <File size={16} /> Path & Copyright
          </h3>
          <div className="space-y-4">
            {data?.path && (
              <JsonFieldEditor
                label="Path"
                value={data.path}
                readonly={currentMode === "view"}
                maxHeight="200px"
                onChange={(newPath) => setData({ ...data, path: newPath })}
              />
            )}
            {data?.copyright && (
              <JsonFieldEditor
                label="Copyright"
                value={data.copyright}
                readonly={currentMode === "view"}
                maxHeight="200px"
                onChange={(newCopyright) => setData({ ...data, copyright: newCopyright })}
              />
            )}
          </div>
        </ComponentCard>
      )}

      {/* Tab Navigation - only show when viewing/editing existing record */}
      {!isLoading && data?.id && (
        <>
          <DetailTabs
            entityType="document"
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
                parent_model="document"
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
                        <History
                          size={16}
                          className="text-slate-400 mt-0.5"
                        />
                        <div className="flex-1 text-sm">
                          <div className="text-slate-900 dark:text-white">
                            {entry.action || entry.description || "Change"}
                          </div>
                          <div className="text-slate-500 text-xs">
                            {entry.timestamp
                              ? new Date(entry.timestamp).toLocaleString()
                              : entry.dt_created
                              ? new Date(
                                  entry.dt_created * 1000
                                ).toLocaleString()
                              : "--"}
                            {entry.user && ` by ${entry.user}`}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-500 text-sm">
                    No history available
                  </p>
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