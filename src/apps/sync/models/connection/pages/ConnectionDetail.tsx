import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createConnection, updateConnection } from "../services/connectionApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { connectionSchema } from "../utils/connectionSchema";
import { ConnectionAddProps } from "../types/connectionType";

export default function ConnectionDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ConnectionAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof connectionSchema>>({
    resolver: zodResolver(connectionSchema),
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

  const onSubmit = async (formData: z.infer<typeof connectionSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createConnection(formData)
          : await updateConnection({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Connection ${
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
              ? "Edit Connection"
              : mode === "view"
              ? "View Connection"
              : "Connection Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Connection"
                : mode === "view"
                ? "View Connection"
                : "Add New Connection"}
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
                placeholder="Connection Name"
                {...register("name")}
                error={errors.name && errors.name.message ? true : false}
                hint={errors.name && errors.name.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="type">Type</Label>
              <Input
                type="text"
                id="type"
                placeholder="Connection Type"
                {...register("type")}
                error={errors.type && errors.type.message ? true : false}
                hint={errors.type && errors.type.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="host">Host</Label>
              <Input
                type="text"
                id="host"
                placeholder="Host"
                {...register("host")}
                error={errors.host && errors.host.message ? true : false}
                hint={errors.host && errors.host.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="port">Port</Label>
              <Input
                type="number"
                id="port"
                placeholder="Port"
                {...register("port", { valueAsNumber: true })}
                error={errors.port && errors.port.message ? true : false}
                hint={errors.port && errors.port.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="username">Username</Label>
              <Input
                type="text"
                id="username"
                placeholder="Username"
                {...register("username")}
                error={errors.username && errors.username.message ? true : false}
                hint={errors.username && errors.username.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input
                type="password"
                id="password"
                placeholder="Password"
                {...register("password")}
                error={errors.password && errors.password.message ? true : false}
                hint={errors.password && errors.password.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div>
            <Label htmlFor="database">Database</Label>
            <Input
              type="text"
              id="database"
              placeholder="Database"
              {...register("database")}
              error={errors.database && errors.database.message ? true : false}
              hint={errors.database && errors.database.message}
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