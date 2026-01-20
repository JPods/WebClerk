import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../../components/common/ComponentCard";
import Label from "../../../../../../components/form/Label";
import { Input } from "../../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import { showToast } from "../../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useParams } from "react-router";

// Simple customer schema - can be expanded as needed
const customerSchema = z.object({
  name_first: z.string().min(1, "First name is required"),
  name_last: z.string().min(1, "Last name is required"),
  company: z.string().optional(),
  email: z.string().email("Invalid email").optional().or(z.literal("")),
  phone: z.string().optional(),
});

type CustomerFormData = z.infer<typeof customerSchema>;

interface CustomerDetailProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: CustomerFormData;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export default function CustomerDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: CustomerDetailProps) {
  const dispatch = useDispatch();
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const routeState = (location.state as any) || {};
  const mode: "add" | "edit" | "view" = modeProp || (id ? "edit" : "add");
  const data = dataProp || routeState.data || null;

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<CustomerFormData>({
    resolver: zodResolver(customerSchema),
  });

  useEffect(() => {
    if (mode === "edit" && data) {
      reset(data);
    } else if (mode === "add") {
      reset();
    }
  }, [data, reset, mode]);

  const onSubmit = async (formData: CustomerFormData) => {
    try {
      // TODO: Implement actual API calls
      console.log("Customer data:", formData);

      dispatch(
        showToast({
          message: `Customer ${
            mode === "add" ? "created" : "updated"
          } successfully`,
          type: "success",
        })
      );

      if (onSaved) {
        onSaved();
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'An error occurred';
      dispatch(showToast({ message, type: "error" }));
    }
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Customer"
              : mode === "view"
              ? "View Customer"
              : "Customer Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Customer"
                : mode === "view"
                ? "View Customer"
                : "Add New Customer"}
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
              <Label htmlFor="name_first">First Name</Label>
              <Input
                type="text"
                id="name_first"
                placeholder="First Name"
                {...register("name_first")}
                error={errors.name_first && errors.name_first.message ? true : false}
                hint={errors.name_first && errors.name_first.message}
                disabled={mode === "view"}
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
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="company">Company</Label>
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
              <Label htmlFor="email">Email</Label>
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
              <Label htmlFor="phone">Phone</Label>
              <Input
                type="tel"
                id="phone"
                placeholder="Phone"
                {...register("phone")}
                error={errors.phone && errors.phone.message ? true : false}
                hint={errors.phone && errors.phone.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
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