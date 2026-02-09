import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import { HorizontalField } from "../../../../../components/form/HorizontalField";
import { useColumnCount, ColumnSelector, getGridClassName } from "../../../../../components/form/useColumnCount";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createSpecification, updateSpecification } from "../services/specificationApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { specificationSchema } from "../utils/specificationSchema";
import { SpecificationAddProps } from "../types/specificationType";
import { FileSpreadsheet, GitBranch, FileText, ListChecks } from "lucide-react";

const STORAGE_KEY = "specificationDetail_columnCount";

export default function SpecificationDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: SpecificationAddProps) {
  const dispatch = useDispatch();
  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof specificationSchema>>({
    resolver: zodResolver(specificationSchema),
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

  const onSubmit = async (formData: z.infer<typeof specificationSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createSpecification(formData)
          : await updateSpecification({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Specification ${
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
              ? "Edit Specification"
              : mode === "view"
              ? "View Specification"
              : "Specification Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Specification"
                : mode === "view"
                ? "View Specification"
                : "Add New Specification"}
            </h3>
            <div className="flex items-center gap-3">
              <ColumnSelector columnCount={columnCount} setColumnCount={setColumnCount} />
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
          </div>
        )}
        {!inline && (
          <div className="flex justify-end mb-4">
            <ColumnSelector columnCount={columnCount} setColumnCount={setColumnCount} />
          </div>
        )}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className={getGridClassName(columnCount)}>
            <HorizontalField
              label="Name"
              htmlFor="name"
              required
              icon={<FileSpreadsheet size={14} />}
              error={errors.name?.message}
            >
              <Input
                type="text"
                id="name"
                placeholder="Specification Name"
                {...register("name")}
                disabled={mode === "view"}
              />
            </HorizontalField>

            <HorizontalField
              label="Version"
              htmlFor="version"
              icon={<GitBranch size={14} />}
              error={errors.version?.message}
            >
              <Input
                type="text"
                id="version"
                placeholder="Version"
                {...register("version")}
                disabled={mode === "view"}
              />
            </HorizontalField>

            <HorizontalField
              label="Requirements"
              htmlFor="requirements"
              icon={<ListChecks size={14} />}
              error={errors.requirements?.message}
            >
              <Input
                type="text"
                id="requirements"
                placeholder="Requirements"
                {...register("requirements")}
                disabled={mode === "view"}
              />
            </HorizontalField>
          </div>

          <HorizontalField
            label="Description"
            htmlFor="description"
            icon={<FileText size={14} />}
            error={errors.description?.message}
          >
            <Input
              type="text"
              id="description"
              placeholder="Description"
              {...register("description")}
              disabled={mode === "view"}
            />
          </HorizontalField>

          {mode !== "view" && (
            <div className="flex items-center gap-2 pt-4 border-t border-slate-200 dark:border-slate-700">
              <button
                type="submit"
                className="flex items-center px-4 py-2 text-white bg-brand-500 rounded-md hover:bg-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
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