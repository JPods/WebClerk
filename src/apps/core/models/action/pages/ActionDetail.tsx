import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";
import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { createAction, updateAction } from "../services/actionApi";
import { PageRoutes } from "../../../../../routes/Routes";

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
  progress: z.number().min(0).max(100).optional(),
  dt_due: z.string().optional(),
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

export default function ActionDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ActionDetailProps) {
  const dispatch = useDispatch();
  const navigate = useNavigate();

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
  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;

  useEffect(() => {
    if (mode === "add") {
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
      setValue("progress", data.progress || 0);
      setValue("project_name", data.project_name || "");
      
      // Format dates for input fields
      if (data.dt_due) {
        const dueDate = new Date(data.dt_due);
        if (!isNaN(dueDate.getTime())) {
          setValue("dt_due", dueDate.toISOString().split('T')[0]);
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
  }, [data, reset, setValue, mode]);

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
      progress: formValues.progress || 0,
      dt_due: formValues.dt_due ? new Date(formValues.dt_due).toISOString() : null,
      dt_start: formValues.dt_start ? new Date(formValues.dt_start).toISOString() : null,
      dt_end: formValues.dt_end ? new Date(formValues.dt_end).toISOString() : null,
      project_name: formValues.project_name || "",
      languages: ["en", "ar", "bn"],
    };
  };

  const onSubmit = async (formData: z.infer<typeof actionSchema>) => {
    try {
      const payload = preparePayload(formData);
      const res =
        mode === "add"
          ? await createAction(payload)
          : await updateAction(data && data.id, payload);
      
      if (res) {
        dispatch(
          showToast({
            message: `Action ${mode === "add" ? "created" : "updated"} successfully`,
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
    }
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Action"
              : mode === "view"
              ? "View Action"
              : "Add New Action"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Action"
                : mode === "view"
                ? "View Action"
                : "Add New Action"}
            </h3>
            {onCancelInline && (
              <button
                type="button"
                onClick={onCancelInline}
                className="text-2xl text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                &times;
              </button>
            )}
          </div>
        )}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Action Translations */}
          <div className="space-y-4">
            <h4 className="text-md font-semibold dark:text-white border-b pb-2">Action Title</h4>
            <div>
              <Label htmlFor="action_en">Action (English) *</Label>
              <Input
                type="text"
                id="action_en"
                placeholder="Enter action in English"
                {...register("action_en")}
                error={errors.action_en && errors.action_en.message ? true : false}
                hint={errors.action_en && errors.action_en.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="action_ar">Action (Arabic)</Label>
              <Input
                type="text"
                id="action_ar"
                placeholder="أدخل الإجراء بالعربية"
                {...register("action_ar")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="action_bn">Action (Bengali)</Label>
              <Input
                type="text"
                id="action_bn"
                placeholder="বাংলায় কর্ম প্রবেশ করুন"
                {...register("action_bn")}
                disabled={mode === "view"}
              />
            </div>
          </div>

          {/* Description Translations */}
          <div className="space-y-4">
            <h4 className="text-md font-semibold dark:text-white border-b pb-2">Description</h4>
            <div>
              <Label htmlFor="description_en">Description (English)</Label>
              <textarea
                id="description_en"
                rows={3}
                placeholder="Enter description in English"
                {...register("description_en")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-50"
              />
            </div>
            <div>
              <Label htmlFor="description_ar">Description (Arabic)</Label>
              <textarea
                id="description_ar"
                rows={3}
                placeholder="أدخل الوصف بالعربية"
                {...register("description_ar")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-50"
              />
            </div>
            <div>
              <Label htmlFor="description_bn">Description (Bengali)</Label>
              <textarea
                id="description_bn"
                rows={3}
                placeholder="বাংলায় বিবরণ প্রবেশ করুন"
                {...register("description_bn")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-50"
              />
            </div>
          </div>

          {/* Action Details */}
          <div className="space-y-4">
            <h4 className="text-md font-semibold dark:text-white border-b pb-2">Details</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="project_name">Project Name</Label>
                <Input
                  type="text"
                  id="project_name"
                  placeholder="Enter project name"
                  {...register("project_name")}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="kanban_column">Kanban Column</Label>
                <Input
                  type="text"
                  id="kanban_column"
                  placeholder="Enter kanban column"
                  {...register("kanban_column")}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="status">Status</Label>
                <select
                  id="status"
                  {...register("status")}
                  disabled={mode === "view"}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-50"
                >
                  <option value="">Select status</option>
                  <option value="active">Active</option>
                  <option value="completed">Completed</option>
                  <option value="pending">Pending</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
              <div>
                <Label htmlFor="priority">Priority (1-4)</Label>
                <select
                  id="priority"
                  {...register("priority", { valueAsNumber: true })}
                  disabled={mode === "view"}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-50"
                >
                  <option value={1}>1 - Low</option>
                  <option value={2}>2 - Medium</option>
                  <option value={3}>3 - High</option>
                  <option value={4}>4 - Critical</option>
                </select>
              </div>
              <div>
                <Label htmlFor="difficulty">Difficulty (1-5)</Label>
                <Input
                  type="number"
                  id="difficulty"
                  min="1"
                  max="5"
                  placeholder="1-5"
                  {...register("difficulty", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="progress">Progress (%)</Label>
                <Input
                  type="number"
                  id="progress"
                  min="0"
                  max="100"
                  placeholder="0-100"
                  {...register("progress", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
            </div>
          </div>

          {/* Dates */}
          <div className="space-y-4">
            <h4 className="text-md font-semibold dark:text-white border-b pb-2">Dates</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label htmlFor="dt_start">Start Date</Label>
                <Input
                  type="date"
                  id="dt_start"
                  {...register("dt_start")}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="dt_due">Due Date</Label>
                <Input
                  type="date"
                  id="dt_due"
                  {...register("dt_due")}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="dt_end">End Date</Label>
                <Input
                  type="date"
                  id="dt_end"
                  {...register("dt_end")}
                  disabled={mode === "view"}
                />
              </div>
            </div>
          </div>

          {mode !== "view" && (
            <div className="flex items-center gap-2 pt-4 border-t">
              <button
                type="submit"
                className="flex items-center px-6 py-2.5 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900 transition-colors"
              >
                {mode === "edit" ? "Update Action" : "Create Action"}
              </button>
              {inline && onCancelInline && (
                <button
                  type="button"
                  onClick={onCancelInline}
                  className="flex items-center px-6 py-2.5 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 transition-colors"
                >
                  Cancel
                </button>
              )}
              {!inline && (
                <button
                  type="button"
                  onClick={() => navigate(PageRoutes.actionList)}
                  className="flex items-center px-6 py-2.5 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 transition-colors"
                >
                  Cancel
                </button>
              )}
            </div>
          )}
        </form>
      </ComponentCard>
    </>
  );
}
