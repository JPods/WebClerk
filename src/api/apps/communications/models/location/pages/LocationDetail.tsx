import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../../components/common/ComponentCard";
import Label from "../../../../../../components/form/Label";
import { Input } from "../../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import { createLocation, updateLocation } from "../services/locationApi";
import { showToast } from "../../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { locationSchema } from "../utils/locationSchema";
import { LocationAddProps } from "../types/locationType";

export default function LocationDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: LocationAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof locationSchema>>({
    resolver: zodResolver(locationSchema),
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
  console.log("errors", errors);
  const onSubmit = async (formData: z.infer<typeof locationSchema>) => {
    console.log("formData", formData);
    try {
      const res =
        mode === "add"
          ? await createLocation(formData)
          : await updateLocation({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Location ${
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
              ? "Edit Location"
              : mode === "view"
              ? "View Location"
              : "Location Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Location"
                : mode === "view"
                ? "View Location"
                : "Add New Location"}
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
          <div className="grid grid-cols-1 md:grid-cols-1 gap-4">
            <div>
              <Label htmlFor="address1">address1</Label>
              <Input
                type="text"
                id="address1"
                placeholder="Location address1"
                {...register("address1")}
                error={
                  errors.address1 && errors.address1.message ? true : false
                }
                hint={errors.address1 && errors.address1.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="address2">address22</Label>
              <Input
                type="text"
                id="address2"
                placeholder="Address2"
                {...register("address2")}
                error={
                  errors.address2 && errors.address2.message ? true : false
                }
                hint={errors.address2 && errors.address2.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="address_type">address_type</Label>
              <Input
                type="text"
                id="address_type"
                placeholder="Address Type"
                {...register("address_type")}
                error={
                  errors.address_type && errors.address_type.message
                    ? true
                    : false
                }
                hint={errors.address_type && errors.address_type.message}
                disabled={mode === "view"}
              />
            </div>

            <div>
              <Label htmlFor="full">full</Label>
              <Input
                type="text"
                id="full"
                placeholder="Full"
                {...register("full")}
                error={errors.full && errors.full.message ? true : false}
                hint={errors.full && errors.full.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="city">city</Label>
              <Input
                type="text"
                id="city"
                placeholder="City"
                {...register("city")}
                error={errors.city && errors.city.message ? true : false}
                hint={errors.city && errors.city.message}
                disabled={mode === "view"}
              />
            </div>

            <div>
              <Label htmlFor="country">country</Label>
              <Input
                type="text"
                id="country"
                placeholder="Country"
                {...register("country")}
                error={errors.country && errors.country.message ? true : false}
                hint={errors.country && errors.country.message}
                disabled={mode === "view"}
              />
            </div>

            <div>
              <Label htmlFor="state">state</Label>
              <Input
                type="text"
                id="state"
                placeholder="State"
                {...register("state")}
                error={errors.state && errors.state.message ? true : false}
                hint={errors.state && errors.state.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="zip">zip</Label>
              <Input
                type="text"
                id="zip"
                placeholder="ZIP Code"
                {...register("zip")}
                error={errors.zip && errors.zip.message ? true : false}
                hint={errors.zip && errors.zip.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="latitude">latitude</Label>
              <Input
                type="text"
                id="latitude"
                placeholder="Latitude"
                {...register("latitude")}
                error={
                  errors.latitude && errors.latitude.message ? true : false
                }
                hint={errors.latitude && errors.latitude.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="longitude">longitude</Label>
              <Input
                type="text"
                id="longitude"
                placeholder="Longitude"
                {...register("longitude")}
                error={
                  errors.longitude && errors.longitude.message ? true : false
                }
                hint={errors.longitude && errors.longitude.message}
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
