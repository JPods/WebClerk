import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input, CustTextArea, DropDown } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createDomain, updateDomain } from "../services/domainApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { domainSchema } from "../utils/domainSchema";
import { DomainAddProps } from "../types/domainType";

export default function DomainDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: DomainAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<z.infer<typeof domainSchema>>({
    resolver: zodResolver(domainSchema),
    defaultValues: { status: "active" },
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

  const onSubmit = async (formData: z.infer<typeof domainSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createDomain(formData)
          : await updateDomain({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Domain ${
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

  const typeOptions = [
    { value: "website", label: "Website" },
    { value: "linkedin", label: "Linkedin" },
    { value: "facebook", label: "Facebook" },
    { value: "twitter", label: "Twitter" },
    { value: "github", label: "GitHub" },
    { value: "other", label: "Other" },
  ];

  const statusOptions = [
    { value: "active", label: "Active" },
    { value: "inactive", label: "Inactive" },
  ];

  const handleTypeChange = (value: string) => {
    setValue("type", value);
  };

  const handleStatusChange = (value: string) => {
    setValue("status", value);
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Domain"
              : mode === "view"
              ? "View Domain"
              : "Domain Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Domain"
                : mode === "view"
                ? "View Domain"
                : "Add New Domain"}
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
              <Label htmlFor="path">Path</Label>
              <Input
                type="text"
                id="path"
                placeholder="URL or handle"
                {...register("path")}
                error={errors.path && errors.path.message ? true : false}
                hint={errors.path && errors.path.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="type">Type</Label>
              <DropDown
                id="type"
                options={typeOptions}
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
              <Label htmlFor="status">Status</Label>
              <DropDown
                id="status"
                options={statusOptions}
                placeholder="Select Status"
                value={watch("status")}
                onChange={handleStatusChange}
                className="dark:bg-dark-900"
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="comment">Comments</Label>
              <CustTextArea
                id="comment"
                placeholder="General notes"
                {...register("comment")}
                error={errors.comment && errors.comment.message ? true : false}
                hint={errors.comment && errors.comment.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="refs">Refs</Label>
              <CustTextArea
                id="refs"
                placeholder="References"
                {...register("refs")}
                error={errors.refs && errors.refs.message ? true : false}
                hint={errors.refs && errors.refs.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="prefs">Prefs</Label>
              <CustTextArea
                id="prefs"
                placeholder="Preferences"
                {...register("prefs")}
                error={errors.prefs && errors.prefs.message ? true : false}
                hint={errors.prefs && errors.prefs.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="metadata">Metadata</Label>
              <CustTextArea
                id="metadata"
                placeholder="Metadata"
                {...register("metadata")}
                error={
                  errors.metadata && errors.metadata.message ? true : false
                }
                hint={errors.metadata && errors.metadata.message}
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