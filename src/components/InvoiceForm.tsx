import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "./common/ComponentCard";
import Label from "./form/Label";
import { Input, Select, TextArea } from "./wrapper";

import { saveRecord, getRecord } from "../api/wcapi";
import { showToast } from "../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import staticLists from "../constants/staticLists";

const invoiceSchema = z.object({
  company: z.string().min(1, "Company is required"),
  attention: z.string().optional(),
  address1: z.string().min(1, "Address1 is required"),
  address2: z.string().optional(),
  city: z.string().min(1, "City is required"),
  state: z.string().optional(),
  zip: z.string().min(1, "Zip is required"),
  email: z.string().email("Invalid email").optional().or(z.literal("")),
  phone: z.string().optional(),
  phone_cell: z.string().optional(),
  action_by: z.string().optional(),
  action: z.string().optional(),
  action_date: z.string().optional(),
  action_time: z.string().optional(),
  sales_name: z.string().optional(),
  ordered_by: z.string().optional(),
  contract_detail_tag: z.string().optional(),
  terms: z.string().optional(),
  type_sale: z.string().optional(),
  tax_juris: z.string().optional(),
  ad_source: z.string().optional(),
  status: z.string().optional(),
  add_comment: z.string().optional(),
  comment: z.string().optional(),
  contract_detail: z.string().optional(),
});

interface InvoiceFormProps {
  modeProp?: 'add' | 'edit' | 'view';
  dataProp?: any;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export default function InvoiceForm({ modeProp, dataProp, onSaved, inline = false, onCancelInline }: InvoiceFormProps) {
  const dispatch = useDispatch();

  const { register, setValue, handleSubmit, formState: { errors }, reset } = useForm<z.infer<typeof invoiceSchema>>({
    resolver: zodResolver(invoiceSchema),
    defaultValues: {},
  });

  const mode: 'add' | 'edit' | 'view' = modeProp || 'add';
  const data = dataProp || null;

  useEffect(() => {
    if (mode === 'add') {
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
  }, [data, reset, setValue, mode]);

  const onSubmit = async (formData: z.infer<typeof invoiceSchema>) => {
    try {
      const payload = { ...formData, id: data?.id };
      const res = await saveRecord('invoice', payload);
      if (res) {
        dispatch(showToast({ message: `Invoice ${mode === 'add' ? 'saved' : 'updated'} successfully`, type: "success" }));
        if (onSaved) {
          onSaved();
        }
      }
    } catch (error: any) {
      dispatch(showToast({ message: error.message || "Failed to save invoice", type: "error" }));
    }
  };

  const stateOptions = [
    { value: "", label: "Select State" },
    ...staticLists.aStates.map(state => ({ value: state, label: state }))
  ];

  return (
    <ComponentCard>
      {inline && (
        <div className="flex justify-between items-center mb-4">
          <h3 className="dark:text-white text-lg font-semibold">
            {mode === 'edit' ? 'Edit Invoice' : mode === 'view' ? 'View Invoice' : 'Add New Invoice'}
          </h3>
          {onCancelInline && (
            <button type="button" onClick={onCancelInline} className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">&times;</button>
          )}
        </div>
      )}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label htmlFor="company">Company</Label>
            <Input
              type="text"
              id="company"
              placeholder="Company"
              {...register("company")}
              error={errors.company && errors.company.message ? true : false}
              hint={errors.company && errors.company.message}
              disabled={mode === 'view'}
            />
          </div>
          <div>
            <Label htmlFor="attention">Attention</Label>
            <Input
              type="text"
              id="attention"
              placeholder="Attention"
              {...register("attention")}
              disabled={mode === 'view'}
            />
          </div>
          <div>
            <Label htmlFor="address1">Address 1</Label>
            <Input
              type="text"
              id="address1"
              placeholder="Address 1"
              {...register("address1")}
              error={errors.address1 && errors.address1.message ? true : false}
              hint={errors.address1 && errors.address1.message}
              disabled={mode === 'view'}
            />
          </div>
          <div>
            <Label htmlFor="address2">Address 2</Label>
            <Input
              type="text"
              id="address2"
              placeholder="Address 2"
              {...register("address2")}
              disabled={mode === 'view'}
            />
          </div>
          <div>
            <Label htmlFor="city">City</Label>
            <Input
              type="text"
              id="city"
              placeholder="City"
              {...register("city")}
              error={errors.city && errors.city.message ? true : false}
              hint={errors.city && errors.city.message}
              disabled={mode === 'view'}
            />
          </div>
          <div>
            <Label htmlFor="state">State</Label>
            <Select
              options={stateOptions}
              placeholder="Select State"
              value={data?.state || ""}
              onChange={(value) => setValue("state", value)}
              className={mode === 'view' ? 'opacity-50 cursor-not-allowed' : ''}
            />
          </div>
          <div>
            <Label htmlFor="zip">Zip</Label>
            <Input
              type="text"
              id="zip"
              placeholder="Zip"
              {...register("zip")}
              error={errors.zip && errors.zip.message ? true : false}
              hint={errors.zip && errors.zip.message}
              disabled={mode === 'view'}
            />
          </div>
          <div>
            <Label htmlFor="email">Email</Label>
            <Input
              type="email"
              id="email"
              placeholder="Email"
              {...register("email")}
              error={errors.email && errors.email.message ? true : false}
              hint={errors.email && errors.email.message}
              disabled={mode === 'view'}
            />
          </div>
          <div>
            <Label htmlFor="phone">Phone</Label>
            <Input
              type="tel"
              id="phone"
              placeholder="Phone"
              {...register("phone")}
              disabled={mode === 'view'}
            />
          </div>
          <div>
            <Label htmlFor="phone_cell">Phone Cell</Label>
            <Input
              type="tel"
              id="phone_cell"
              placeholder="Phone Cell"
              {...register("phone_cell")}
              disabled={mode === 'view'}
            />
          </div>
        </div>
        <div>
          <Label htmlFor="comment">Comment</Label>
          <TextArea
            placeholder="Comment"
            register={register("comment")}
            disabled={mode === 'view'}
          />
        </div>
        {mode !== 'view' && (
          <div className="flex items-center gap-4">
            <button
              type="submit"
              className="flex items-center px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
            >
              {mode === 'edit' ? 'Update' : 'Submit'}
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
  );
}