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

const contactSchema = z.object({
  name_first: z.string().min(1, "First name is required"),
  name_last: z.string().min(1, "Last name is required"),
  company: z.string().optional(),
  email: z.string().email("Invalid email").optional().or(z.literal("")),
  phone: z.string().optional(),
  address1: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  zip: z.string().optional(),
  comment: z.string().optional(),
});

interface CustomerFormProps {
  modeProp?: 'add' | 'edit' | 'view';
  dataProp?: any;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export default function CustomerForm({ modeProp, dataProp, onSaved, inline = false, onCancelInline }: CustomerFormProps) {
  const dispatch = useDispatch();

  const { register, setValue, handleSubmit, formState: { errors }, reset } = useForm<z.infer<typeof contactSchema>>({
    resolver: zodResolver(contactSchema),
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

  const onSubmit = async (formData: z.infer<typeof contactSchema>) => {
    try {
      const payload = { ...formData, id: data?.id };
      const res = await saveRecord('contact', payload);
      if (res) {
        dispatch(showToast({ message: `Contact ${mode === 'add' ? 'saved' : 'updated'} successfully`, type: "success" }));
        if (onSaved) {
          onSaved();
        }
      }
    } catch (error: any) {
      dispatch(showToast({ message: error.message || "Failed to save contact", type: "error" }));
    }
  };

  const stateOptions = [
    { value: "", label: "Select State" },
    { value: "AL", label: "Alabama" },
    { value: "AK", label: "Alaska" },
    // Add more states as needed
  ];

  return (
    <ComponentCard>
      {inline && (
        <div className="flex justify-between items-center mb-4">
          <h3 className="dark:text-white text-lg font-semibold">
            {mode === 'edit' ? 'Edit Contact' : mode === 'view' ? 'View Contact' : 'Add New Contact'}
          </h3>
          {onCancelInline && (
            <button type="button" onClick={onCancelInline} className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">&times;</button>
          )}
        </div>
      )}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label htmlFor="name_first">First Name</Label>
            <Input
              type="text"
              id="name_first"
              placeholder="First Name"
              {...register("name_first")}
              error={errors.name_first && errors.name_first.message ? true : false}
              hint={errors.name_first && errors.name_first.message}
              disabled={mode === 'view'}
            />
          </div>
          <div>
            <Label htmlFor="name_last">Last Name</Label>
            <Input
              type="text"
              id="name_last"
              placeholder="Last Name"
              {...register("name_last")}
              error={errors.name_last && errors.name_last.message ? true : false}
              hint={errors.name_last && errors.name_last.message}
              disabled={mode === 'view'}
            />
          </div>
          <div>
            <Label htmlFor="company">Company</Label>
            <Input
              type="text"
              id="company"
              placeholder="Company"
              {...register("company")}
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
            <Label htmlFor="address1">Address 1</Label>
            <Input
              type="text"
              id="address1"
              placeholder="Address 1"
              {...register("address1")}
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