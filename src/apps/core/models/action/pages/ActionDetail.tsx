/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import ComponentCard from "../../../../../components/common/ComponentCard";
import { HorizontalField } from "../../../../../components/form/HorizontalField";
import { useColumnCount, ColumnSelector, getGridClassName } from "../../../../../components/form/useColumnCount";
import { Input } from "../../../../../components/wrapper";
import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { createAction, updateAction } from "../services/actionApi";
import { PageRoutes } from "../../../../../routes/Routes";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";
import { DetailTabs, useDetailTabs, TabConfig } from "../../../../../components/common/DetailTabs";
import CommentsPanel from "../../../../common/components/panels/CommentsPanel";
import DocumentsPanel from "../../../../common/components/panels/DocumentsPanel";
import QAPanel from "../../../../common/components/panels/QAPanel";
import ContactLinksPanel from "../../../../common/components/panels/ContactPanel";
import { ScalarCard, BaseModelCards } from "@/apps/common/components/detail";
import { FileText, Calendar, BarChart3, Target, Folder, Columns as ColumnsIcon, Clock, MessageSquare, FileIcon, HelpCircle, Users } from "lucide-react";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

const STORAGE_KEY = "actionDetail_columnCount";

// Action form schema
const actionSchema = z.object({
  action_en: z.string().min(1, "Action (English) is required"),
  action_ar: z.string().optional(),
  action_bn: z.string().optional(),
  description_en: z.string().optional(),
  description_ar: z.string().optional(),
  description_bn: z.string().optional(),
  kanban_column: z.string().optional(),
  priority: z.number().min(1).max(4).optional(),
  difficulty: z.number().min(1).max(5).optional(),
  status: z.string().optional(),
  percent_complete: z.number().min(0).max(100).optional(),
  dt_deadline: z.string().optional(),
  dt_start: z.string().optional(),
  dt_end: z.string().optional(),
  project_name: z.string().optional(),
});

interface ActionDetailProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

function ActionDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ActionDetailProps) {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 2);
  
  // Tab navigation
  const { activeTab, setActiveTab } = useDetailTabs("action", "comments", [
    "comments",
    "documents",
    "qa",
    "contacts",
  ]);
  
  // Additional tabs for Action entity
  const additionalTabs: TabConfig[] = [
    {
      id: "comments",
      label: "Comments",
      icon: <MessageSquare size={14} />,
    },
    {
      id: "documents",
      label: "Documents",
      icon: <FileIcon size={14} />,
    },
    {
      id: "qa",
      label: "QA",
      icon: <HelpCircle size={14} />,
    },
    {
      id: "contacts",
      label: "Contacts",
      icon: <Users size={14} />,
    },
  ];

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof actionSchema>>({
    resolver: zodResolver(actionSchema),
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  const [isSaving, setIsSaving] = useState(false);
  const data = dataProp || routeState.data || null;

  useEffect(() => {
    if (initialMode === "add") {
      reset();
    } else if (data) {
      // Populate form with existing data
      if (data.action) {
        setValue("action_en", data.action.en || "");
        setValue("action_ar", data.action.ar || "");
        setValue("action_bn", data.action.bn || "");
      }
      if (data.description) {
        setValue("description_en", data.description.en || "");
        setValue("description_ar", data.description.ar || "");
        setValue("description_bn", data.description.bn || "");
      }
      setValue("kanban_column", data.kanban_column || "");
      setValue("priority", data.priority || 1);
      setValue("difficulty", data.difficulty || 1);
      setValue("status", data.status || "");
      setValue("percent_complete", data.percent_complete || 0);
      setValue("project_name", data.project_name || "");
      
      // Format dates for input fields
      if (data.dt_deadline) {
        const dueDate = new Date(data.dt_deadline);
        if (!isNaN(dueDate.getTime())) {
          setValue("dt_deadline", dueDate.toISOString().split('T')[0]);
        }
      }
      if (data.dt_start) {
        const startDate = new Date(data.dt_start);
        if (!isNaN(startDate.getTime())) {
          setValue("dt_start", startDate.toISOString().split('T')[0]);
        }
      }
      if (data.dt_end) {
        const endDate = new Date(data.dt_end);
        if (!isNaN(endDate.getTime())) {
          setValue("dt_end", endDate.toISOString().split('T')[0]);
        }
      }
    } else {
      reset({});
    }
  }, [data, reset, setValue, initialMode]);

  const preparePayload = (formValues: z.infer<typeof actionSchema>): Record<string, unknown> => {
    return {
      action: {
        en: formValues.action_en,
        ar: formValues.action_ar || "",
        bn: formValues.action_bn || "",
      },
      description: {
        en: formValues.description_en || "",
        ar: formValues.description_ar || "",
        bn: formValues.description_bn || "",
      },
      kanban_column: formValues.kanban_column || "",
      priority: formValues.priority || 1,
      difficulty: formValues.difficulty || 1,
      status: formValues.status || "active",
      percent_complete: formValues.percent_complete || 0,
      dt_deadline: formValues.dt_deadline ? new Date(formValues.dt_deadline).toISOString() : null,
      dt_start: formValues.dt_start ? new Date(formValues.dt_start).toISOString() : null,
      dt_end: formValues.dt_end ? new Date(formValues.dt_end).toISOString() : null,
      project_name: formValues.project_name || "",
      languages: ["en", "ar", "bn"],
    };
  };

  const onSubmit = async (formData: z.infer<typeof actionSchema>) => {
    setIsSaving(true);
    try {
      const payload = preparePayload(formData);
      const actionId = data?.id ?? data?.pk ?? data?.uuid;
      if (currentMode === "edit" && (actionId === undefined || actionId === null)) {
        dispatch(
          showToast({
            message: "Action id is missing. Please reopen the action and try again.",
            type: "error",
          })
        );
        setIsSaving(false);
        return;
      }
      const res =
        currentMode === "add"
          ? await createAction(payload)
          : await updateAction(actionId, payload);
      
      if (res) {
        dispatch(
          showToast({
            message: `Action ${currentMode === "add" ? "created" : "updated"} successfully`,
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        }
        if (!inline) {
          navigate(PageRoutes.actionList);
        }
      }
    } catch (error: any) {
      dispatch(showToast({ message: error.message || "Failed to save action", type: "error" }));
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
        if (data.action) {
          setValue("action_en", data.action.en || "");
          setValue("action_ar", data.action.ar || "");
          setValue("action_bn", data.action.bn || "");
        }
        if (data.description) {
          setValue("description_en", data.description.en || "");
          setValue("description_ar", data.description.ar || "");
          setValue("description_bn", data.description.bn || "");
        }
        setValue("kanban_column", data.kanban_column || "");
        setValue("priority", data.priority || 1);
        setValue("difficulty", data.difficulty || 1);
        setValue("status", data.status || "");
        setValue("percent_complete", data.percent_complete || 0);
        setValue("project_name", data.project_name || "");
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
              ? "Edit Action"
              : currentMode === "view"
              ? "View Action"
              : "Add New Action"
          }
        />
      )}

      <SimpleDetailHeader
        entityName="Action"
        recordId={data?.id}
        recordName={data?.action?.en}
        mode={currentMode}
        backUrl={inline ? undefined : "/core/actions"}
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
        <div className="flex justify-end mb-4">
          <ColumnSelector columnCount={columnCount} setColumnCount={setColumnCount} />
        </div>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Action Title Section */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700 pb-2">
              Action Title
            </h4>
            <div className={getGridClassName(columnCount)}>
              <HorizontalField
                label="English"
                htmlFor="action_en"
                required
                icon={<FileText size={14} />}
                error={errors.action_en?.message}
              >
                <Input
                  type="text"
                  id="action_en"
                  placeholder="Enter action in English"
                  {...register("action_en")}
                  disabled={currentMode === "view"}
                />
              </HorizontalField>

              <HorizontalField
                label="Arabic"
                htmlFor="action_ar"
                icon={<FileText size={14} />}
              >
                <Input
                  type="text"
                  id="action_ar"
                  placeholder="أدخل الإجراء بالعربية"
                  {...register("action_ar")}
                  disabled={currentMode === "view"}
                />
              </HorizontalField>

              <HorizontalField
                label="Bengali"
                htmlFor="action_bn"
                icon={<FileText size={14} />}
              >
                <Input
                  type="text"
                  id="action_bn"
                  placeholder="বাংলায় কর্ম প্রবেশ করুন"
                  {...register("action_bn")}
                  disabled={currentMode === "view"}
                />
              </HorizontalField>
            </div>
          </div>

          {/* Description Section */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700 pb-2">
              Description
            </h4>
            <HorizontalField
              label="English"
              htmlFor="description_en"
              icon={<FileText size={14} />}
            >
              <textarea
                id="description_en"
                rows={2}
                placeholder="Enter description in English"
                {...register("description_en")}
                disabled={currentMode === "view"}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-50"
              />
            </HorizontalField>

            <HorizontalField
              label="Arabic"
              htmlFor="description_ar"
              icon={<FileText size={14} />}
            >
              <textarea
                id="description_ar"
                rows={2}
                placeholder="أدخل الوصف بالعربية"
                {...register("description_ar")}
                disabled={currentMode === "view"}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-50"
              />
            </HorizontalField>

            <HorizontalField
              label="Bengali"
              htmlFor="description_bn"
              icon={<FileText size={14} />}
            >
              <textarea
                id="description_bn"
                rows={2}
                placeholder="বাংলায় বিবরণ প্রবেশ করুন"
                {...register("description_bn")}
                disabled={currentMode === "view"}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-50"
              />
            </HorizontalField>
          </div>

          {/* Action Details Section */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700 pb-2">
              Details
            </h4>
            <div className={getGridClassName(columnCount)}>
              <HorizontalField
                label="Project"
                htmlFor="project_name"
                icon={<Folder size={14} />}
              >
                <Input
                  type="text"
                  id="project_name"
                  placeholder="Enter project name"
                  {...register("project_name")}
                  disabled={currentMode === "view"}
                />
              </HorizontalField>

              <HorizontalField
                label="Kanban"
                htmlFor="kanban_column"
                icon={<ColumnsIcon size={14} />}
              >
                <Input
                  type="text"
                  id="kanban_column"
                  placeholder="Enter kanban column"
                  {...register("kanban_column")}
                  disabled={currentMode === "view"}
                />
              </HorizontalField>

              <HorizontalField
                label="Status"
                htmlFor="status"
                icon={<Target size={14} />}
              >
                <select
                  id="status"
                  {...register("status")}
                  disabled={currentMode === "view"}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-50"
                >
                  <option value="">Select status</option>
                  <option value="active">Active</option>
                  <option value="completed">Completed</option>
                  <option value="pending">Pending</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </HorizontalField>

              <HorizontalField
                label="Priority"
                htmlFor="priority"
                icon={<BarChart3 size={14} />}
              >
                <select
                  id="priority"
                  {...register("priority", { valueAsNumber: true })}
                  disabled={currentMode === "view"}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-50"
                >
                  <option value={1}>1 - Low</option>
                  <option value={2}>2 - Medium</option>
                  <option value={3}>3 - High</option>
                  <option value={4}>4 - Critical</option>
                </select>
              </HorizontalField>

              <HorizontalField
                label="Difficulty"
                htmlFor="difficulty"
                icon={<BarChart3 size={14} />}
              >
                <Input
                  type="number"
                  id="difficulty"
                  min="1"
                  max="5"
                  placeholder="1-5"
                  {...register("difficulty", { valueAsNumber: true })}
                  disabled={currentMode === "view"}
                />
              </HorizontalField>

              <HorizontalField
                label="Progress"
                htmlFor="percent_complete"
                icon={<Target size={14} />}
              >
                <Input
                  type="number"
                  id="percent_complete"
                  min="0"
                  max="100"
                  placeholder="0-100%"
                  {...register("percent_complete", { valueAsNumber: true })}
                  disabled={currentMode === "view"}
                />
              </HorizontalField>
            </div>
          </div>

          {/* Dates Section */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700 pb-2">
              Dates
            </h4>
            <div className={getGridClassName(columnCount)}>
              <HorizontalField
                label="Start"
                htmlFor="dt_start"
                icon={<Calendar size={14} />}
              >
                <Input
                  type="date"
                  id="dt_start"
                  {...register("dt_start")}
                  disabled={currentMode === "view"}
                />
              </HorizontalField>

              <HorizontalField
                label="Deadline"
                htmlFor="dt_deadline"
                icon={<Calendar size={14} />}
              >
                <Input
                  type="date"
                  id="dt_deadline"
                  {...register("dt_deadline")}
                  disabled={currentMode === "view"}
                />
              </HorizontalField>

              <HorizontalField
                label="End"
                htmlFor="dt_end"
                icon={<Calendar size={14} />}
              >
                <Input
                  type="date"
                  id="dt_end"
                  {...register("dt_end")}
                  disabled={currentMode === "view"}
                />
              </HorizontalField>

              <HorizontalField
                label="Duration"
                htmlFor="duration"
                icon={<Clock size={14} />}
              >
                <div className="px-3 py-2 text-sm border border-gray-300 rounded-md bg-gray-50 dark:bg-gray-700 dark:border-gray-600 dark:text-white">
                  {data?.duration != null 
                    ? `${data.duration} day${data.duration !== 1 ? 's' : ''}`
                    : (data?.dt_start && data?.dt_deadline
                      ? (() => {
                          const start = new Date(data.dt_start);
                          const end = new Date(data.dt_deadline);
                          const days = Math.max(1, Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)));
                          return `${days} day${days !== 1 ? 's' : ''}`;
                        })()
                      : '—'
                    )
                  }
                </div>
              </HorizontalField>
            </div>
          </div>
        </form>
      </ComponentCard>

      {currentMode === "view" && data && (
        <div className="mt-4 space-y-0">
          <ScalarCard
            title="Action Fields"
            icon={<Target size={14} />}
            fields={[
              { label: "action", value: data.action },
              { label: "action_by", value: data.action_by },
              { label: "priority", value: data.priority },
              { label: "difficulty", value: data.difficulty },
              { label: "hours", value: data.hours },
              { label: "percent", value: data.percent },
              { label: "status", value: data.status },
              { label: "quality", value: data.quality },
              { label: "description", value: data.description },
              { label: "dt_action", value: data.dt_action },
              { label: "dt_completed", value: data.dt_completed },
              { label: "dt_deadline", value: data.dt_deadline },
              { label: "dt_updated", value: data.dt_updated },
            ]}
            columns={columnCount as 1 | 2 | 3}
          />
          <BaseModelCards data={data as Record<string, unknown>} />
        </div>
      )}

      {/* Tab Navigation */}
      <DetailTabs
        entityType="action"
        activeTab={activeTab}
        onTabChange={setActiveTab}
        standardTabs={[]}
        additionalTabs={additionalTabs}
      />

      {/* Tab Content */}
      <div className="mt-4">
        {activeTab === "comments" && (
          <CommentsPanel
            comments={data?.comments}
            isEditing={currentMode !== "view"}
            entityType="action"
            entityId={data?.id}
          />
        )}

        {activeTab === "documents" && (
          <DocumentsPanel
            parent_model="action"
            parentId={data?.id}
            data={data?.refs?.links?.document}
          />
        )}

        {activeTab === "qa" && (
          <QAPanel
            parent_model="action"
            parentId={data?.id}
          />
        )}

        {activeTab === "contacts" && (
          <ContactLinksPanel
            data={data?.refs?.links?.contact}
            entityType="action"
            entityId={data?.id}
          />
        )}
      </div>
    </>
  );
}

export default withDevIdentifier(ActionDetail, 'ActionDetail');
