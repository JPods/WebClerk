import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input, CustTextArea, DropDown } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createEmail, updateEmail } from "../services/emailApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { emailSchema } from "../utils/emailSchema";
import { EmailAddProps } from "../types/emailType";

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
    watch,
  } = useForm<z.infer<typeof emailSchema>>({
    resolver: zodResolver(emailSchema),
    defaultValues: { status: "draft" },
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
          ? await createEmail(formData)
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
    { value: "draft", label: "Draft" },
    { value: "sent", label: "Sent" },
    { value: "failed", label: "Failed" },
  ];

  const handleStatusChange = (value: string) => {
    setValue("status", value as "draft" | "sent" | "failed");
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
              <Label htmlFor="subject">subject</Label>
              <Input
                type="text"
                id="subject"
                placeholder="Email Subject"
                {...register("subject")}
                error={errors.subject && errors.subject.message ? true : false}
                hint={errors.subject && errors.subject.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="status">status</Label>
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
              <Label htmlFor="from_email">from_email</Label>
              <Input
                type="email"
                id="from_email"
                placeholder="From Email"
                {...register("from_email")}
                error={
                  errors.from_email && errors.from_email.message ? true : false
                }
                hint={errors.from_email && errors.from_email.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="to_email">to_email</Label>
              <Input
                type="email"
                id="to_email"
                placeholder="To Email"
                {...register("to_email")}
                error={errors.to_email && errors.to_email.message ? true : false}
                hint={errors.to_email && errors.to_email.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4">
            <div>
              <Label htmlFor="body">body</Label>
              <CustTextArea
                id="body"
                placeholder="Email Body"
                {...register("body")}
                error={errors.body && errors.body.message ? true : false}
                hint={errors.body && errors.body.message}
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