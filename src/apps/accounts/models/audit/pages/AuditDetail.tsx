import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input, CustTextArea } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";
import { createAudit, updateAudit } from "../services/auditApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { auditSchema } from "../utils/auditSchema";
import { AuditAddProps } from "../types/auditType";

export default function AuditDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: AuditAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof auditSchema>>({
    resolver: zodResolver(auditSchema),
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  const [isSaving, setIsSaving] = useState(false);
  const data = dataProp || routeState.data || null;

  const handleEdit = () => setCurrentMode("edit");
  const handleCancel = () => {
    if (inline && onCancelInline) {
      onCancelInline();
    } else if (initialMode === "add") {
      // Navigate back or reset
    } else {
      setCurrentMode("view");
    }
  };
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

  const onSubmit = async (formData: z.infer<typeof auditSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createAudit(formData)
          : await updateAudit({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Audit ${
              currentMode === "add" ? "created" : "updated"
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
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            currentMode === "edit"
              ? "Edit Audit"
              : currentMode === "view"
              ? "View Audit"
              : "Audit Detail"
          }
        />
      )}

      <SimpleDetailHeader
        entityName="Audit"
        recordId={data?.id}
        recordName={data?.action || data?.description}
        mode={currentMode}
        backUrl={inline ? undefined : "/accounts/audits"}
        onClose={inline ? onCancelInline : undefined}
      />

      <SimpleDetailToolbar
        mode={currentMode}
        isSaving={isSaving}
        onSave={handleSubmit(onSubmit)}
        onCancel={handleCancel}
        onEdit={handleEdit}
      />

      <ComponentCard>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="date">date</Label>
              <Input
                type="date"
                id="date"
                placeholder="Audit Date"
                {...register("date")}
                error={errors.date && errors.date.message ? true : false}
                hint={errors.date && errors.date.message}
                disabled={currentMode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="action">action</Label>
              <Input
                type="text"
                id="action"
                placeholder="Audit Action"
                {...register("action")}
                error={errors.action && errors.action.message ? true : false}
                hint={errors.action && errors.action.message}
                disabled={currentMode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="user">user</Label>
              <Input
                type="text"
                id="user"
                placeholder="User"
                {...register("user")}
                error={errors.user && errors.user.message ? true : false}
                hint={errors.user && errors.user.message}
                disabled={currentMode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4">
            <div>
              <Label htmlFor="description">description</Label>
              <CustTextArea
                id="description"
                placeholder="Audit Description"
                {...register("description")}
                error={errors.description && errors.description.message ? true : false}
                hint={errors.description && errors.description.message}
                disabled={currentMode === "view"}
              />
            </div>
          </div>
        </form>
      </ComponentCard>
    </>
  );
}