import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createInvoice, updateInvoice } from "../services/invoiceApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { invoiceSchema } from "../utils/invoiceSchema";
import { InvoiceAddProps } from "../types/invoiceType";
import { AuditTrail } from "../../../../../components/transactions/common/AuditTrail";
import InvoiceStatus from "../components/InvoiceStatus";

export default function InvoiceDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: InvoiceAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof invoiceSchema>>({
    resolver: zodResolver(invoiceSchema),
  });

  const location = useLocation();
  const routeState = (location.state as { mode?: string; data?: z.infer<typeof invoiceSchema> }) || {};
  const mode: "add" | "edit" | "view" = modeProp || (routeState.mode as "add" | "edit" | "view" | undefined) || "add";
  const data = dataProp || routeState.data || null;
  useEffect(() => {
    if (mode === "add") {
      reset();
    } else if (data) {
      Object.keys(data).forEach((key: string) => {
        if (data[key as keyof typeof data] !== undefined) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          setValue(key as any, data[key as keyof typeof data]);
        }
      });
    } else {
      reset({});
    }
  }, [data, reset, setValue, mode]);

  const onSubmit = async (formData: z.infer<typeof invoiceSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createInvoice(formData)
          : await updateInvoice(data && data.id, formData);
      if (res) {
        dispatch(
          showToast({
            message: `Invoice ${
              mode === "add" ? "created" : "updated"
            } successfully`,
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        }
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'An error occurred';
      dispatch(showToast({ message, type: "error" }));
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!data?.id) return;
    try {
      await updateInvoice(data.id, { ...data, status: newStatus });
      dispatch(showToast({ message: `Invoice marked as ${newStatus}`, type: "success" }));
      if (onSaved) {
        onSaved();
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to update status";
      dispatch(showToast({ message, type: "error" }));
    }
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Invoice"
              : mode === "view"
              ? "View Invoice"
              : "Invoice Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Invoice"
                : mode === "view"
                ? "View Invoice"
                : "Add New Invoice"}
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
           <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
             <div>
               <Label htmlFor="invoice_no">invoice_no</Label>
               <Input
                 type="text"
                 id="invoice_no"
                 placeholder="Invoice Number"
                 {...register("invoice_no")}
                 error={errors.invoice_no && errors.invoice_no.message ? true : false}
                 hint={errors.invoice_no && errors.invoice_no.message}
                 disabled={mode === "view"}
               />
             </div>
             <div>
               <Label htmlFor="status">status</Label>
               <select
                 id="status"
                 {...register("status")}
                 disabled={mode === "view"}
                 className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
               >
                 <option value="draft">Draft</option>
                 <option value="sent">Sent</option>
                 <option value="paid">Paid</option>
                 <option value="overdue">Overdue</option>
                 <option value="cancelled">Cancelled</option>
               </select>
               {errors.status && <p className="text-red-500 text-sm">{errors.status.message}</p>}
             </div>
           </div>
          {mode === "view" && data && (
            <div className="space-y-6">
              <div>
                <Label htmlFor="dt_created">dt_created</Label>
                <Input
                  type="text"
                  id="dt_created"
                  value={new Date(data.dt_created * 1000).toLocaleString()}
                  disabled
                />
                {data.id && <AuditTrail transactionId={data.id} model="invoice" />}
              </div>

              {/* Status Management */}
              <div>
                <Label>Invoice Status</Label>
                <InvoiceStatus
                  currentStatus={data.status || 'draft'}
                  onStatusChange={handleStatusChange}
                  showHistory={true}
                />
              </div>
            </div>
          )}
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