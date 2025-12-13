import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createProposal, updateProposal, convertProposalToOrder, fetchProposalLines, createProposalLine, updateProposalLine, deleteProposalLine } from "../services/proposalApi";
import { generateProposalPdf } from "../services/proposalPdfService";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { proposalSchema } from "../utils/proposalSchema";
import { ProposalAddProps } from "../types/proposalType";
import ProposalLineList from "../components/ProposalLineList";
import ProposalStatus from "../components/ProposalStatus";
import CustomerSelect from "../components/CustomerSelect";

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
  const [editingLineId, setEditingLineId] = useState<number | null>(null);
  const [newLine, setNewLine] = useState<any>({ item_id: undefined, item_name: '', description: '', quantity: 1, price: { sell: 0, cost: 0 }, discount_amount: 0 });

  type ProposalFormData = z.infer<typeof proposalSchema>;

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ProposalFormData>({
    resolver: zodResolver(proposalSchema),
    mode: "onSubmit",
    reValidateMode: "onChange",
  });

  const location = useLocation();
  const navigate = useNavigate();
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

  const onSubmit = async (formData: ProposalFormData) => {
    try {
      // Clean up the data - remove undefined and null values, but keep valid values
      const cleanData: any = {};
      Object.keys(formData).forEach(key => {
        const value = (formData as any)[key];
        // Skip undefined and null, but allow 0, false, and empty strings for text fields
        if (value !== undefined && value !== null) {
          // For empty strings, only include for string fields (ida, priority, price_level, status)
          if (value === '' && ['ida', 'priority', 'price_level', 'status'].includes(key)) {
            // Skip empty strings for optional text fields
            return;
          }
          cleanData[key] = value;
        }
      });
      
      const res =
        mode === "add"
          ? await createProposal(cleanData)
          : await updateProposal(data?.id, { 
              ...cleanData, 
              id: data?.id
            });
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
          await createProposalLine(data.id, newLine);
          dispatch(showToast({ message: "Line item added successfully", type: "success" }));
        }
      } else {
        // Update line
        if (data?.id) {
          await updateProposalLine(data.id, editingLineId!, newLine);
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
        await deleteProposalLine(data.id, lineId);
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

  const handleStatusChange = async (newStatus: string) => {
    if (!data?.id) return;
    try {
      await updateProposal(data.id, { ...data, status: newStatus });
      dispatch(showToast({ message: `Proposal marked as ${newStatus}`, type: "success" }));
      if (onSaved) {
        onSaved();
      }
    } catch (error: any) {
      dispatch(showToast({ message: error.message || "Failed to update status", type: "error" }));
    }
  };
 console.log('Errors:', errors);
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
              <Label htmlFor="ida">ida</Label>
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
              <Label htmlFor="status">status</Label>
              <select
                id="status"
                {...register("status")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                <option value="planned">Planned</option>
                <option value="sent">Sent</option>
                <option value="accepted">Accepted</option>
                <option value="rejected">Rejected</option>
                <option value="cancelled">Cancelled</option>
              </select>
              {errors.status && <p className="text-red-500 text-sm">{errors.status.message}</p>}
            </div>
          </div>

          {/* Customer Information */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <Label htmlFor="id_customer">id_customer *</Label>
              <CustomerSelect
                value={data?.id_customer}
                onChange={(value) => {
                  setValue("id_customer", value as any, { shouldValidate: true });
                }}
                disabled={mode === "view"}
              />
              {errors.id_customer && <p className="text-red-500 text-sm">{errors.id_customer.message}</p>}
            </div>
            <div>
              <Label htmlFor="id_manufacturer">id_manufacturer</Label>
              <Input
                type="number"
                id="id_manufacturer"
                placeholder="Manufacturer ID"
                {...register("id_manufacturer")}
                disabled={mode === "view"}
              />
              {errors.id_manufacturer && <p className="text-red-500 text-sm">{errors.id_manufacturer.message}</p>}
            </div>
            <div>
              <Label htmlFor="id_vendor">id_vendor</Label>
              <CustomerSelect
                value={data?.id_vendor}
                onChange={(value) => setValue("id_vendor", value as any)}
                disabled={mode === "view"}
                contactType="vendor"
              />
              {errors.id_vendor && <p className="text-red-500 text-sm">{errors.id_vendor.message}</p>}
            </div>
          </div>

          {/* Additional Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <Label htmlFor="priority">priority</Label>
              <Input
                type="text"
                id="priority"
                placeholder="Priority"
                {...register("priority")}
                disabled={mode === "view"}
              />
              {errors.priority && <p className="text-red-500 text-sm">{errors.priority.message}</p>}
            </div>
            <div>
              <Label htmlFor="price_level">price_level</Label>
              <Input
                type="text"
                id="price_level"
                placeholder="Price Level"
                {...register("price_level")}
                disabled={mode === "view"}
              />
              {errors.price_level && <p className="text-red-500 text-sm">{errors.price_level.message}</p>}
            </div>
          </div>

          {/* Line Items Section */}
          {(mode === "edit" || mode === "add") && (
            <ProposalLineList
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
   
                  {/* Related Records */}
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-md">
                    <h4 className="text-lg font-semibold mb-3 dark:text-white">Related Records</h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">0</div>
                        <div className="text-sm text-gray-600 dark:text-gray-400">Documents</div>
                        <button
                          className="mt-2 rounded bg-blue-500 px-4 py-2 text-white hover:bg-blue-600"
                          onClick={() => navigate('/docs/document/list')}
                        >
                          View Documents
                        </button>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-600 dark:text-green-400">0</div>
                        <div className="text-sm text-gray-600 dark:text-gray-400">Linkages</div>
                        <button
                          className="mt-2 rounded bg-green-500 px-4 py-2 text-white hover:bg-green-600"
                          onClick={() => navigate('/docs/linkage/list')}
                        >
                          View Linkages
                        </button>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">0</div>
                        <div className="text-sm text-gray-600 dark:text-gray-400">Q&A Records</div>
                        <button
                          className="mt-2 rounded bg-purple-500 px-4 py-2 text-white hover:bg-purple-600"
                          onClick={() => navigate('/docs/question-answer/list')}
                        >
                          View Q&A
                        </button>
                      </div>
                    </div>
                  </div>
   
                </div>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <Label>Customer</Label>
                  <Input
                    type="text"
                    value={data.customer_name || 'Not specified'}
                    disabled
                  />
                </div>
                <div>
                  <Label>Vendor</Label>
                  <Input
                    type="text"
                    value={data.vendor_name || 'Not specified'}
                    disabled
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <Label htmlFor="dt_created">dt_created</Label>
                  <Input
                    type="text"
                    id="dt_created"
                    value={data.dt_created ? new Date(data.dt_created).toLocaleString() : ''}
                    disabled
                  />
                </div>
                <div>
                  <Label htmlFor="dt_modified">dt_modified</Label>
                  <Input
                    type="text"
                    id="dt_modified"
                    value={data.dt_modified ? new Date(data.dt_modified).toLocaleString() : ''}
                    disabled
                  />
                </div>
              </div>

              {/* Status Management */}
              <div>
                <Label>Proposal Status</Label>
                <ProposalStatus
                  currentStatus={data.status || 'planned'}
                  onStatusChange={handleStatusChange}
                  showHistory={true}
                />
              </div>

              {/* Special Actions */}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => generateProposalPdf({
                    proposal: data,
                    lines: lineItems,
                    customerName: data.customer_name,
                    vendorName: data.vendor_name
                  })}
                  className="flex items-center px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600"
                >
                  Download PDF
                </button>
                {data.status === 'accepted' && (
                  <button
                    type="button"
                    onClick={handleConvertToOrder}
                    className="flex items-center px-4 py-2 text-white bg-green-500 rounded-md hover:bg-green-600"
                  >
                    Convert to Sales Order
                  </button>
                )}
              </div>

              {/* Totals Summary for View Mode */}
              <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-md">
                <h4 className="text-lg font-semibold mb-3 dark:text-white">Proposal Totals</h4>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                      ${(() => {
                        const total = lineItems.reduce((sum, item) => sum + (item.extended_price || 0), 0);
                        return total.toFixed(2);
                      })()}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Total Amount</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                      ${(() => {
                        const totalSell = lineItems.reduce((sum, item) => sum + ((item.price?.sell || 0) * (item.quantity || 0)), 0);
                        const totalCost = lineItems.reduce((sum, item) => sum + ((item.price?.cost || 0) * (item.quantity || 0)), 0);
                        const margin = totalSell - totalCost;
                        return margin.toFixed(2);
                      })()}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Total Margin</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                      {(() => {
                        const totalSell = lineItems.reduce((sum, item) => sum + ((item.price?.sell || 0) * (item.quantity || 0)), 0);
                        const totalCost = lineItems.reduce((sum, item) => sum + ((item.price?.cost || 0) * (item.quantity || 0)), 0);
                        const margin = totalSell - totalCost;
                        const percentage = totalSell > 0 ? (margin / totalSell) * 100 : 0;
                        return percentage.toFixed(1);
                      })()}%
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Margin %</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
                      {lineItems.length}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Line Items</div>
                  </div>
                </div>
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