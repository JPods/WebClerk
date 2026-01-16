import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createPurchaseOrder, updatePurchaseOrder, fetchPurchaseOrderDetail } from "../services/purchaseOrderApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate, useParams } from "react-router";
import { purchaseOrderSchema } from "../utils/purchaseOrderSchema";
import { PurchaseOrderAddProps } from "../types/purchaseOrderType";
import { AuditTrail } from "../../../../../components/transactions/common/AuditTrail";
import PurchaseOrderStatus from "../components/PurchaseOrderStatus";
import { coerceFormValue, sanitizeRecord, formatDateTimeValue } from "../../common/valueNormalization";
import JsonEnvelopesPanel from "../../../components/JsonEnvelopesPanel";

const numericPurchaseOrderKeys = ["dt_created", "id_vendor"];

export default function PurchaseOrderDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
  isAdmin = false,
}: PurchaseOrderAddProps) {
  const dispatch = useDispatch();
  const location = useLocation();
  const navigate = useNavigate();
  const { id: routeId } = useParams<{ id?: string }>();
  const routeState = (location.state as any) || {};
  const routeData = routeState?.data;
  const routeMode = routeState?.mode as "add" | "edit" | "view" | undefined;
  const shouldPrefetch = Boolean(routeId && !dataProp && !routeData);

  const [fetchedData, setFetchedData] = useState<any>(null);
  const [loading, setLoading] = useState(shouldPrefetch);
  const [loadError, setLoadError] = useState<string | null>(null);

  const resolvedData = dataProp ?? routeData ?? fetchedData;
  const normalizedResolvedData = useMemo(
    () => sanitizeRecord(resolvedData, numericPurchaseOrderKeys),
    [resolvedData]
  );

  const mode: "add" | "edit" | "view" = modeProp || routeMode || (routeId ? "view" : "add");
  const pageTitle =
    mode === "edit"
      ? "Edit Purchase Order"
      : mode === "view"
      ? "View Purchase Order"
      : "Purchase Order Detail";
  const inlineTitle = mode === "add" ? "Add New Purchase Order" : pageTitle;

  const defaultValues = useMemo(
    () => ({
      purchase_order_no: "",
      status: "draft",
      receipt_id: "",
      vendor_pack_list: "",
      vendor_pack_date: "",
      id_vendor: undefined,
    }),
    []
  );

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof purchaseOrderSchema>>({
    resolver: zodResolver(purchaseOrderSchema),
    defaultValues,
  });

  useEffect(() => {
    if (dataProp || routeData) {
      setFetchedData(null);
    }
  }, [dataProp, routeData]);

  useEffect(() => {
    if (normalizedResolvedData) {
      setLoadError(null);
    }
  }, [normalizedResolvedData]);

  useEffect(() => {
    if (dataProp || routeData || !routeId) {
      return;
    }

    const idNumber = Number.parseInt(routeId, 10);
    if (Number.isNaN(idNumber)) {
      setLoadError("Invalid purchase order id");
      setLoading(false);
      return;
    }

    let cancelled = false;

    setFetchedData(null);
    setLoading(true);
    setLoadError(null);

    fetchPurchaseOrderDetail(idNumber)
      .then((detail) => {
        if (cancelled) {
          return;
        }
        if (!detail || Object.keys(detail).length === 0) {
          setLoadError("Purchase order not found");
          return;
        }
        setFetchedData(sanitizeRecord(detail, numericPurchaseOrderKeys));
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        const message = error instanceof Error ? error.message : "Failed to load purchase order";
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
      return;
    }

    if (normalizedResolvedData && typeof normalizedResolvedData === "object") {
      const nextValues = { ...defaultValues } as Record<string, unknown>;
      Object.keys(defaultValues).forEach((key) => {
        const value = (normalizedResolvedData as Record<string, unknown>)[key];
        const sanitized = coerceFormValue(value);
        if (sanitized !== undefined) {
          nextValues[key] = sanitized === null ? "" : (sanitized as unknown);
        }
      });
      reset(nextValues);
      return;
    }

    reset(defaultValues);
  }, [normalizedResolvedData, reset, mode, defaultValues]);

  const onSubmit = async (formData: z.infer<typeof purchaseOrderSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createPurchaseOrder(formData)
          : await updatePurchaseOrder(resolvedData && resolvedData.id, formData);
      if (res) {
        dispatch(
          showToast({
            message: `Purchase order ${
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

  const handleStatusChange = async (newStatus: string) => {
    if (!resolvedData?.id) return;
    try {
      await updatePurchaseOrder(resolvedData.id, { ...resolvedData, status: newStatus });
      dispatch(showToast({ message: `Purchase order marked as ${newStatus}`, type: "success" }));
      if (onSaved) {
        onSaved();
      }
    } catch (error: any) {
      dispatch(showToast({ message: error.message || "Failed to update status", type: "error" }));
    }
  };

  if (!inline && loading) {
    return (
      <>
        {!hideBreadcrumb && <PageBreadcrumb pageTitle={pageTitle} />}
        <ComponentCard>
          <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400">Loading purchase order...</div>
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
        <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400">Loading purchase order...</div>
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
               <Label htmlFor="purchase_order_no">purchase_order_no</Label>
               <Input
                 type="text"
                 id="purchase_order_no"
                 placeholder="Purchase Order Number"
                 {...register("purchase_order_no")}
                 error={!!errors.purchase_order_no?.message}
                 hint={errors.purchase_order_no?.message}
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
                 <option value="approved">Approved</option>
                 <option value="rejected">Rejected</option>
                 <option value="received">Received</option>
                 <option value="closed">Closed</option>
               </select>
               {errors.status && <p className="text-red-500 text-sm">{errors.status.message}</p>}
             </div>
           </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <Label htmlFor="receipt_id">Receipt ID</Label>
                <Input
                  type="text"
                  id="receipt_id"
                  placeholder="Receipt ID"
                  {...register("receipt_id")}
                  error={!!errors.receipt_id?.message}
                  hint={errors.receipt_id?.message}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="vendor_pack_list">Vendor Pack List</Label>
                <Input
                  type="text"
                  id="vendor_pack_list"
                  placeholder="Vendor Pack List"
                  {...register("vendor_pack_list")}
                  error={!!errors.vendor_pack_list?.message}
                  hint={errors.vendor_pack_list?.message}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="vendor_pack_date">Vendor Pack Date</Label>
                <Input
                  type="date"
                  id="vendor_pack_date"
                  {...register("vendor_pack_date")}
                  error={!!errors.vendor_pack_date?.message}
                  hint={errors.vendor_pack_date?.message}
                  disabled={mode === "view"}
                />
              </div>
            </div>
          {mode === "view" && normalizedResolvedData && (
            <div className="space-y-6">
              <div>
                <Label htmlFor="dt_created">dt_created</Label>
                <Input
                  type="text"
                  id="dt_created"
                  value={formatDateTimeValue(normalizedResolvedData.dt_created)}
                  disabled
                />
                {normalizedResolvedData.id && <AuditTrail transactionId={normalizedResolvedData.id} model="purchase_order" />}
              </div>

              {/* Status Management */}
              <div>
                <Label>Purchase Order Status</Label>
                <PurchaseOrderStatus
                  currentStatus={normalizedResolvedData.status || 'draft'}
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

          {/* Admin/Developer JSON Envelopes Panel */}
          <JsonEnvelopesPanel
            data={normalizedResolvedData || {}}
            isVisible={isAdmin}
            isEditing={mode === "edit"}
          />
        </form>
      </ComponentCard>
    </>
  );
}