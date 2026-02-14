import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Type, Activity, AlignLeft, Calendar, CalendarCheck, CheckSquare, MessageSquare, FileIcon, History, Link, Code, FileText, SlidersHorizontal } from "lucide-react";

import ComponentCard from "../../../../../components/common/ComponentCard";
import HorizontalField from "../../../../../components/form/HorizontalField";
import { useColumnCount, ColumnSelector, getGridClassName } from "../../../../../components/form/useColumnCount";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";
import { createCampaign, updateCampaign } from "../services/campaignApi";

// Tab navigation
import { DetailTabs, useDetailTabs, TabConfig } from "@/components/common/DetailTabs";

// Panels
import { ActionsPanel, CommentsPanel, DocumentsPanel, MetadataPanel, PrefsPanel, RefsPanel } from "@/apps/common/components/panels";
import JsonFieldEditor from "@/apps/common/components/JsonFieldEditor";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { campaignSchema } from "../utils/campaignSchema";
import { CampaignAddProps } from "../types/campaignType";

const STORAGE_KEY = "campaignDetail_columnCount";

export default function CampaignDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: CampaignAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof campaignSchema>>({
    resolver: zodResolver(campaignSchema),
  });

  const location = useLocation();
  const navigate = useNavigate();
  const routeState = (location.state as any) || {};
  const data = dataProp || routeState.data || null;
  const [isSaving, setIsSaving] = useState(false);
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);

  // Full record data for panels
  const [recordData, setRecordData] = useState<any>(data || {});

  // Tab navigation
  const { activeTab, setActiveTab } = useDetailTabs("campaign_detail", "actions", [
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

  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  const onSubmit = async (formData: z.infer<typeof campaignSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createCampaign(formData)
          : await updateCampaign({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Campaign ${
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
              ? "Edit Campaign"
              : currentMode === "view"
              ? "View Campaign"
              : "Campaign Detail"
          }
        />
      )}

      {!inline && (
        <SimpleDetailHeader
          entityName="Campaign"
          recordId={data?.id}
          recordName={data?.name}
          mode={currentMode}
          backUrl="/support/campaigns"
        />
      )}

      {!inline && (
        <SimpleDetailToolbar
          mode={currentMode}
          isSaving={isSaving}
          onSave={handleSubmit(onSubmit)}
          onCancel={handleCancel}
          onEdit={handleEdit}
        />
      )}

      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {currentMode === "edit"
                ? "Edit Campaign"
                : currentMode === "view"
                ? "View Campaign"
                : "Add New Campaign"}
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
          <div className="flex justify-end mb-4">
            <ColumnSelector value={columnCount} onChange={setColumnCount} />
          </div>
          <div className={getGridClassName(columnCount)}>
            <HorizontalField label="Name" htmlFor="name" error={errors.name?.message} icon={Type}>
              <Input
                type="text"
                id="name"
                placeholder="Campaign Name"
                {...register("name")}
                error={errors.name && errors.name.message ? true : false}
                hint={errors.name && errors.name.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Status" htmlFor="status" error={errors.status?.message} icon={Activity}>
              <Input
                type="text"
                id="status"
                placeholder="Status"
                {...register("status")}
                error={errors.status && errors.status.message ? true : false}
                hint={errors.status && errors.status.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Description" htmlFor="description" error={errors.description?.message} icon={AlignLeft}>
              <Input
                type="text"
                id="description"
                placeholder="Description"
                {...register("description")}
                error={errors.description && errors.description.message ? true : false}
                hint={errors.description && errors.description.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Start Date" htmlFor="start_date" error={errors.start_date?.message} icon={Calendar}>
              <Input
                type="date"
                id="start_date"
                placeholder="Start Date"
                {...register("start_date")}
                error={errors.start_date && errors.start_date.message ? true : false}
                hint={errors.start_date && errors.start_date.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="End Date" htmlFor="end_date" error={errors.end_date?.message} icon={CalendarCheck}>
              <Input
                type="date"
                id="end_date"
                placeholder="End Date"
                {...register("end_date")}
                error={errors.end_date && errors.end_date.message ? true : false}
                hint={errors.end_date && errors.end_date.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
          </div>
          {inline && currentMode !== "view" && (
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4 flex items-center gap-2">
              <button
                type="submit"
                className="flex items-center px-4 py-2 text-white bg-brand-500 rounded-md hover:bg-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
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
            entityType="campaign_detail"
            activeTab={activeTab}
            onTabChange={setActiveTab}
            standardTabs={[]}
            additionalTabs={tabs}
          />
          <div className="mt-4">
            {activeTab === "actions" && (
              <ActionsPanel entityType="campaign" entityId={recordData.id} data={recordData?.actions?.items} actionIds={recordData?.actions?.ids} isEditing={currentMode !== "view"} onChange={(actions: any) => setRecordData({ ...recordData, actions: { ...recordData.actions, items: actions } })} />
            )}
            {activeTab === "comments" && (
              <CommentsPanel comments={recordData?.comments} isEditing={currentMode !== "view"} entityType="campaign" entityId={recordData.id} onChange={(comments: any) => setRecordData({ ...recordData, comments })} />
            )}
            {activeTab === "documents" && (
              <DocumentsPanel parent_model="campaign" parentId={recordData.id} data={recordData?.refs?.links?.document} isEditing={currentMode !== "view"} onChange={(docs: any) => setRecordData({ ...recordData, refs: { ...recordData.refs, links: { ...recordData.refs?.links, document: docs } } })} />
            )}
            {activeTab === "history" && (
              <MetadataPanel entityType="campaign" entityId={recordData.id} data={recordData?.metadata} />
            )}
            {activeTab === "metadata" && (
              <MetadataPanel entityType="campaign" entityId={recordData.id} data={recordData?.metadata} />
            )}
            {activeTab === "prefs" && (
              <PrefsPanel entityType="campaign" entityId={recordData.id} data={recordData?.prefs} />
            )}
            {activeTab === "raw" && (
              <JsonFieldEditor label="Full Campaign JSON" value={recordData} readonly defaultExpanded maxHeight="600px" />
            )}
            {activeTab === "refs" && (
              <RefsPanel entityType="campaign" entityId={recordData.id} data={recordData?.refs} isEditing={currentMode !== "view"} onChange={(refs: any) => setRecordData({ ...recordData, refs })} />
            )}
          </div>
        </>
      )}
    </>
  );
}