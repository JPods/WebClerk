import { useEffect, useState } from "react";
import { Controller, useForm, useFieldArray, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import Input from "../../../../../components/form/input/InputField";
import DropDown from "../../../../../components/form/input/DropDown";
import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createContact, updateContact } from "../services/contactApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import {
  contactSchema,
  updateContactSchema,
  mapRefsFormToApi,
} from "../utils/contactSchema";
import {
  ContactAddProps,
  CreateContactRequest,
  UpdateContactRequest,
} from "../types/contactType";
import Checkbox from "../../../../../components/form/input/Checkbox";
import { FaEdit, FaEye, FaPlus, FaTrash } from "react-icons/fa";

/* ----------------------------------
   Types
---------------------------------- */

export default function ContactDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ContactAddProps) {
  const [isEmailEdit, setIsEmailEdit] = useState<boolean>(false);

  const dispatch = useDispatch();
  const location = useLocation();
  const routeState = (location.state as any) || {};

  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;

  /* ----------------------------------
     React Hook Form
  ---------------------------------- */
  const {
    register,
    control,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(
      mode === "edit" ? updateContactSchema : contactSchema
    ),
    defaultValues: {
      refs: {
        tags: [],
        categories: [],
        keywords: [],
        depends_on: {},
        related_ids: [],
        links: {
          rep: [],
          item: [],
          email: [],
          order: [],
          phone: [],
          domain: [],
          contact: [],
          customer: [],
          document: [],
          location: [],
          manufacturer: [],
          project: [],
          vendor: [],
        },
      },
    },
  });

  /* ----------------------------------
     Field Array for Emails
  ---------------------------------- */
  const {
    fields: emailFields,
    append: appendEmail,
    remove: removeEmail,
  } = useFieldArray({
    control,
    name: "refs.links.email",
  });
  console.log("emailFields", emailFields, emailFields.length);
  /* ----------------------------------
     Load Edit Data
  ---------------------------------- */

  useEffect(() => {
    if (mode === "add") {
      reset();
      if (data?.refs) {
        reset({ refs: data.refs });
      }
    } else if (data) {
      reset(data);
      if (data?.refs) {
        reset({ ...data, refs: data.refs });
      }
      // Fetch linked lists by ids if present: data.refs.links
      // Commented out as linked data is not displayed
    } else {
      reset({});
    }
    if (mode === "edit") {
      setValue("password", "");
      setValue("cnf_password", "");
    }
  }, [data, reset, setValue, mode]);
  useEffect(() => {
    setIsEmailEdit(false);
  }, [data]);

  /* ----------------------------------
     Submit
  ---------------------------------- */
  console.log("errors", errors);

  const onSubmit = async (
    formData:
      | z.infer<typeof contactSchema>
      | z.infer<typeof updateContactSchema>
  ) => {
    console.log("formData", formData);
    try {
      const mappedRefs = formData.refs
        ? mapRefsFormToApi(formData.refs)
        : undefined;
      const payload = {
        email: formData.email,
        name_first: formData.name_first,
        name_last: formData.name_last,
        name_middle: formData.name_middle,
        name_prefix: formData.name_prefix,
        name_suffix: formData.name_suffix,
        company: formData.company,
        title: formData.title,
        department: formData.department,
        role: formData.role,
        is_active: formData.is_active,
        is_staff: formData.is_staff,
        refs: mappedRefs,
        ...(mode === "add" || mode === "edit"
          ? {
              password: formData.password,
              cnf_password: formData.cnf_password,
            }
          : {}),
      };

      const res =
        mode === "add"
          ? await createContact(payload as CreateContactRequest)
          : await updateContact({
              ...payload,
              id: data?.id,
            } as UpdateContactRequest);
      if (res) {
        dispatch(
          showToast({
            message: `Action ${
              mode === "add" ? "saved" : "updated"
            } successfully`,
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        }
      }
    } catch (error: unknown) {
      if (error instanceof Error) {
        dispatch(showToast({ message: error.message, type: "error" }));
      }
    }
  };

  const roleOptions = [
    { value: "user", label: "User" },
    { value: "admin", label: "Administrator" },
    { value: "manager", label: "Manager" },
    { value: "staff", label: "Staff" },
    { value: "guest", label: "Guest" },
  ];
  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Contact"
              : mode === "view"
              ? "View Contact"
              : "Contact Detail"
          }
        />
      )}

      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className=" dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Contact"
                : mode === "view"
                ? "View Contact"
                : "Add New Contact"}
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
          <h5 className=" dark:text-white text-md font-semibold">
            After you’ve created a user, you’ll be able to edit more user
            options.
          </h5>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Label htmlFor="email">email</Label>
              <Input
                type="email"
                id="email"
                placeholder="Primary email address for login"
                {...register("email")}
                error={errors.email && errors.email.message ? true : false}
                hint={errors.email && errors.email.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          {(mode === "add" || mode === "edit") && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                <div>
                  <Label htmlFor="password">password</Label>
                  <Input
                    type="password"
                    id="password"
                    placeholder="Password"
                    {...register("password")}
                    error={
                      errors.password && errors.password.message ? true : false
                    }
                    hint={
                      errors.password?.message ||
                      "Your password can't be too similar to your other personal information. Your password must contain at least 8 characters. Your password can't be a commonly used password. Your password can't be entirely numeric."
                    }
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                <div>
                  <Label htmlFor="cnf_password">cnf_password</Label>
                  <Input
                    type="password"
                    id="cnf_password"
                    placeholder="Confirm Password"
                    {...register("cnf_password")}
                    error={
                      errors.cnf_password && errors.cnf_password.message
                        ? true
                        : false
                    }
                    hint={
                      errors.cnf_password?.message ||
                      "Enter the same password as before, for verification."
                    }
                  />
                </div>
              </div>
            </>
          )}
          <h5 className=" dark:text-white text-md font-semibold">
            Personal info
          </h5>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Label htmlFor="name_first">name_first</Label>
              <Input
                type="text"
                id="name_first"
                placeholder="First Name"
                {...register("name_first")}
                error={
                  errors.name_first && errors.name_first.message ? true : false
                }
                hint={errors.name_first && errors.name_first.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="name_last">name_last</Label>
              <Input
                type="text"
                id="name_last"
                placeholder="Last Name"
                {...register("name_last")}
                error={
                  errors.name_last && errors.name_last.message ? true : false
                }
                hint={errors.name_last && errors.name_last.message}
                disabled={mode === "view"}
              />
            </div>

            <div>
              <Label htmlFor="name_middle">name_middle</Label>
              <Input
                type="text"
                id="name_middle"
                placeholder="Middle Name"
                {...register("name_middle")}
                error={
                  errors.name_middle && errors.name_middle.message
                    ? true
                    : false
                }
                hint={errors.name_middle && errors.name_middle.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="name_prefix">name_prefix</Label>
              <Input
                type="text"
                id="name_prefix"
                placeholder="Title (Mr., Ms., Dr.)"
                {...register("name_prefix")}
                error={
                  errors.name_prefix && errors.name_prefix.message
                    ? true
                    : false
                }
                hint={errors.name_prefix && errors.name_prefix.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="name_suffix">name_suffix</Label>
              <Input
                type="text"
                id="name_suffix"
                placeholder="Suffix (Jr., Sr., III)"
                {...register("name_suffix")}
                error={
                  errors.name_suffix && errors.name_suffix.message
                    ? true
                    : false
                }
                hint={errors.name_suffix && errors.name_suffix.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <h5 className=" dark:text-white text-md font-semibold">
            Company info
          </h5>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Label htmlFor="company">company</Label>
              <Input
                type="text"
                id="company"
                placeholder="Company name"
                {...register("company")}
                error={errors.company && errors.company.message ? true : false}
                hint={errors.company && errors.company.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="title">title</Label>
              <Input
                type="text"
                id="title"
                placeholder="Job title"
                {...register("title")}
                error={errors.title && errors.title.message ? true : false}
                hint={errors.title && errors.title.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="department">department</Label>
              <Input
                type="text"
                id="department"
                placeholder="Department"
                {...register("department")}
                error={
                  errors.department && errors.department.message ? true : false
                }
                hint={errors.department && errors.department.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <h5 className=" dark:text-white text-md font-semibold">
            Permissions
          </h5>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Label htmlFor="role">role</Label>
              <Controller
                name="role"
                control={control}
                render={({ field }) => (
                  <DropDown
                    id="role"
                    options={roleOptions}
                    placeholder="Select Role"
                    value={field.value}
                    onChange={field.onChange}
                    className="dark:bg-dark-900"
                    disabled={mode === "view"}
                  />
                )}
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
                    label="Is Active"
                  />
                )}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Controller
                name="is_staff"
                control={control}
                render={({ field }) => (
                  <Checkbox
                    id="is_staff"
                    checked={field.value ?? false}
                    onChange={field.onChange}
                    label="Is Staff"
                  />
                )}
              />
            </div>
          </div>

          <h5 className="font-semibold">Contact Ref. Link</h5>

          {/* ----------------------------------
              LINKED EMAILS
          ---------------------------------- */}
          <div className="flex items-center justify-between mb-1">
            <div className="flex-2/3 me-2">
              <Label>model_name: email</Label>
            </div>

            {mode !== "view" && (
              <div className="flex items-end gap-2">
                <button
                  type="button"
                  className="h-[38px] w-[38px] flex items-center justify-center
                         border rounded-md hover:text-success-600"
                  onClick={() => {
                    setIsEmailEdit(true);
                    appendEmail({ id: 0, name: "", address: "" });
                  }}
                >
                  <FaPlus className="text-success-600 hover:scale-110" />
                </button>
                {emailFields.length && isEmailEdit ? (
                  <button
                    type="button"
                    className="h-[38px] w-[38px] flex items-center justify-center
                         border rounded-md hover:text-blue-600"
                    onClick={() => {
                      setIsEmailEdit(false);
                    }}
                  >
                    <FaEye className="text-blue-600 hover:scale-110" />
                  </button>
                ) : (
                  <button
                    type="button"
                    className="h-[38px] w-[38px] flex items-center justify-center
                         border rounded-md hover:text-blue-600"
                    onClick={() => {
                      setIsEmailEdit(true);
                    }}
                  >
                    <FaEdit className="text-blue-600 hover:scale-110" />
                  </button>
                )}
              </div>
            )}
          </div>
          {emailFields.length && isEmailEdit ? (
            <div className="gap-4 p-3 border rounded-md bg-gray-50 dark:bg-dark-800">
              {emailFields.map((field, index) => (
                <div
                  key={field.id}
                  className="flex items-center justify-between py-2"
                >
                  <div className="flex-2/3 me-2">
                    <Label htmlFor={`refs.links.email.${index}.address`}>
                      address (.ref)
                    </Label>
                    <Input
                      type="text"
                      id={`refs.links.email.${index}.address`}
                      {...register(`refs.links.email.${index}.address`)}
                      disabled={mode === "view"}
                    />
                  </div>

                  <div className="flex-1/3">
                    <Label htmlFor={`refs.links.email.${index}.name`}>
                      name (.ref)
                    </Label>
                    <Input
                      type="text"
                      id={`refs.links.email.${index}.name`}
                      {...register(`refs.links.email.${index}.name`)}
                      disabled={mode === "view"}
                    />
                  </div>

                  {mode !== "view" && (
                    <div className="flex items-end">
                      <button
                        type="button"
                        onClick={() => removeEmail(index)}
                        className="p-2 text-red-600"
                      >
                        <FaTrash />
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <>
              {emailFields.length ? (
                <div className="gap-4 p-3 border rounded-md bg-gray-50 dark:bg-dark-800">
                  {emailFields.map((field, index) => (
                    <div
                      key={field.id}
                      className="flex items-center justify-between py-2 border-b-2"
                    >
                      <div className="flex-2/3 me-2">
                        <Label htmlFor={`refs.links.email.${index}.address`}>
                          address (.ref)
                        </Label>
                        <h1>{field.address}</h1>
                      </div>

                      <div className="flex-1/3">
                        <Label htmlFor={`refs.links.email.${index}.name`}>
                          name (.ref)
                        </Label>
                        <h1>{field.name}</h1>
                      </div>

                      {mode !== "view" && (
                        <div className="flex items-end">
                          <button
                            type="button"
                            onClick={() => removeEmail(index)}
                            className="p-2 text-red-600"
                          >
                            <FaTrash />
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p>No email record found!</p>
              )}
            </>
          )}
          {/* SUBMIT */}
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
