import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input, DropDown } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createPhone, updatePhone } from "../services/phoneApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { phoneSchema } from "../utils/phoneSchema";
import { PhoneAddProps } from "../types/phoneType";
import Checkbox from "../../../../../components/form/input/Checkbox";

export default function PhoneDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: PhoneAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
    control,
    watch,
  } = useForm<z.infer<typeof phoneSchema>>({
    resolver: zodResolver(phoneSchema),
    defaultValues: { opt_out: false },
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

  const onSubmit = async (formData: z.infer<typeof phoneSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createPhone(formData)
          : await updatePhone({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Phone ${
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

  // const typeOptions = [
  //   { value: "mobile", label: "Mobile" },
  //   { value: "home", label: "Home" },
  //   { value: "work", label: "Work" },
  //   { value: "fax", label: "Fax" },
  //   { value: "other", label: "Other" },
  // ];

  // const countryCodeOptions = [
  //   { value: "+1", label: "+1 (USA)" },
  //   { value: "+44", label: "+44 (UK)" },
  //   { value: "+91", label: "+91 (India)" },
  //   { value: "+86", label: "+86 (China)" },
  //   { value: "+81", label: "+81 (Japan)" },
  // ];

  const handleTypeChange = (value: string) => {
    setValue("type", value);
  };

  const handleCountryCodeChange = (value: string) => {
    setValue("country_code", value);
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Phone"
              : mode === "view"
              ? "View Phone"
              : "Phone Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Phone"
                : mode === "view"
                ? "View Phone"
                : "Add New Phone"}
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
              <Label htmlFor="number">number</Label>
              <Input
                type="text"
                id="number"
                placeholder="Phone Number"
                {...register("number")}
                error={errors.number && errors.number.message ? true : false}
                hint={errors.number && errors.number.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="country_code">country_code</Label>
              <Input
                type="text"
                id="country_code"
                placeholder="country_code"
                {...register("country_code")}
                error={
                  errors.country_code && errors.country_code.message
                    ? true
                    : false
                }
                hint={errors.country_code && errors.country_code.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="format">format</Label>
              <Input
                type="text"
                id="format"
                placeholder="Format"
                {...register("format")}
                error={errors.format && errors.format.message ? true : false}
                hint={errors.format && errors.format.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="name">name</Label>
              <Input
                type="text"
                id="name"
                placeholder="Name"
                {...register("name")}
                error={errors.name && errors.name.message ? true : false}
                hint={errors.name && errors.name.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-1 gap-2">
            <div>
              <Label htmlFor="attention">attention</Label>
              <Input
                type="text"
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
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Controller
                name="opt_out"
                control={control}
                render={({ field }) => (
                  <Checkbox
                    id="opt_out"
                    checked={field.value ?? false}
                    onChange={field.onChange}
                    label="Opt Out"
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
