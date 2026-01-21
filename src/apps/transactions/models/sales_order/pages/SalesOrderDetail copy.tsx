// @ts-nocheck
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createSalesOrder, updateSalesOrder, fetchSalesOrderLines, createSalesOrderLine, updateSalesOrderLine, deleteSalesOrderLine } from "../services/salesOrderApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { salesOrderSchema } from "../utils/salesOrderSchema";
import { SalesOrderAddProps } from "../types/salesOrderType";
import { AuditTrail } from "../../../../../components/transactions/common/AuditTrail";
import SalesOrderStatus from "../components/SalesOrderStatus";
import SalesOrderLineEditor from "../components/SalesOrderLineEditor";
import { getRecords } from "../../../../../api/wcapi";

export default function SalesOrderDetailTest({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: SalesOrderAddProps) {
  const dispatch = useDispatch();
  const [lineItems, setLineItems] = useState<any[]>([]);
  const [editingLineId, setEditingLineId] = useState<number | null>(null);
  const [newLine, setNewLine] = useState<any>({ item_id: undefined, item_name: '', description: '', quantity: 1, price: { sell: 0, cost: 0 }, discount_amount: 0 });
  const [searchId, setSearchId] = useState<string>('');
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [searchedData, setSearchedData] = useState<any>(null);

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof salesOrderSchema>>({
    resolver: zodResolver(salesOrderSchema),
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || searchedData || routeState.data || null;

  // Load line items when viewing/editing existing sales order
  const loadLineItems = async (salesOrderId: number) => {
    try {
      const response = await fetchSalesOrderLines(salesOrderId);
      if (response.status === 200) {
        setLineItems(response.data.results || []);
      }
    } catch (error) {
      console.error('Failed to load line items:', error);
    }
  };
  
  useEffect(() => {
    if (mode === "add") {
      reset({});
      setLineItems([]);
    } else if (data) {
      // Log the data to check what's being received
      console.log('Sales Order Data received:', data);
      
      // Map API response to form structure
      const formData = {
        // Fields from prefs.userdefined
        sales_order_no: data.prefs?.userdefined?.sales_order_no || '',
        id_customer: data.prefs?.userdefined?.id_customer || 0,
        total: data.prefs?.userdefined?.total || 0,
        tax: data.prefs?.userdefined?.tax || 0,
        discount: data.prefs?.userdefined?.discount || 0,
        id_transaction: data.prefs?.userdefined?.id_transaction || '',
        subtotal: data.prefs?.userdefined?.subtotal || 0,
        id_manufacturer: data.prefs?.userdefined?.id_manufacturer || 0,
        id_vendor: data.prefs?.userdefined?.id_vendor || 0,
        due_date: data.prefs?.userdefined?.due_date || '',
        valid_until: data.prefs?.userdefined?.valid_until || '',
        
        // Fields from root level
        status: data.status || 'draft',
        priority: data.priority || '',
        price_level: data.price_level || '',
        version: data.version || 0,
        
        // JSON fields - already at root level
        cost: data.cost || '',
        sell: data.sell || '',
        finance: data.finance || '',
        flow: data.flow || '',
        source: data.source || '',
        action: data.action || '',
        
        // Timestamps
        dt_created: data.dt_created,
        dt_modified: data.dt_modified,
      };
      
      // Reset form with mapped data
      reset(formData);
      
      // Load line items for existing sales orders
      if (data.id) {
        loadLineItems(data.id);
      }
    } else {
      reset({});
      setLineItems([]);
    }
  }, [data, reset, mode]);

  const onSubmit = async (formData: z.infer<typeof salesOrderSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createSalesOrder(formData)
          : await updateSalesOrder(data && data.id, formData);
      if (res) {
        dispatch(
          showToast({
            message: `Sales order ${
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
      await updateSalesOrder(data.id, { ...data, status: newStatus });
      dispatch(showToast({ message: `Sales order marked as ${newStatus}`, type: "success" }));
      if (onSaved) {
        onSaved();
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to update status";
      dispatch(showToast({ message, type: "error" }));
    }
  };

  const handleAddLine = () => {
    setEditingLineId(-1); // -1 for new line
    setNewLine({ item_id: undefined, item_name: '', description: '', quantity: 1, price: { sell: 0, cost: 0 }, discount_amount: 0 });
  };

  const handleEditLine = (line: any) => {
    setEditingLineId(line.id);
    setNewLine({ ...line });
  };

  const handleSaveLine = async () => {
    try {
      if (editingLineId === -1) {
        // New line
        if (data?.id) {
          await createSalesOrderLine(data.id, newLine);
          dispatch(showToast({ message: "Line item added successfully", type: "success" }));
        }
      } else {
        // Update line
        if (data?.id) {
          await updateSalesOrderLine(data.id, editingLineId!, newLine);
          dispatch(showToast({ message: "Line item updated successfully", type: "success" }));
        }
      }
      setEditingLineId(null);
      // Refresh line items
      if (data?.id) {
        loadLineItems(data.id);
      }
    } catch (error: any) {
      dispatch(showToast({ message: error.message || "Failed to save line item", type: "error" }));
    }
  };

  const handleDeleteLine = async (lineId: number) => {
    if (!data?.id) return;
    if (window.confirm('Delete this line item?')) {
      try {
        await deleteSalesOrderLine(data.id, lineId);
        dispatch(showToast({ message: "Line item deleted successfully", type: "success" }));
        loadLineItems(data.id);
      } catch (error: any) {
        dispatch(showToast({ message: error.message || "Failed to delete line item", type: "error" }));
      }
    }
  };

  const handleCancelEdit = () => {
    setEditingLineId(null);
    setNewLine({ item_id: undefined, item_name: '', description: '', quantity: 1, price: { sell: 0, cost: 0 }, discount_amount: 0 });
  };

  console.log("Errors:", errors);
  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Sales Order (id=" + (data?.id || "") + ")"
              : mode === "view"
              ? "View Sales Order (Test)"
              : "Sales Order Detail (Test)"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Sales Order (id=" + (data?.id || "") + ")"
                : mode === "view"
                ? "View Sales Order (id=" + (data?.id || "") + ")"
                : "Add New Sales Order (Test)"}
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
              <Label htmlFor="sales_order_no">sales_order_no</Label>
              <Input
                type="text"
                id="sales_order_no"
                placeholder="Sales Order Number"
                {...register("sales_order_no")}
                error={errors.sales_order_no && errors.sales_order_no.message ? true : false}
                hint={errors.sales_order_no && errors.sales_order_no.message}
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
                <option value="confirmed">Confirmed</option>
                <option value="shipped">Shipped</option>
                <option value="delivered">Delivered</option>
                <option value="cancelled">Cancelled</option>
              </select>
              {errors.status && <p className="text-red-500 text-sm">{errors.status.message}</p>}
            </div>
            <div>
              <Label htmlFor="id_customer">id_customer</Label>
              <Input
                type="number"
                id="id_customer"
                placeholder="Customer ID"
                {...register("id_customer")}
                error={errors.id_customer && errors.id_customer.message ? true : false}
                hint={errors.id_customer && errors.id_customer.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="total">total</Label>
              <Input
                type="number"
                id="total"
                placeholder="Total"
                {...register("total")}
                error={errors.total && errors.total.message ? true : false}
                hint={errors.total && errors.total.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="tax">tax</Label>
              <Input
                type="number"
                id="tax"
                placeholder="Tax"
                {...register("tax")}
                error={errors.tax && errors.tax.message ? true : false}
                hint={errors.tax && errors.tax.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="discount">discount</Label>
              <Input
                type="number"
                id="discount"
                placeholder="Discount"
                {...register("discount")}
                error={errors.discount && errors.discount.message ? true : false}
                hint={errors.discount && errors.discount.message}
                disabled={mode === "view"}
              />
            </div>
            {/* New fields based on updated schema */}
            <div>
              <Label htmlFor="id_transaction">id_transaction</Label>
              <Input
                type="text"
                id="id_transaction"
                placeholder="Transaction ID"
                {...register("id_transaction")}
                error={errors.id_transaction && errors.id_transaction.message ? true : false}
                hint={errors.id_transaction && errors.id_transaction.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="priority">priority</Label>
              <Input
                type="text"
                id="priority"
                placeholder="Priority"
                {...register("priority")}
                error={errors.priority && errors.priority.message ? true : false}
                hint={errors.priority && errors.priority.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="price_level">price_level</Label>
              <Input
                type="text"
                id="price_level"
                placeholder="Price Level"
                {...register("price_level")}
                error={errors.price_level && errors.price_level.message ? true : false}
                hint={errors.price_level && errors.price_level.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="id_manufacturer">id_manufacturer</Label>
              <Input
                type="number"
                id="id_manufacturer"
                placeholder="Manufacturer ID"
                {...register("id_manufacturer")}
                error={errors.id_manufacturer && errors.id_manufacturer.message ? true : false}
                hint={errors.id_manufacturer && errors.id_manufacturer.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="id_vendor">id_vendor</Label>
              <Input
                type="number"
                id="id_vendor"
                placeholder="Vendor ID"
                {...register("id_vendor")}
                error={errors.id_vendor && errors.id_vendor.message ? true : false}
                hint={errors.id_vendor && errors.id_vendor.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="subtotal">subtotal</Label>
              <Input
                type="number"
                id="subtotal"
                placeholder="Subtotal"
                {...register("subtotal")}
                error={errors.subtotal && errors.subtotal.message ? true : false}
                hint={errors.subtotal && errors.subtotal.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="due_date">due_date</Label>
              <Input
                type="date"
                id="due_date"
                {...register("due_date")}
                error={errors.due_date && errors.due_date.message ? true : false}
                hint={errors.due_date && errors.due_date.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="valid_until">valid_until</Label>
              <Input
                type="date"
                id="valid_until"
                {...register("valid_until")}
                error={errors.valid_until && errors.valid_until.message ? true : false}
                hint={errors.valid_until && errors.valid_until.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="version">version</Label>
              <Input
                type="number"
                id="version"
                placeholder="Version"
                {...register("version")}
                error={errors.version && errors.version.message ? true : false}
                hint={errors.version && errors.version.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          {/* JSON fields as textareas */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <Label htmlFor="cost">cost (JSON)</Label>
              <textarea
                id="cost"
                {...register("cost")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                placeholder='{"key": "value"}'
              />
              {errors.cost && typeof errors.cost === 'object' && 'message' in errors.cost && (
                <p className="text-red-500 text-sm mt-1">{String(errors.cost.message)}</p>
              )}
            </div>
            <div>
              <Label htmlFor="sell">sell (JSON)</Label>
              <textarea
                id="sell"
                {...register("sell")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                placeholder='{"key": "value"}'
              />
              {errors.sell && typeof errors.sell === 'object' && 'message' in errors.sell && (
                <p className="text-red-500 text-sm mt-1">{String(errors.sell.message)}</p>
              )}
            </div>
            <div>
              <Label htmlFor="finance">finance (JSON)</Label>
              <textarea
                id="finance"
                {...register("finance")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                placeholder='{"key": "value"}'
              />
              {errors.finance && typeof errors.finance === 'object' && 'message' in errors.finance && (
                <p className="text-red-500 text-sm mt-1">{String(errors.finance.message)}</p>
              )}
            </div>
            <div>
              <Label htmlFor="flow">flow (JSON)</Label>
              <textarea
                id="flow"
                {...register("flow")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                placeholder='{"key": "value"}'
              />
              {errors.flow && typeof errors.flow === 'object' && 'message' in errors.flow && (
                <p className="text-red-500 text-sm mt-1">{String(errors.flow.message)}</p>
              )}
            </div>
            <div>
              <Label htmlFor="source">source (JSON)</Label>
              <textarea
                id="source"
                {...register("source")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                placeholder='{"key": "value"}'
              />
              {errors.source && typeof errors.source === 'object' && 'message' in errors.source && (
                <p className="text-red-500 text-sm mt-1">{String(errors.source.message)}</p>
              )}
            </div>
            <div>
              <Label htmlFor="action">action (JSON)</Label>
              <textarea
                id="action"
                {...register("action")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                placeholder='{"key": "value"}'
              />
              {errors.action && typeof errors.action === 'object' && 'message' in errors.action && (
                <p className="text-red-500 text-sm mt-1">{String(errors.action.message)}</p>
              )}
            </div>
          </div>
          
          {/* Line Items Section */}
          {(mode === "edit" || mode === "add") && (
            <SalesOrderLineEditor
              lines={lineItems}
              editingId={editingLineId}
              newLine={newLine}
              onAdd={handleAddLine}
              onEdit={handleEditLine}
              onDelete={handleDeleteLine}
              onSave={handleSaveLine}
              onCancel={handleCancelEdit}
              onNewLineChange={setNewLine}
            />
          )}

          {mode === "view" && data && lineItems.length > 0 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold dark:text-white">Line Items</h3>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse border border-gray-300 dark:border-gray-600 text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                      <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-left">Item</th>
                      <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-left">Description</th>
                      <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">Qty</th>
                      <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">Price</th>
                      <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lineItems.map((item, index) => (
                      <tr key={item.id || index}>
                        <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">{item.item_name || 'Unknown'}</td>
                        <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">{item.description || ''}</td>
                        <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">{item.quantity || 0}</td>
                        <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">${item.price?.sell ? Number(item.price.sell).toFixed(2) : '0.00'}</td>
                        <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right font-medium">${item.extended_price ? Number(item.extended_price).toFixed(2) : '0.00'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

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
                {data.id && <AuditTrail transactionId={data.id} model="sales_order" />}
              </div>

              {/* Status Management */}
              <div>
                <Label>Sales Order Status</Label>
                <SalesOrderStatus
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