import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import { HorizontalField } from "../../../../../components/form/HorizontalField";
import { useColumnCount, ColumnSelector, getGridClassName } from "../../../../../components/form/useColumnCount";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";
import { createUsage, updateUsage } from "../services/usageApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { usageSchema } from "../utils/usageSchema";
import { UsageAddProps } from "../types/usageType";
import { Package, User, Hash, Calendar, FileText } from "lucide-react";

const STORAGE_KEY = "usageDetail_columnCount";

export default function UsageDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: UsageAddProps) {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);
  const [isSaving, setIsSaving] = useState(false);

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;
  
  // Mode state for switching between view/edit
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof usageSchema>>({
    resolver: zodResolver(usageSchema),
  });

  useEffect(() => {
    if (currentMode === "add") {
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
  }, [data, reset, setValue, currentMode]);

  const onSubmit = async (formData: z.infer<typeof usageSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createUsage(formData)
          : await updateUsage({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Usage ${
              currentMode === "add" ? "created" : "updated"
            } successfully`,
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        } else {
          // Switch to view mode after save
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
      // Reset form and go back to view mode
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
              ? "Edit Usage"
              : currentMode === "view"
              ? "View Usage"
              : "Usage Detail"
          }
        />
      )}
      
      {/* Header with entity name, ID, and mode indicator */}
      {!inline && (
        <SimpleDetailHeader
          entityName="Usage"
          recordId={data?.id}
          recordName={data?.item_id}
          mode={currentMode}
          backUrl="/products/usages"
        />
      )}

      {/* Toolbar with action buttons */}
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
                ? "Edit Usage"
                : currentMode === "view"
                ? "View Usage"
                : "Add New Usage"}
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
              label="Item ID"
              htmlFor="item_id"
              required
              icon={<Package size={14} />}
              error={errors.item_id?.message}
            >
              <Input
                type="text"
                id="item_id"
                placeholder="Item ID"
                {...register("item_id")}
                disabled={currentMode === "view"}
              />
            </HorizontalField>

            <HorizontalField
              label="User ID"
              htmlFor="user_id"
              icon={<User size={14} />}
              error={errors.user_id?.message}
            >
              <Input
                type="text"
                id="user_id"
                placeholder="User ID"
                {...register("user_id")}
                disabled={currentMode === "view"}
              />
            </HorizontalField>

            <HorizontalField
              label="Quantity"
              htmlFor="quantity_used"
              icon={<Hash size={14} />}
              error={errors.quantity_used?.message}
            >
              <Input
                type="number"
                id="quantity_used"
                placeholder="Quantity Used"
                {...register("quantity_used", { valueAsNumber: true })}
                disabled={currentMode === "view"}
              />
            </HorizontalField>

            <HorizontalField
              label="Date Used"
              htmlFor="date_used"
              icon={<Calendar size={14} />}
              error={errors.date_used?.message}
            >
              <Input
                type="date"
                id="date_used"
                placeholder="Date Used"
                {...register("date_used")}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
          </div>

          <HorizontalField
            label="Notes"
            htmlFor="notes"
            icon={<FileText size={14} />}
            error={errors.notes?.message}
          >
            <Input
              type="text"
              id="notes"
              placeholder="Notes"
              {...register("notes")}
              disabled={currentMode === "view"}
            />
          </HorizontalField>

          {/* Inline mode buttons */}
          {inline && currentMode !== "view" && (
            <div className="flex items-center gap-2 pt-4 border-t border-slate-200 dark:border-slate-700">
              <button
                type="submit"
                className="flex items-center px-4 py-2 text-white bg-brand-500 rounded-md hover:bg-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
              >
                {currentMode === "edit" ? "Update" : "Submit"}
              </button>
              {onCancelInline && (
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