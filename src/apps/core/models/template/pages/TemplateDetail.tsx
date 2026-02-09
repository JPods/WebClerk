import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Target, Type, Database } from "lucide-react";

import ComponentCard from "../../../../../components/common/ComponentCard";
import HorizontalField from "../../../../../components/form/HorizontalField";
import { useColumnCount, ColumnSelector, getGridClassName } from "../../../../../components/form/useColumnCount";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createTemplate, updateTemplate } from "../services/templateApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { templateSchema } from "../utils/templateSchema";
import { TemplateAddProps } from "../types/templateType";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";

const STORAGE_KEY = "templateDetail_columnCount";

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
  const navigate = useNavigate();
  const routeState = (location.state as any) || {};
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  const [isSaving, setIsSaving] = useState(false);
  const data = dataProp || routeState.data || null;
  useEffect(() => {
    if (initialMode === "add") {
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
  }, [data, reset, setValue, initialMode]);

  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  const onSubmit = async (formData: z.infer<typeof templateSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
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
              ? "Edit Template"
              : currentMode === "view"
              ? "View Template"
              : "Template Detail"
          }
        />
      )}

      {!inline && (
        <SimpleDetailHeader
          entityName="Template"
          recordId={data?.id}
          recordName={data?.name}
          mode={currentMode}
          backUrl="/core/templates"
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
                ? "Edit Template"
                : currentMode === "view"
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
          <div className="flex justify-end mb-4">
            <ColumnSelector value={columnCount} onChange={setColumnCount} />
          </div>
          <div className={getGridClassName(columnCount)}>
            <HorizontalField label="Purpose" htmlFor="purpose" error={errors.purpose?.message} icon={Target}>
              <Input
                type="text"
                id="purpose"
                placeholder="Purpose"
                {...register("purpose")}
                error={errors.purpose && errors.purpose.message ? true : false}
                hint={errors.purpose && typeof errors.purpose.message === 'string' ? errors.purpose.message : undefined}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Name" htmlFor="name" error={errors.name?.message} icon={Type}>
              <Input
                type="text"
                id="name"
                placeholder="Name"
                {...register("name")}
                error={errors.name && errors.name.message ? true : false}
                hint={errors.name && typeof errors.name.message === 'string' ? errors.name.message : undefined}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Data" htmlFor="data" error={errors.data?.message} icon={Database}>
              <Input
                type="text"
                id="data"
                placeholder="Data"
                {...register("data")}
                error={errors.data && errors.data.message ? true : false}
                hint={errors.data && typeof errors.data.message === 'string' ? errors.data.message : undefined}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
          </div>
          {currentMode !== "view" && (
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
    </>
  );
}