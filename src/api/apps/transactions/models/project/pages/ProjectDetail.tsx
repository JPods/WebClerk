import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../../components/common/ComponentCard";
import Label from "../../../../../../components/form/Label";
import { Input } from "../../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import { createProject, updateProject } from "../services/projectApi";
import { showToast } from "../../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { projectSchema } from "../utils/projectSchema";
import { ProjectAddProps } from "../types/projectType";

export default function ProjectDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ProjectAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof projectSchema>>({
    resolver: zodResolver(projectSchema),
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

  const onSubmit = async (formData: z.infer<typeof projectSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createProject(formData)
          : await updateProject(data && data.id, formData);
      if (res) {
        dispatch(
          showToast({
            message: `Project ${
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

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Project"
              : mode === "view"
              ? "View Project"
              : "Project Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Project"
                : mode === "view"
                ? "View Project"
                : "Add New Project"}
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
          <div>
            <Label htmlFor="name">name</Label>
            <Input
              type="text"
              id="name"
              placeholder="Project Name"
              {...register("name")}
              error={errors.name && errors.name.message ? true : false}
              hint={errors.name && errors.name.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="description">description</Label>
            <Input
              type="text"
              id="description"
              placeholder="Description"
              {...register("description")}
              error={errors.description && errors.description.message ? true : false}
              hint={errors.description && errors.description.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="status">status</Label>
            <Input
              type="text"
              id="status"
              placeholder="Status"
              {...register("status")}
              error={errors.status && errors.status.message ? true : false}
              hint={errors.status && errors.status.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="start_date">start_date</Label>
            <Input
              type="date"
              id="start_date"
              placeholder="Start Date"
              {...register("start_date")}
              error={errors.start_date && errors.start_date.message ? true : false}
              hint={errors.start_date && errors.start_date.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="end_date">end_date</Label>
            <Input
              type="date"
              id="end_date"
              placeholder="End Date"
              {...register("end_date")}
              error={errors.end_date && errors.end_date.message ? true : false}
              hint={errors.end_date && errors.end_date.message}
              disabled={mode === "view"}
            />
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