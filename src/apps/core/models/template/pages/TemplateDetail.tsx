import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createTemplate, updateTemplate } from "../services/templateApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { templateSchema } from "../utils/templateSchema";
import { TemplateAddProps } from "../types/templateType";

export default function TemplateDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: TemplateAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof templateSchema>>({
    resolver: zodResolver(templateSchema),
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

  const onSubmit = async (formData: z.infer<typeof templateSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createTemplate(formData)
          : await updateTemplate({
              id: data.id,
              purpose: formData.purpose,
              name: formData.name,
              data: formData.data,
            });
      if (res) {
        dispatch(
          showToast({
            message: `Template ${
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
              ? "Edit Template"
              : mode === "view"
              ? "View Template"
              : "Template Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Template"
                : mode === "view"
                ? "View Template"
                : "Add New Template"}
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
              <Label htmlFor="purpose">purpose</Label>
              <Input
                type="text"
                id="purpose"
                placeholder="Purpose"
                {...register("purpose")}
                error={errors.purpose && errors.purpose.message ? true : false}
                hint={errors.purpose && typeof errors.purpose.message === 'string' ? errors.purpose.message : undefined}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="name">name</Label>
              <Input
                type="text"
                id="name"
                placeholder="Name"
                {...register("name")}
                error={errors.name && errors.name.message ? true : false}
                hint={errors.name && typeof errors.name.message === 'string' ? errors.name.message : undefined}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4">
            <div>
              <Label htmlFor="data">data</Label>
              <Input
                type="text"
                id="data"
                placeholder="Data"
                {...register("data")}
                error={errors.data && errors.data.message ? true : false}
                hint={errors.data && typeof errors.data.message === 'string' ? errors.data.message : undefined}
                disabled={mode === "view"}
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