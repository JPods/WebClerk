import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Type, List, Server, Hash, User, Lock, Database } from "lucide-react";

import ComponentCard from "../../../../../components/common/ComponentCard";
import HorizontalField from "../../../../../components/form/HorizontalField";
import { useColumnCount, ColumnSelector, getGridClassName } from "../../../../../components/form/useColumnCount";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";
import { createConnection, updateConnection } from "../services/connectionApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { connectionSchema } from "../utils/connectionSchema";
import { ConnectionAddProps } from "../types/connectionType";

const STORAGE_KEY = "connectionDetail_columnCount";

export default function ConnectionDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ConnectionAddProps) {
  const dispatch = useDispatch();
  const navigate = useNavigate();

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
  const data = dataProp || routeState.data || null;
  const [isSaving, setIsSaving] = useState(false);
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  useEffect(() => {
    if (currentMode === "add") {
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
  }, [data, reset, setValue, currentMode]);

  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  const onSubmit = async (formData: z.infer<typeof connectionSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createConnection(formData)
          : await updateConnection({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Connection ${
              currentMode === "add" ? "created" : "updated"
            } successfully`,
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        }
        if (currentMode === "add") {
          navigate(-1);
        } else {
          setCurrentMode("view");
        }
      }
    } catch (error: any) {
      dispatch(showToast({ message: error.message, type: "error" }));
    } finally {
      setIsSaving(false);
    }
  };

  const handleEdit = () => {
    setCurrentMode("edit");
  };

  const handleCancel = () => {
    if (inline && onCancelInline) {
      onCancelInline();
    } else if (initialMode === "add") {
      navigate(-1);
    } else {
      if (data) {
        Object.keys(data).forEach((key: any) => {
          if (data[key] !== undefined) {
            setValue(key, data[key]);
          }
        });
      }
      setCurrentMode("view");
    }
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            currentMode === "edit"
              ? "Edit Connection"
              : currentMode === "view"
              ? "View Connection"
              : "Connection Detail"
          }
        />
      )}

      {!inline && (
        <SimpleDetailHeader
          entityName="Connection"
          recordId={data?.id}
          recordName={data?.name}
          mode={currentMode}
          backUrl="/sync/connections"
        />
      )}

      {!inline && (
        <SimpleDetailToolbar
          mode={currentMode}
          isSaving={isSaving}
          onSave={handleSubmit(onSubmit)}
          onCancel={handleCancel}
          onEdit={handleEdit}
        />
      )}

      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {currentMode === "edit"
                ? "Edit Connection"
                : currentMode === "view"
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
          <div className="flex justify-end mb-4">
            <ColumnSelector value={columnCount} onChange={setColumnCount} />
          </div>
          <div className={getGridClassName(columnCount)}>
            <HorizontalField label="Name" htmlFor="name" error={errors.name?.message} icon={Type}>
              <Input
                type="text"
                id="name"
                placeholder="Connection Name"
                {...register("name")}
                error={errors.name && errors.name.message ? true : false}
                hint={errors.name && errors.name.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Type" htmlFor="type" error={errors.type?.message} icon={List}>
              <Input
                type="text"
                id="type"
                placeholder="Connection Type"
                {...register("type")}
                error={errors.type && errors.type.message ? true : false}
                hint={errors.type && errors.type.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Host" htmlFor="host" error={errors.host?.message} icon={Server}>
              <Input
                type="text"
                id="host"
                placeholder="Host"
                {...register("host")}
                error={errors.host && errors.host.message ? true : false}
                hint={errors.host && errors.host.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Port" htmlFor="port" error={errors.port?.message} icon={Hash}>
              <Input
                type="number"
                id="port"
                placeholder="Port"
                {...register("port", { valueAsNumber: true })}
                error={errors.port && errors.port.message ? true : false}
                hint={errors.port && errors.port.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Username" htmlFor="username" error={errors.username?.message} icon={User}>
              <Input
                type="text"
                id="username"
                placeholder="Username"
                {...register("username")}
                error={errors.username && errors.username.message ? true : false}
                hint={errors.username && errors.username.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Password" htmlFor="password" error={errors.password?.message} icon={Lock}>
              <Input
                type="password"
                id="password"
                placeholder="Password"
                {...register("password")}
                error={errors.password && errors.password.message ? true : false}
                hint={errors.password && errors.password.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Database" htmlFor="database" error={errors.database?.message} icon={Database}>
              <Input
                type="text"
                id="database"
                placeholder="Database"
                {...register("database")}
                error={errors.database && errors.database.message ? true : false}
                hint={errors.database && errors.database.message}
                disabled={currentMode === "view"
              />
            </HorizontalField>
          </div>
          {currentMode !== "view" && inline && (
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4 flex items-center gap-2">
              <button
                type="submit"
                className="flex items-center px-4 py-2 text-white bg-brand-500 rounded-md hover:bg-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
              >
                {currentMode === "edit" ? "Update" : "Submit"}
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