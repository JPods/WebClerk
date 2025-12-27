import { useEffect } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useForm, Controller } from "react-hook-form";
import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import {
  Input,
  CustTextArea,
  DropDown,
} from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createEmail, updateEmail } from "../services/emailApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { emailSchema } from "../utils/emailSchema";
import { EmailAddProps } from "../types/emailType";
import Checkbox from "../../../../../components/form/input/Checkbox";
export default function EmailDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: EmailAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
    control,
    watch,
  } = useForm<z.infer<typeof emailSchema>>({
    resolver: zodResolver(emailSchema),
    defaultValues: { is_primary: false, is_verified: false },
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

  const onSubmit = async (formData: z.infer<typeof emailSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createEmail({ ...formData, id: "" })
          : await updateEmail({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Email ${
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

  const statusOptions = [
    { value: "", label: "Active" },
    { value: "opted_out", label: "Opted Out" },
    { value: "bounced", label: "Bounced" },
    { value: "invalid", label: "Invalid" },
    { value: "spam_complaint", label: "Spam Complaint" },
  ];

  const handleStatusChange = (value: string) => {
    setValue(
      "opt_out",
      value as
        | "bounced"
        | "opted_out"
        | "invalid"
        | "spam_complaint"
        | undefined
    );
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Email"
              : mode === "view"
              ? "View Email"
              : "Email Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Email"
                : mode === "view"
                ? "View Email"
                : "Add New Email"}
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
              <Label htmlFor="email">email</Label>
              <Input
                type="email"
                id="email"
                placeholder="Email Address"
                {...register("email")}
                error={errors.email && errors.email.message ? true : false}
                hint={errors.email && errors.email.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="name">name</Label>
              <Input
                type="name"
                id="name"
                placeholder="Name"
                {...register("name")}
                error={errors.name && errors.name.message ? true : false}
                hint={errors.name && errors.name.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="attention">attention</Label>
              <Input
                type="attention"
                id="attention"
                placeholder="Attention"
                {...register("attention")}
                error={
                  errors.attention && errors.attention.message ? true : false
                }
                hint={errors.attention && errors.attention.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="opt_out">opt_out</Label>
              <DropDown
                id="opt_out"
                options={statusOptions}
                placeholder="Select Status"
                value={watch("opt_out")}
                onChange={handleStatusChange}
                className="dark:bg-dark-900"
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Controller
                name="is_primary"
                control={control}
                render={({ field }) => (
                  <Checkbox
                    id="is_primary"
                    checked={field.value ?? false}
                    onChange={field.onChange}
                    label="Is Primary"
                  />
                )}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Controller
                name="is_verified"
                control={control}
                render={({ field }) => (
                  <Checkbox
                    id="is_verified"
                    checked={field.value ?? false}
                    onChange={field.onChange}
                    label="Is Verified"
                  />
                )}
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
