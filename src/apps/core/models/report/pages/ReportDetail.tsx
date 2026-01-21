import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input, DropDown } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createReport, updateReport } from "../services/reportApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { reportSchema } from "../utils/reportSchema";
import { ReportAddProps } from "../types/reportType";
import Checkbox from "../../../../../components/form/input/Checkbox";

export default function ReportDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ReportAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<z.infer<typeof reportSchema>>({
    resolver: zodResolver(reportSchema),
    defaultValues: { is_active: false },
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;
  useEffect(() => {
    if (mode === "add") {
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
  }, [data, reset, setValue, mode]);

  const onSubmit = async (formData: z.infer<typeof reportSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createReport(formData)
          : await updateReport({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Report ${
              mode === "add" ? "created" : "updated"
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
    }
  };

  const reportTypes = [
    { value: "sales", label: "Sales Report" },
    { value: "inventory", label: "Inventory Report" },
    { value: "financial", label: "Financial Report" },
    { value: "user", label: "User Report" },
  ];

  const handleTypeChange = (value: string) => {
    setValue("type", value);
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Report"
              : mode === "view"
              ? "View Report"
              : "Report Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Report"
                : mode === "view"
                ? "View Report"
                : "Add New Report"}
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Label htmlFor="title">title</Label>
              <Input
                type="text"
                id="title"
                placeholder="Report Title"
                {...register("title")}
                error={errors.title && errors.title.message ? true : false}
                hint={errors.title && errors.title.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Label htmlFor="type">type</Label>
              <DropDown
                id="type"
                options={reportTypes}
                placeholder="Select Report Type"
                value={watch("type")}
                onChange={handleTypeChange}
                className="dark:bg-dark-900"
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Label htmlFor="description">description</Label>
              <Input
                type="text"
                id="description"
                placeholder="Report Description"
                {...register("description")}
                error={
                  errors.description && errors.description.message ? true : false
                }
                hint={errors.description && errors.description.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Label htmlFor="parameters">parameters</Label>
              <Input
                type="text"
                id="parameters"
                placeholder="Report Parameters"
                {...register("parameters")}
                error={
                  errors.parameters && errors.parameters.message ? true : false
                }
                hint={errors.parameters && errors.parameters.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Checkbox
                id="is_active"
                checked={watch("is_active")}
                onChange={(checked) => setValue("is_active", checked)}
                label="is_active"
              />
            </div>
          </div>
          {mode !== "view" && (
            <div className="flex items-center gap-2">
              <button
                type="submit"
                className="flex items-center px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
              >
                {mode === "edit" ? "Update" : "Submit"}
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
    </>
  );
}