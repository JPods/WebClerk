import { useEffect, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";
import InternationalPhoneInput from "@/components/form/input/InternationalPhoneInput";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";

// Simplified schema based on Vue component fields
const proposalVueSchema = z.object({
  company: z.string().min(1, "Company is required"),
  attention: z.string().min(1, "Attention is required"),
  address1: z.string().min(1, "Address1 is required"),
  address2: z.string().optional(),
  city: z.string().min(1, "City is required"),
  state: z.string().min(1, "State is required"),
  zip: z.string().min(1, "Zip is required"),
  email: z.string().email("Invalid email"),
  phoneCell: z.string().optional(),
  phone: z.string().optional(),
  actionBy: z.string().optional(),
  action: z.string().optional(),
  actionDate: z.string().optional(),
  actionTime: z.string().optional(),
  salesNameId: z.string().optional(),
  orderedBy: z.string().optional(),
  contractDetailTag: z.string().optional(),
  terms: z.string().optional(),
  typeSale: z.string().optional(),
  taxJuris: z.string().optional(),
  adSource: z.string().optional(),
  status: z.string().optional(),
  addComment: z.string().optional(),
  comment: z.string().optional(),
  contractDetail: z.string().optional(),
});

type ProposalVueFormData = z.infer<typeof proposalVueSchema>;

export default function ProposalDetailVue() {
  const dispatch = useDispatch();
  const [isDisabled, setIsDisabled] = useState(false);
  const [showHideEdit, setShowHideEdit] = useState("Edit");
  const [commentDisabled, setCommentDisabled] = useState(true);
  const [contractDetailDisabled, setContractDetailDisabled] = useState(true);

  const {
    register,
    control,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ProposalVueFormData>({
    resolver: zodResolver(proposalVueSchema),
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const mode: "add" | "edit" | "view" = routeState.mode || "add";
  const data = routeState.data || null;

  useEffect(() => {
    if (data) {
      Object.keys(data).forEach((key: any) => {
        if (data[key] !== undefined) {
          setValue(key, data[key]);
        }
      });
    } else {
      reset({});
    }
  }, [data, reset, setValue]);

  const onSubmit = async (formData: ProposalVueFormData) => {
    setIsDisabled(true);
    try {
      // Simulate API call - replace with actual API
      console.log("Updating proposal:", formData);
      dispatch(
        showToast({
          message: "Proposal updated successfully",
          type: "success",
        })
      );
    } catch (error: any) {
      dispatch(showToast({ message: error.message, type: "error" }));
    } finally {
      setIsDisabled(false);
    }
  };

  const handleEdit = () => {
    if (showHideEdit === "Lock") {
      setShowHideEdit("Edit");
      setCommentDisabled(true);
      setContractDetailDisabled(true);
    } else {
      setShowHideEdit("Lock");
      setCommentDisabled(false);
      setContractDetailDisabled(false);
    }
  };

  return (
    <>
      <PageBreadcrumb
        pageTitle="Proposal Detail Vue"
      />
      <ComponentCard>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Company and Attention */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <Label htmlFor="company">Company *</Label>
              <Input
                type="text"
                id="company"
                placeholder="Company"
                {...register("company")}
                error={errors.company && errors.company.message ? true : false}
                hint={errors.company && errors.company.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="attention">Attention *</Label>
              <Input
                type="text"
                id="attention"
                placeholder="Attention"
                {...register("attention")}
                error={errors.attention && errors.attention.message ? true : false}
                hint={errors.attention && errors.attention.message}
                disabled={mode === "view"}
              />
            </div>
          </div>

          {/* Address */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <Label htmlFor="address1">Address1 *</Label>
              <Input
                type="text"
                id="address1"
                placeholder="Address1"
                {...register("address1")}
                error={errors.address1 && errors.address1.message ? true : false}
                hint={errors.address1 && errors.address1.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="address2">Address2</Label>
              <Input
                type="text"
                id="address2"
                placeholder="Address2"
                {...register("address2")}
                disabled={mode === "view"}
              />
            </div>
          </div>

          {/* City, State, Zip */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <Label htmlFor="city">City *</Label>
              <Input
                type="text"
                id="city"
                placeholder="City"
                {...register("city")}
                error={errors.city && errors.city.message ? true : false}
                hint={errors.city && errors.city.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="state">State *</Label>
              <select
                id="state"
                {...register("state")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                <option value="">Select State</option>
                {/* Add state options here */}
                <option value="CA">California</option>
                <option value="TX">Texas</option>
                {/* etc. */}
              </select>
              {errors.state && <p className="text-red-500 text-sm">{errors.state.message}</p>}
            </div>
            <div>
              <Label htmlFor="zip">Zip *</Label>
              <Input
                type="text"
                id="zip"
                placeholder="Zip"
                {...register("zip")}
                error={errors.zip && errors.zip.message ? true : false}
                hint={errors.zip && errors.zip.message}
                disabled={mode === "view"}
              />
            </div>
          </div>

          {/* Email, Phone Cell, Phone */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <Label htmlFor="email">Email *</Label>
              <Input
                type="email"
                id="email"
                placeholder="Email"
                {...register("email")}
                error={errors.email && errors.email.message ? true : false}
                hint={errors.email && errors.email.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="phoneCell">Cell Phone</Label>
              <Controller
                name="phoneCell"
                control={control}
                render={({ field }) => (
                  <InternationalPhoneInput
                    id="phoneCell"
                    value={field.value ?? ""}
                    onBlur={field.onBlur}
                    onChange={field.onChange}
                    disabled={mode === "view"}
                    placeholder="Cell Phone"
                  />
                )}
              />
            </div>
            <div>
              <Label htmlFor="phone">Phone</Label>
              <Controller
                name="phone"
                control={control}
                render={({ field }) => (
                  <InternationalPhoneInput
                    id="phone"
                    value={field.value ?? ""}
                    onBlur={field.onBlur}
                    onChange={field.onChange}
                    disabled={mode === "view"}
                    placeholder="Phone"
                  />
                )}
              />
            </div>
          </div>

          {/* Action By, Action, Action Date, Action Time */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <Label htmlFor="actionBy">Action By</Label>
              <select
                id="actionBy"
                {...register("actionBy")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                <option value="">Select</option>
                {/* Add options */}
              </select>
            </div>
            <div>
              <Label htmlFor="action">Action</Label>
              <select
                id="action"
                {...register("action")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                <option value="">Select</option>
                {/* Add options */}
              </select>
            </div>
            <div>
              <Label htmlFor="actionDate">Action Date</Label>
              <Input
                type="date"
                id="actionDate"
                {...register("actionDate")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="actionTime">Action Time</Label>
              <Input
                type="time"
                id="actionTime"
                {...register("actionTime")}
                disabled={mode === "view"}
              />
            </div>
          </div>

          {/* Sales Name, Ordered By, Contract Detail Tag, Terms */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <Label htmlFor="salesNameId">Sales Name</Label>
              <select
                id="salesNameId"
                {...register("salesNameId")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                <option value="">Select</option>
                {/* Add options */}
              </select>
            </div>
            <div>
              <Label htmlFor="orderedBy">Ordered By</Label>
              <Input
                type="text"
                id="orderedBy"
                placeholder="Ordered By"
                {...register("orderedBy")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="contractDetailTag">Contract Detail</Label>
              <select
                id="contractDetailTag"
                {...register("contractDetailTag")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                <option value="">Select</option>
                {/* Add options */}
              </select>
            </div>
            <div>
              <Label htmlFor="terms">Terms</Label>
              <select
                id="terms"
                {...register("terms")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                <option value="">Select</option>
                {/* Add options */}
              </select>
            </div>
          </div>

          {/* Type Sale, Tax Juris, Ad Source, Status */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <Label htmlFor="typeSale">Type Sale</Label>
              <select
                id="typeSale"
                {...register("typeSale")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                <option value="">Select</option>
                {/* Add options */}
              </select>
            </div>
            <div>
              <Label htmlFor="taxJuris">Tax Juris</Label>
              <select
                id="taxJuris"
                {...register("taxJuris")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                <option value="">Select</option>
                {/* Add options */}
              </select>
            </div>
            <div>
              <Label htmlFor="adSource">Ad Source</Label>
              <select
                id="adSource"
                {...register("adSource")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                <option value="">Select</option>
                {/* Add options */}
              </select>
            </div>
            <div>
              <Label htmlFor="status">Status</Label>
              <select
                id="status"
                {...register("status")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                <option value="">Select</option>
                {/* Add options */}
              </select>
            </div>
          </div>

          {/* Add Comment */}
          <div>
            <Label htmlFor="addComment">Add Comment</Label>
            <textarea
              id="addComment"
              {...register("addComment")}
              disabled={mode === "view"}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              rows={3}
            />
          </div>

          {/* Comment */}
          <div>
            <Label htmlFor="comment">Comment</Label>
            <textarea
              id="comment"
              {...register("comment")}
              disabled={commentDisabled || mode === "view"}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              rows={3}
            />
          </div>

          {/* Contract Detail */}
          <div>
            <Label htmlFor="contractDetail">Contract Detail</Label>
            <textarea
              id="contractDetail"
              {...register("contractDetail")}
              disabled={contractDetailDisabled || mode === "view"}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              rows={3}
            />
          </div>

          {/* Buttons */}
          <div className="flex items-center gap-2">
            <button
              type="submit"
              disabled={isDisabled}
              className="flex items-center px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
            >
              Update
            </button>
            <button
              type="button"
              onClick={handleEdit}
              className="flex items-center px-4 py-2 text-white bg-gray-500 rounded-md hover:bg-gray-600"
            >
              {showHideEdit}
            </button>
          </div>
        </form>
      </ComponentCard>
    </>
  );
}