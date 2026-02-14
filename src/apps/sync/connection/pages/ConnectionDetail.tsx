import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CheckSquare, MessageSquare, FileIcon, History, Link, Code, FileText, SlidersHorizontal } from "lucide-react";

import ComponentCard from "../../../../components/common/ComponentCard";
import SimpleDetailHeader from "../../../../components/common/SimpleDetailHeader";
import SimpleDetailToolbar from "../../../../components/common/SimpleDetailToolbar";
import Label from "../../../../components/form/Label";
import { Input } from "../../../../components/wrapper";

import PageBreadcrumb from "../../../../components/common/PageBreadCrumb";
import { createConnection, updateConnection } from "../services/connectionApi";
import { showToast } from "../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { connectionSchema } from "../utils/connectionSchema";
import { ConnectionAddProps } from "../types/connectionType";

// Tab navigation
import { DetailTabs, useDetailTabs, TabConfig } from "@/components/common/DetailTabs";

// Panels
import { ActionsPanel, CommentsPanel, DocumentsPanel, MetadataPanel, PrefsPanel, RefsPanel } from "@/apps/common/components/panels";
import JsonFieldEditor from "@/apps/common/components/JsonFieldEditor";

export default function ConnectionDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ConnectionAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof connectionSchema>>({
    resolver: zodResolver(connectionSchema),
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;

  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  const [isSaving, setIsSaving] = useState(false);

  // Full record data for panels
  const [recordData, setRecordData] = useState<any>(data || {});

  // Tab navigation
  const { activeTab, setActiveTab } = useDetailTabs("connection_legacy_detail", "actions", [
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
    setCurrentMode("view");
    if (data) {
      Object.keys(data).forEach((key: any) => {
        if (data[key] !== undefined) {
          setValue(key, data[key]);
        }
      });
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

  const onSubmit = async (formData: z.infer<typeof connectionSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createConnection(formData)
          : await updateConnection({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Connection ${
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
              ? "Edit Connection"
              : currentMode === "view"
              ? "View Connection"
              : "Connection Detail"
          }
        />
      )}
      <SimpleDetailHeader
        entityName="Connection"
        id={data?.id}
        mode={currentMode}
      />
      <SimpleDetailToolbar
        mode={currentMode}
        isSaving={isSaving}
        onEdit={handleEdit}
        onCancel={handleCancel}
        onSave={handleSubmit(onSubmit)}
      />
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {currentMode === "edit"
                ? "Edit Connection"
                : currentMode === "view"
                ? "View Connection"
                : "Add New Connection"}
            </h3>
            {onCancelInline && (
              <button
                type="button"
                onClick={onCancelInline}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                &times;
              </button>
            )}
          </div>
        )}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="name">name</Label>
              <Input
                type="text"
                id="name"
                placeholder="Connection Name"
                {...register("name")}
                error={errors.name && errors.name.message ? true : false}
                hint={errors.name && errors.name.message}
                disabled={currentMode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="type">type</Label>
              <Input
                type="text"
                id="type"
                placeholder="Connection Type"
                {...register("type")}
                error={errors.type && errors.type.message ? true : false}
                hint={errors.type && errors.type.message}
                disabled={currentMode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="host">host</Label>
              <Input
                type="text"
                id="host"
                placeholder="Host"
                {...register("host")}
                error={errors.host && errors.host.message ? true : false}
                hint={errors.host && errors.host.message}
                disabled={currentMode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="port">port</Label>
              <Input
                type="number"
                id="port"
                placeholder="Port"
                {...register("port", { valueAsNumber: true })}
                error={errors.port && errors.port.message ? true : false}
                hint={errors.port && errors.port.message}
                disabled={currentMode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="username">username</Label>
              <Input
                type="text"
                id="username"
                placeholder="Username"
                {...register("username")}
                error={errors.username && errors.username.message ? true : false}
                hint={errors.username && errors.username.message}
                disabled={currentMode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="password">password</Label>
              <Input
                type="password"
                id="password"
                placeholder="Password"
                {...register("password")}
                error={errors.password && errors.password.message ? true : false}
                hint={errors.password && errors.password.message}
                disabled={currentMode === "view"}
              />
            </div>
          </div>
          <div>
            <Label htmlFor="database">database</Label>
            <Input
              type="text"
              id="database"
              placeholder="Database"
              {...register("database")}
              error={errors.database && errors.database.message ? true : false}
              hint={errors.database && errors.database.message}
              disabled={currentMode === "view"}
            />
          </div>
          {currentMode !== "view" && (
            <div className="flex items-center gap-2">
              <button
                type="submit"
                className="flex items-center px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
              >
                {currentMode === "edit" ? "Update" : "Submit"}
              </button>
              {inline && onCancelInline && (
                <button
                  type="button"
                  onClick={onCancelInline}
                  className="flex items-center px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
                >
                  Cancel
                </button>
              )}
            </div>
          )}
        </form>
      </ComponentCard>

      {/* Tab Navigation */}
      {recordData?.id && (
        <>
          <DetailTabs
            entityType="connection_legacy_detail"
            activeTab={activeTab}
            onTabChange={setActiveTab}
            standardTabs={[]}
            additionalTabs={tabs}
          />
          <div className="mt-4">
            {activeTab === "actions" && (
              <ActionsPanel entityType="connection" entityId={recordData.id} data={recordData?.actions?.items} actionIds={recordData?.actions?.ids} isEditing={currentMode !== "view"} onChange={(actions: any) => setRecordData({ ...recordData, actions: { ...recordData.actions, items: actions } })} />
            )}
            {activeTab === "comments" && (
              <CommentsPanel comments={recordData?.comments} isEditing={currentMode !== "view"} entityType="connection" entityId={recordData.id} onChange={(comments: any) => setRecordData({ ...recordData, comments })} />
            )}
            {activeTab === "documents" && (
              <DocumentsPanel parent_model="connection" parentId={recordData.id} data={recordData?.refs?.links?.document} isEditing={currentMode !== "view"} onChange={(docs: any) => setRecordData({ ...recordData, refs: { ...recordData.refs, links: { ...recordData.refs?.links, document: docs } } })} />
            )}
            {activeTab === "history" && (
              <MetadataPanel entityType="connection" entityId={recordData.id} data={recordData?.metadata} />
            )}
            {activeTab === "metadata" && (
              <MetadataPanel entityType="connection" entityId={recordData.id} data={recordData?.metadata} />
            )}
            {activeTab === "prefs" && (
              <PrefsPanel entityType="connection" entityId={recordData.id} data={recordData?.prefs} />
            )}
            {activeTab === "raw" && (
              <JsonFieldEditor label="Full Connection JSON" value={recordData} readonly defaultExpanded maxHeight="600px" />
            )}
            {activeTab === "refs" && (
              <RefsPanel entityType="connection" entityId={recordData.id} data={recordData?.refs} isEditing={currentMode !== "view"} onChange={(refs: any) => setRecordData({ ...recordData, refs })} />
            )}
          </div>
        </>
      )}
    </>
  );
}