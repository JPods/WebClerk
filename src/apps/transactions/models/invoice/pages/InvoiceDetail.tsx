import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input, TextArea } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createInvoice, updateInvoice, fetchInvoiceDetail } from "../services/invoiceApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate, useParams } from "react-router";
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
  const location = useLocation();
  const navigate = useNavigate();
  const { id: routeId } = useParams<{ id?: string }>();
  const routeState = (location.state as { mode?: string; data?: any }) || {};
  const routeData = routeState?.data;
  const routeMode = routeState?.mode as "add" | "edit" | "view" | undefined;
  const shouldPrefetch = Boolean(routeId && !dataProp && !routeData);

  const [isNotesLocked, setIsNotesLocked] = useState(true);
  const [loading, setLoading] = useState(shouldPrefetch);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [fetchedData, setFetchedData] = useState<any>(null);

  const resolvedData = dataProp ?? routeData ?? fetchedData;

  const mode: "add" | "edit" | "view" = modeProp || routeMode || (routeId ? "view" : "add");
  const pageTitle =
    mode === "edit"
      ? "Edit Invoice"
      : mode === "view"
      ? "View Invoice"
      : "Invoice Detail";
  const inlineTitle = mode === "add" ? "Add New Invoice" : pageTitle;

  const defaultValues = useMemo(
    () => ({
      invoice_no: "",
      status: "draft",
      company: "",
      attention: "",
      address1: "",
      address2: "",
      city: "",
      state: "",
      zip: "",
      email: "",
      phoneCell: "",
      phone: "",
      actionBy: "",
      action: "",
      actionDate: "",
      actionTime: "",
      salesName: "",
      orderedBy: "",
      contractDetailTag: "",
      terms: "",
      typeSale: "",
      taxJuris: "",
      adSource: "",
      addComment: "",
      comment: "",
      contractDetail: "",
      price_level: "",
      vendor_id: undefined,
      manufacturer_id: undefined,
    }),
    []
  );

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof invoiceSchema>>({
    resolver: zodResolver(invoiceSchema),
    defaultValues,
  });

  useEffect(() => {
    if (dataProp || routeData) {
      setFetchedData(null);
    }
  }, [dataProp, routeData]);

  useEffect(() => {
    if (resolvedData) {
      setLoadError(null);
    }
  }, [resolvedData]);

  useEffect(() => {
    if (dataProp || routeData || !routeId) {
      return;
    }

    const idNumber = Number.parseInt(routeId, 10);
    if (Number.isNaN(idNumber)) {
      setLoadError("Invalid invoice id");
      setLoading(false);
      return;
    }

    let cancelled = false;

    setFetchedData(null);
    setLoading(true);
    setLoadError(null);

    fetchInvoiceDetail(idNumber)
      .then((detail) => {
        if (cancelled) {
          return;
        }
        if (!detail || Object.keys(detail).length === 0) {
          setLoadError("Invoice not found");
          return;
        }
        setFetchedData(detail);
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        const message = error instanceof Error ? error.message : "Failed to load invoice";
        setLoadError(message);
        dispatch(showToast({ message, type: "error" }));
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [dataProp, routeData, routeId, dispatch]);

  useEffect(() => {
    if (mode === "add") {
      reset(defaultValues);
      setIsNotesLocked(true);
      return;
    }

    if (resolvedData && typeof resolvedData === "object") {
      const nextValues = { ...defaultValues } as Partial<z.infer<typeof invoiceSchema>>;
      Object.keys(defaultValues).forEach((key) => {
        const value = (resolvedData as Record<string, unknown>)[key];
        if (value !== undefined) {
          (nextValues as Record<string, unknown>)[key] = value as unknown;
        }
      });
      reset(nextValues);
      setIsNotesLocked(true);
      return;
    }

    reset(defaultValues);
    setIsNotesLocked(true);
  }, [resolvedData, defaultValues, reset, mode]);

  const onSubmit = async (formData: z.infer<typeof invoiceSchema>) => {
    try {
      // Sanitize payload and fold addComment into comment like the legacy Vue form
      const payload: Record<string, unknown> = {};
      Object.entries(formData).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          payload[key] = value;
        }
      });

      if (formData.addComment) {
        const timestamp = new Date().toISOString();
        const existingComment = formData.comment ? `\n${formData.comment}` : "";
        payload.comment = `${timestamp}: ${formData.addComment}${existingComment}`;
      }
      delete payload.addComment;

      const res =
        mode === "add"
          ? await createInvoice(payload)
          : await updateInvoice(resolvedData && resolvedData.id, payload);
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
    if (!resolvedData?.id) return;
    try {
      await updateInvoice(resolvedData.id, { ...resolvedData, status: newStatus });
      dispatch(showToast({ message: `Invoice marked as ${newStatus}`, type: "success" }));
      if (onSaved) {
        onSaved();
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to update status";
      dispatch(showToast({ message, type: "error" }));
    }
  };

  if (!inline && loading) {
    return (
      <>
        {!hideBreadcrumb && <PageBreadcrumb pageTitle={pageTitle} />}
        <ComponentCard>
          <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400">Loading invoice...</div>
        </ComponentCard>
      </>
    );
  }

  if (!inline && loadError && !resolvedData) {
    return (
      <>
        {!hideBreadcrumb && <PageBreadcrumb pageTitle={pageTitle} />}
        <ComponentCard>
          <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400 space-y-4">
            <div>{loadError}</div>
            <div>
              <button
                type="button"
                onClick={() => navigate(-1)}
                className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-500 rounded-md hover:bg-blue-600"
              >
                Go Back
              </button>
            </div>
          </div>
        </ComponentCard>
      </>
    );
  }

  if (inline && mode !== "add" && !resolvedData) {
    return (
      <ComponentCard>
        <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400">Loading invoice...</div>
      </ComponentCard>
    );
  }

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb pageTitle={pageTitle} />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {inlineTitle}
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
                error={Boolean(errors.invoice_no?.message)}
                hint={errors.invoice_no?.message}
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

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <Label htmlFor="company">company</Label>
              <Input
                type="text"
                id="company"
                placeholder="Company"
                {...register("company")}
                error={Boolean(errors.company?.message)}
                hint={errors.company?.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="attention">attention</Label>
              <Input
                type="text"
                id="attention"
                placeholder="Attention"
                {...register("attention")}
                error={Boolean(errors.attention?.message)}
                hint={errors.attention?.message}
                disabled={mode === "view"}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <Label htmlFor="address1">address1</Label>
              <Input
                type="text"
                id="address1"
                placeholder="Address line 1"
                {...register("address1")}
                error={Boolean(errors.address1?.message)}
                hint={errors.address1?.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="address2">address2</Label>
              <Input
                type="text"
                id="address2"
                placeholder="Address line 2"
                {...register("address2")}
                disabled={mode === "view"}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <Label htmlFor="city">city</Label>
              <Input
                type="text"
                id="city"
                placeholder="City"
                {...register("city")}
                error={Boolean(errors.city?.message)}
                hint={errors.city?.message}
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
                error={Boolean(errors.state?.message)}
                hint={errors.state?.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="zip">zip</Label>
              <Input
                type="text"
                id="zip"
                placeholder="Zip"
                {...register("zip")}
                error={Boolean(errors.zip?.message)}
                hint={errors.zip?.message}
                disabled={mode === "view"}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <Label htmlFor="email">email</Label>
              <Input
                type="email"
                id="email"
                placeholder="Email"
                {...register("email")}
                error={Boolean(errors.email?.message)}
                hint={errors.email?.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="phoneCell">phoneCell</Label>
              <Input
                type="text"
                id="phoneCell"
                placeholder="Cell Phone"
                {...register("phoneCell")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="phone">phone</Label>
              <Input
                type="text"
                id="phone"
                placeholder="Phone"
                {...register("phone")}
                disabled={mode === "view"}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <Label htmlFor="actionBy">actionBy</Label>
              <Input
                type="text"
                id="actionBy"
                placeholder="Action By"
                {...register("actionBy")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="action">action</Label>
              <Input
                type="text"
                id="action"
                placeholder="Action"
                {...register("action")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="actionDate">actionDate</Label>
              <Input
                type="date"
                id="actionDate"
                {...register("actionDate")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="actionTime">actionTime</Label>
              <Input
                type="time"
                id="actionTime"
                {...register("actionTime")}
                disabled={mode === "view"}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <Label htmlFor="salesName">salesName</Label>
              <Input
                type="text"
                id="salesName"
                placeholder="Sales Name"
                {...register("salesName")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="orderedBy">orderedBy</Label>
              <Input
                type="text"
                id="orderedBy"
                placeholder="Ordered By"
                {...register("orderedBy")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="contractDetailTag">contractDetailTag</Label>
              <Input
                type="text"
                id="contractDetailTag"
                placeholder="Contract Detail"
                {...register("contractDetailTag")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="terms">terms</Label>
              <Input
                type="text"
                id="terms"
                placeholder="Terms"
                {...register("terms")}
                disabled={mode === "view"}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <Label htmlFor="typeSale">typeSale</Label>
              <Input
                type="text"
                id="typeSale"
                placeholder="Type of Sale"
                {...register("typeSale")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="taxJuris">taxJuris</Label>
              <Input
                type="text"
                id="taxJuris"
                placeholder="Tax Jurisdiction"
                {...register("taxJuris")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="adSource">adSource</Label>
              <Input
                type="text"
                id="adSource"
                placeholder="Ad Source"
                {...register("adSource")}
                disabled={mode === "view"}
              />
            </div>
          </div>

          <div>
            <Label htmlFor="addComment">addComment</Label>
            <TextArea
              rows={3}
              placeholder="Add comment"
              register={register("addComment")}
              disabled={mode === "view"}
              error={errors.addComment}
              hint={errors.addComment?.message}
            />
          </div>

          <div className="flex items-center justify-between">
            <h4 className="font-semibold text-gray-800 dark:text-white">Notes</h4>
            {mode !== "view" && (
              <button
                type="button"
                onClick={() => setIsNotesLocked((prev) => !prev)}
                className="px-3 py-1 text-sm rounded-md border border-gray-300 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:border-gray-700"
              >
                {isNotesLocked ? "Edit" : "Lock"}
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <Label htmlFor="comment">comment</Label>
              <TextArea
                rows={4}
                placeholder="Comment"
                register={register("comment")}
                disabled={mode === "view" || isNotesLocked}
                error={errors.comment}
                hint={errors.comment?.message}
              />
            </div>
            <div>
              <Label htmlFor="contractDetail">contractDetail</Label>
              <TextArea
                rows={4}
                placeholder="Contract Detail"
                register={register("contractDetail")}
                disabled={mode === "view" || isNotesLocked}
                error={errors.contractDetail}
                hint={errors.contractDetail?.message}
              />
            </div>
          </div>
          {mode === "view" && resolvedData && (
            <div className="space-y-6">
              <div>
                <Label htmlFor="dt_created">dt_created</Label>
                <Input
                  type="text"
                  id="dt_created"
                  value={resolvedData.dt_created ? new Date(resolvedData.dt_created * 1000).toLocaleString() : ""}
                  disabled
                />
                {resolvedData.id && <AuditTrail transactionId={resolvedData.id} model="invoice" />}
              </div>

              {/* Status Management */}
              <div>
                <Label>Invoice Status</Label>
                <InvoiceStatus
                  currentStatus={resolvedData.status || 'draft'}
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