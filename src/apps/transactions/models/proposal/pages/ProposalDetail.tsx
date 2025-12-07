import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createProposal, updateProposal, convertProposalToOrder, fetchProposalLines } from "../services/proposalApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { proposalSchema } from "../utils/proposalSchema";
import { ProposalAddProps } from "../types/proposalType";
import { FaPlus, FaTrash, FaEdit } from "react-icons/fa";

export default function ProposalDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ProposalAddProps) {
  const dispatch = useDispatch();
  const [lineItems, setLineItems] = useState<any[]>([]);

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof proposalSchema>>({
    resolver: zodResolver(proposalSchema),
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;
  // Load line items when viewing/editing existing proposal
  const loadLineItems = async (proposalId: number) => {
    try {
      const response = await fetchProposalLines(proposalId);
      if (response.status === 200) {
        setLineItems(response.data.results || []);
      }
    } catch (error) {
      console.error('Failed to load line items:', error);
    }
  };

  useEffect(() => {
    if (mode === "add") {
      reset();
      setLineItems([]);
    } else if (data) {
      Object.keys(data).forEach((key: any) => {
        if (data[key] !== undefined) {
          setValue(key, data[key]);
        }
      });
      // Load line items for existing proposals
      if (data.id) {
        loadLineItems(data.id);
      }
    } else {
      reset({});
      setLineItems([]);
    }
  }, [data, reset, setValue, mode]);

  const onSubmit = async (formData: z.infer<typeof proposalSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createProposal(formData)
          : await updateProposal(data?.id, { ...formData, id: data?.id });
      if (res) {
        dispatch(
          showToast({
            message: `Proposal ${
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

  const handleConvertToOrder = async () => {
    if (!data?.id) return;

    try {
      const res = await convertProposalToOrder(data.id);
      if (res.status === 200) {
        dispatch(
          showToast({
            message: "Proposal converted to sales order successfully",
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        }
      }
    } catch (error: any) {
      dispatch(showToast({ message: error.message || "Failed to convert proposal", type: "error" }));
    }
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Proposal"
              : mode === "view"
              ? "View Proposal"
              : "Proposal Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Proposal"
                : mode === "view"
                ? "View Proposal"
                : "Add New Proposal"}
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
          {/* Basic Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <Label htmlFor="ida">Proposal ID</Label>
              <Input
                type="text"
                id="ida"
                placeholder="Proposal ID"
                {...register("ida")}
                error={errors.ida && errors.ida.message ? true : false}
                hint={errors.ida && errors.ida.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="status">Status</Label>
              <select
                id="status"
                {...register("status")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                <option value="planned">Planned</option>
                <option value="released">Released</option>
                <option value="in_progress">In Progress</option>
                <option value="hold">Hold</option>
                <option value="complete">Complete</option>
                <option value="canceled">Canceled</option>
              </select>
            </div>
          </div>

          {/* Customer Information */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <Label htmlFor="id_customer">Customer ID *</Label>
              <Input
                type="number"
                id="id_customer"
                placeholder="Customer ID"
                {...register("id_customer", { valueAsNumber: true })}
                error={errors.id_customer && errors.id_customer.message ? true : false}
                hint={errors.id_customer && errors.id_customer.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="id_manufacturer">Manufacturer ID</Label>
              <Input
                type="number"
                id="id_manufacturer"
                placeholder="Manufacturer ID"
                {...register("id_manufacturer", { valueAsNumber: true })}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="id_vendor">Vendor ID</Label>
              <Input
                type="number"
                id="id_vendor"
                placeholder="Vendor ID"
                {...register("id_vendor", { valueAsNumber: true })}
                disabled={mode === "view"}
              />
            </div>
          </div>

          {/* Additional Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <Label htmlFor="priority">Priority</Label>
              <Input
                type="text"
                id="priority"
                placeholder="Priority"
                {...register("priority")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="price_level">Price Level</Label>
              <Input
                type="text"
                id="price_level"
                placeholder="Price Level"
                {...register("price_level")}
                disabled={mode === "view"}
              />
            </div>
          </div>

          {/* Line Items Section */}
          {(mode === "edit" || mode === "add") && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold dark:text-white">Line Items</h3>
                <button
                  type="button"
                  className="flex items-center gap-2 px-3 py-1 text-white bg-green-500 rounded-md hover:bg-green-600 text-sm"
                >
                  <FaPlus className="text-xs" />
                  Add Item
                </button>
              </div>

              {lineItems.length === 0 ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  No line items added yet. Click "Add Item" to get started.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse border border-gray-300 dark:border-gray-600 text-sm">
                    <thead className="bg-gray-50 dark:bg-gray-800">
                      <tr>
                        <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-left">Item</th>
                        <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-left">Description</th>
                        <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">Qty</th>
                        <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">Price</th>
                        <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">Total</th>
                        <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-center">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lineItems.map((item, index) => (
                        <tr key={item.id || index} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                          <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">{item.item_name || 'Unknown'}</td>
                          <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">{item.description || ''}</td>
                          <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">{item.quantity || 0}</td>
                          <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">${item.price?.sell ? Number(item.price.sell).toFixed(2) : '0.00'}</td>
                          <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right font-medium">${item.extended_price ? Number(item.extended_price).toFixed(2) : '0.00'}</td>
                          <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-center">
                            <div className="flex gap-1 justify-center">
                              <button type="button" className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded">
                                <FaEdit className="text-blue-600 text-xs" />
                              </button>
                              <button type="button" className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded">
                                <FaTrash className="text-red-600 text-xs" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Totals Summary */}
              {lineItems.length > 0 && (
                <div className="flex justify-end">
                  <div className="w-64 space-y-2">
                    <div className="flex justify-between">
                      <span>Subtotal:</span>
                      <span>${lineItems.reduce((sum, item) => sum + (item.extended_price || 0), 0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between font-semibold text-lg border-t pt-2">
                      <span>Total:</span>
                      <span>${lineItems.reduce((sum, item) => sum + (item.extended_price || 0), 0).toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {mode === "view" && data && (
            <div className="space-y-6">
              {/* Line Items Display for View Mode */}
              {lineItems.length > 0 && (
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

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <Label htmlFor="dt_created">Created Date</Label>
                  <Input
                    type="text"
                    id="dt_created"
                    value={data.dt_created ? new Date(data.dt_created).toLocaleString() : ''}
                    disabled
                  />
                </div>
                <div>
                  <Label htmlFor="dt_modified">Modified Date</Label>
                  <Input
                    type="text"
                    id="dt_modified"
                    value={data.dt_modified ? new Date(data.dt_modified).toLocaleString() : ''}
                    disabled
                  />
                </div>
              </div>

              {/* Actions for view mode */}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleConvertToOrder}
                  className="flex items-center px-4 py-2 text-white bg-green-500 rounded-md hover:bg-green-600"
                >
                  Convert to Sales Order
                </button>
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