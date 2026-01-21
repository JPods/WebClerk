import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createCustomer, updateCustomer } from "../services/customerApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { customerSchema } from "../utils/customerSchema";
import { CustomerAddProps } from "../types/customerType";
import Checkbox from "@/components/form/input/Checkbox";


// Dashboard-style containers for modular customer view
import React from "react";
function ScalarData({ data }: { data: any }) {
  // Scalar fields (alphabetical): company, display_name, id, is_active, status, version, dt_created, dt_modified
  // Object fields (alphabetical): contacts, data, domains, emails, financial, locations, phones, relations
  if (!data) return <section><h3>Customer Data</h3><div>No data</div></section>;
  const scalarFields = [
    "company",
    "display_name",
    "id",
    "is_active",
    "status",
    "version",
    "dt_created",
    "dt_modified",
  ];
  const objectFields = [
    "contacts",
    "data",
    "domains",
    "emails",
    "financial",
    "locations",
    "phones",
    "relations",
  ];
  return (
    <section>
      <h3>Customer Data</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        <div>
          <h4 className="font-semibold mb-1">Scalars</h4>
          <ul className="text-sm">
            {scalarFields.map((field) => (
              <li key={field}>
                <span className="font-mono text-gray-700 dark:text-gray-200">{field}:</span> {String(data[field] ?? "")} 
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h4 className="font-semibold mb-1">Objects</h4>
          <ul className="text-sm">
            {objectFields.map((field) => (
              <li key={field}>
                <span className="font-mono text-gray-700 dark:text-gray-200">{field}:</span>
                <pre className="bg-gray-100 dark:bg-gray-800 rounded p-2 overflow-x-auto text-xs">
                  {JSON.stringify(data[field], null, 2)}
                </pre>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
function ContactContainer() {
  // TODO: Add/Edit email, phone, domain, address
  return <section><h3>Contact Information</h3></section>;
}
function BusinessObjects() {
  // TODO: Proposals, Orders, Invoices, Payments, Ledgers, Projects
  return <section><h3>Proposals, Orders, Invoices, Payments, Ledgers, Projects</h3></section>;
}
function CommentsContainer() {
  // TODO: View/Add comments
  return <section><h3>Comments</h3></section>;
}
function PrefsContainer() {
  // TODO: View/Edit .prefs
  return <section><h3>Preferences</h3></section>;
}
function ActionsContainer() {
  // TODO: View/Edit actions
  return <section><h3>Actions</h3></section>;
}
function LinkageContainer() {
  // TODO: View/Edit linkage
  return <section><h3>Linkage</h3></section>;
}
function DocumentContainer() {
  // TODO: View/Edit documents
  return <section><h3>Documents</h3></section>;
}
function QAContainer() {
  // TODO: View/Edit question_answer
  return <section><h3>Q&A</h3></section>;
}
function TagContainer() {
  // TODO: View/Edit tags
  return <section><h3>Tags</h3></section>;
}
function ProductsContainer() {
  // TODO: View/Edit products/serials
  return <section><h3>Products/Serials</h3></section>;
}
function RelationshipsContainer() {
  // TODO: Vendor, Manufacturer, Rep, Employee
  return <section><h3>Relationships</h3></section>;
}
function CatalogsContainer() {
  // TODO: View/Edit catalogs
  return <section><h3>Catalogs</h3></section>;
}
function CampaignsContainer() {
  // TODO: View/Edit campaigns
  return <section><h3>Campaigns</h3></section>;
}

export default function CustomerDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: CustomerAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
    control,
  } = useForm<z.infer<typeof customerSchema>>({
    resolver: zodResolver(customerSchema),
    defaultValues: { is_active: false, version: 1, org_type: "customer" },
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;
  useEffect(() => {
    if (mode === "add") {
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
  console.log("errors", errors);
  const onSubmit = async (formData: z.infer<typeof customerSchema>) => {
    console.log("formData", formData);
    try {
      const res =
        mode === "add"
          ? await createCustomer(formData)
          : await updateCustomer({ ...formData, id: data && data.id });
      if (res) {
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
      }
    } catch (error: any) {
      dispatch(showToast({ message: error.message, type: "error" }));
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
        {/* Dashboard containers for customer context */}
        <ScalarData data={data} />
        <ContactContainer />
        <BusinessObjects />
        <CommentsContainer />
        <PrefsContainer />
        <ActionsContainer />
        <LinkageContainer />
        <DocumentContainer />
        <QAContainer />
        <TagContainer />
        <ProductsContainer />
        <RelationshipsContainer />
        <CatalogsContainer />
        <CampaignsContainer />
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
        {/* ...existing customer form and logic... */}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-1 gap-4">
            <div>
              <Label htmlFor="display_name">display_name</Label>
              <Input
                type="text"
                id="display_name"
                placeholder="Display Name"
                {...register("display_name")}
                error={
                  errors.display_name && errors.display_name.message
                    ? true
                    : false
                }
                hint={errors.display_name && errors.display_name.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="status">status</Label>
              <Input
                type="text"
                id="status"
                placeholder="status"
                {...register("status")}
                error={errors.status && errors.status.message ? true : false}
                hint={errors.status && errors.status.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Controller
                name="is_active"
                control={control}
                render={({ field }) => (
                  <Checkbox
                    id="is_active"
                    checked={field.value ?? false}
                    onChange={field.onChange}
                    label="is_active"
                  />
                )}
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
