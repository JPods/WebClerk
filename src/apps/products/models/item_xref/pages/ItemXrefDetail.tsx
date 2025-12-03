import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createItemXref, updateItemXref } from "../services/itemXrefApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { itemXrefSchema } from "../utils/itemXrefSchema";
import { ItemXrefAddProps } from "../types/itemXrefType";

export default function ItemXrefDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ItemXrefAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof itemXrefSchema>>({
    resolver: zodResolver(itemXrefSchema),
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

  const onSubmit = async (formData: z.infer<typeof itemXrefSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createItemXref(formData)
          : await updateItemXref({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Item xref ${
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
              ? "Edit Item Xref"
              : mode === "view"
              ? "View Item Xref"
              : "Item Xref Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Item Xref"
                : mode === "view"
                ? "View Item Xref"
                : "Add New Item Xref"}
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
              <Label htmlFor="item_id_1">Item ID 1</Label>
              <Input
                type="text"
                id="item_id_1"
                placeholder="Item ID 1"
                {...register("item_id_1")}
                error={errors.item_id_1 && errors.item_id_1.message ? true : false}
                hint={errors.item_id_1 && errors.item_id_1.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="item_id_2">Item ID 2</Label>
              <Input
                type="text"
                id="item_id_2"
                placeholder="Item ID 2"
                {...register("item_id_2")}
                error={errors.item_id_2 && errors.item_id_2.message ? true : false}
                hint={errors.item_id_2 && errors.item_id_2.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div>
            <Label htmlFor="relationship_type">Relationship Type</Label>
            <Input
              type="text"
              id="relationship_type"
              placeholder="Relationship Type"
              {...register("relationship_type")}
              error={errors.relationship_type && errors.relationship_type.message ? true : false}
              hint={errors.relationship_type && errors.relationship_type.message}
              disabled={mode === "view"}
            />
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