import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createVendor, updateVendor } from "../services/vendorApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { vendorSchema } from "../utils/vendorSchema";
import { VendorAddProps } from "../types/vendorType";

export default function VendorDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: VendorAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof vendorSchema>>({
    resolver: zodResolver(vendorSchema),
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

  const onSubmit = async (formData: z.infer<typeof vendorSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createVendor(formData)
          : await updateVendor({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Vendor ${
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
              ? "Edit Vendor"
              : mode === "view"
              ? "View Vendor"
              : "Vendor Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Vendor"
                : mode === "view"
                ? "View Vendor"
                : "Add New Vendor"}
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
              <Label htmlFor="name">Name</Label>
              <Input
                type="text"
                id="name"
                placeholder="Vendor Name"
                {...register("name")}
                error={errors.name && errors.name.message ? true : false}
                hint={errors.name && errors.name.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="vendor_number">Vendor Number</Label>
              <Input
                type="text"
                id="vendor_number"
                placeholder="Vendor Number"
                {...register("vendor_number")}
                error={errors.vendor_number && errors.vendor_number.message ? true : false}
                hint={errors.vendor_number && errors.vendor_number.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div>
            <Label htmlFor="address">Address</Label>
            <Input
              type="text"
              id="address"
              placeholder="Vendor Address"
              {...register("address")}
              error={errors.address && errors.address.message ? true : false}
              hint={errors.address && errors.address.message}
              disabled={mode === "view"}
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="phone">Phone</Label>
              <Input
                type="text"
                id="phone"
                placeholder="Phone Number"
                {...register("phone")}
                error={errors.phone && errors.phone.message ? true : false}
                hint={errors.phone && errors.phone.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="email">Email</Label>
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
          </div>
          <div>
            <Label htmlFor="website">Website</Label>
            <Input
              type="url"
              id="website"
              placeholder="Website URL"
              {...register("website")}
              error={errors.website && errors.website.message ? true : false}
              hint={errors.website && errors.website.message}
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