import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createUsage, updateUsage } from "../services/usageApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { usageSchema } from "../utils/usageSchema";
import { UsageAddProps } from "../types/usageType";

export default function UsageDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: UsageAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof usageSchema>>({
    resolver: zodResolver(usageSchema),
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

  const onSubmit = async (formData: z.infer<typeof usageSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createUsage(formData)
          : await updateUsage({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Usage ${
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
              ? "Edit Usage"
              : mode === "view"
              ? "View Usage"
              : "Usage Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Usage"
                : mode === "view"
                ? "View Usage"
                : "Add New Usage"}
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
              <Label htmlFor="item_id">Item ID</Label>
              <Input
                type="text"
                id="item_id"
                placeholder="Item ID"
                {...register("item_id")}
                error={errors.item_id && errors.item_id.message ? true : false}
                hint={errors.item_id && errors.item_id.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="user_id">User ID</Label>
              <Input
                type="text"
                id="user_id"
                placeholder="User ID"
                {...register("user_id")}
                error={errors.user_id && errors.user_id.message ? true : false}
                hint={errors.user_id && errors.user_id.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="quantity_used">Quantity Used</Label>
              <Input
                type="number"
                id="quantity_used"
                placeholder="Quantity Used"
                {...register("quantity_used", { valueAsNumber: true })}
                error={errors.quantity_used && errors.quantity_used.message ? true : false}
                hint={errors.quantity_used && errors.quantity_used.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="date_used">Date Used</Label>
              <Input
                type="date"
                id="date_used"
                placeholder="Date Used"
                {...register("date_used")}
                error={errors.date_used && errors.date_used.message ? true : false}
                hint={errors.date_used && errors.date_used.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div>
            <Label htmlFor="notes">Notes</Label>
            <Input
              type="text"
              id="notes"
              placeholder="Notes"
              {...register("notes")}
              error={errors.notes && errors.notes.message ? true : false}
              hint={errors.notes && errors.notes.message}
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