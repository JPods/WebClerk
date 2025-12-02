import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../components/common/ComponentCard";
import Label from "../../../../components/form/Label";
import { Input } from "../../../../components/wrapper";

import PageBreadcrumb from "../../../../components/common/PageBreadCrumb";
import { createBundle, updateBundle } from "../services/bundleApi";
import { showToast } from "../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { bundleSchema } from "../utils/bundleSchema";
import { BundleAddProps } from "../types/bundleType";

export default function BundleDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: BundleAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof bundleSchema>>({
    resolver: zodResolver(bundleSchema),
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

  const onSubmit = async (formData: z.infer<typeof bundleSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createBundle(formData)
          : await updateBundle({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Bundle ${
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
              ? "Edit Bundle"
              : mode === "view"
              ? "View Bundle"
              : "Bundle Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Bundle"
                : mode === "view"
                ? "View Bundle"
                : "Add New Bundle"}
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
              <Label htmlFor="name">Name</Label>
              <Input
                type="text"
                id="name"
                placeholder="Bundle Name"
                {...register("name")}
                error={errors.name && errors.name.message ? true : false}
                hint={errors.name && errors.name.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="version">Version</Label>
              <Input
                type="text"
                id="version"
                placeholder="Version"
                {...register("version")}
                error={errors.version && errors.version.message ? true : false}
                hint={errors.version && errors.version.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div>
            <Label htmlFor="description">Description</Label>
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
            <Label htmlFor="data">Data (JSON)</Label>
            <Input
              type="text"
              id="data"
              placeholder="Data"
              {...register("data")}
              error={errors.data && errors.data.message ? true : false}
              hint={errors.data && errors.data.message}
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