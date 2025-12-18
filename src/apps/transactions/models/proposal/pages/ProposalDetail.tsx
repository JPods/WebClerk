import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input, TextArea } from "../../../../../components/wrapper";

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
  const [isNotesLocked, setIsNotesLocked] = useState(true);
  const [lineItems, setLineItems] = useState<any[]>([]);
  const [editingLineId, setEditingLineId] = useState<number | null>(null);
  const [newLine, setNewLine] = useState<any>({ item_id: undefined, item_name: '', description: '', quantity: 1, price: { sell: 0, cost: 0 }, discount_amount: 0 });

  type ProposalFormData = z.infer<typeof proposalSchema>;

  const defaultValues = useMemo(
    () => ({
      ida: "",
      status: "planned",
      priority: "",
      price_level: "",
      id_customer: undefined,
      id_manufacturer: undefined,
      id_vendor: undefined,
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
      salesNameId: "",
      orderedBy: "",
      contractDetailTag: "",
      terms: "",
      typeSale: "",
      taxJuris: "",
      adSource: "",
      addComment: "",
      comment: "",
      contractDetail: "",
    }),
    []
  );

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
    defaultValues,
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
      reset(defaultValues);
      setLineItems([]);
      setIsNotesLocked(true);
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
      setIsNotesLocked(true);
    } else {
      reset(defaultValues);
      setLineItems([]);
      setIsNotesLocked(true);
    }
  }, [data, defaultValues, reset, setValue, mode]);

  const onSubmit = async (formData: ProposalFormData) => {
    try {
      // Clean up the data - remove undefined and null values, but keep valid values
      const cleanData: any = {};
      Object.keys(formData).forEach(key => {
        const value = (formData as any)[key];
        if (value !== undefined && value !== null && value !== "") {
          cleanData[key] = value;
        }
      });

      if (formData.addComment) {
        const timestamp = new Date().toISOString();
        const existing = formData.comment ? `\n${formData.comment}` : "";
        cleanData.comment = `${timestamp}: ${formData.addComment}${existing}`;
      }
      delete cleanData.addComment;
      
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
                error={Boolean(errors.ida?.message)}
                hint={errors.ida?.message}
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

          {/* Contact & address (legacy Vue proposal form) */}
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
              <Label htmlFor="salesNameId">salesNameId</Label>
              <Input
                type="text"
                id="salesNameId"
                placeholder="Sales Name"
                {...register("salesNameId")}
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

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <Label htmlFor="priority">priority</Label>
              <Input
                type="text"
                id="priority"
                placeholder="Priority"
                {...register("priority")}
                error={Boolean(errors.priority?.message)}
                hint={errors.priority?.message}
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
                error={Boolean(errors.price_level?.message)}
                hint={errors.price_level?.message}
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
              error={errors.addComment as any}
              hint={errors.addComment?.message as string}
            />
          </div>

          <div className="flex items-center justify-between">
            <h4 className="text-lg font-semibold dark:text-white">Notes</h4>
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
                error={errors.comment as any}
                hint={errors.comment?.message as string}
              />
            </div>
            <div>
              <Label htmlFor="contractDetail">contractDetail</Label>
              <TextArea
                rows={4}
                placeholder="Contract Detail"
                register={register("contractDetail")}
                disabled={mode === "view" || isNotesLocked}
                error={errors.contractDetail as any}
                hint={errors.contractDetail?.message as string}
              />
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