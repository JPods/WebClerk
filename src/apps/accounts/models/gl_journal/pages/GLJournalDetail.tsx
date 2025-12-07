import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input, DropDown } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createGLJournal, updateGLJournal } from "../services/glJournalApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { glJournalSchema } from "../utils/glJournalSchema";
import { GLJournalAddProps } from "../types/glJournalType";

export default function GLJournalDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: GLJournalAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<z.infer<typeof glJournalSchema>>({
    resolver: zodResolver(glJournalSchema),
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

  const onSubmit = async (formData: z.infer<typeof glJournalSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createGLJournal(formData)
          : await updateGLJournal({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `GL Journal ${
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

  const journalTypes = [
    { value: "debit", label: "Debit" },
    { value: "credit", label: "Credit" },
    { value: "adjustment", label: "Adjustment" },
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
              ? "Edit GL Journal"
              : mode === "view"
              ? "View GL Journal"
              : "GL Journal Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit GL Journal"
                : mode === "view"
                ? "View GL Journal"
                : "Add New GL Journal"}
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
              <Label htmlFor="date">date</Label>
              <Input
                type="date"
                id="date"
                placeholder="Date"
                {...register("date")}
                error={errors.date && errors.date.message ? true : false}
                hint={errors.date && errors.date.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="type">type</Label>
              <DropDown
                id="type"
                options={journalTypes}
                placeholder="Select Type"
                value={watch("type")}
                onChange={handleTypeChange}
                className="dark:bg-dark-900"
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="amount">amount</Label>
              <Input
                type="number"
                id="amount"
                placeholder="Amount"
                {...register("amount", { valueAsNumber: true })}
                error={errors.amount && errors.amount.message ? true : false}
                hint={errors.amount && errors.amount.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4">
            <div>
              <Label htmlFor="description">description</Label>
              <Input
                type="text"
                id="description"
                placeholder="Description"
                {...register("description")}
                error={
                  errors.description && errors.description.message ? true : false
                }
                hint={errors.description && errors.description.message}
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