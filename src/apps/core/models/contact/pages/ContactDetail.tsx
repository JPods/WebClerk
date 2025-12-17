import { useEffect, useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import Select from "react-select";
import { FaPlus, FaTrash } from "react-icons/fa";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";

import ComponentCard from "../../../../../components/common/ComponentCard";
import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";

import { contactSchema, updateContactSchema } from "../utils/contactSchema";
import { createContact, updateContact } from "../services/contactApi";
import { fetchEmails } from "@/apps/communications/models/email/services/emailApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { ContactAddProps } from "../types/contactType";
import Checkbox from "@/components/form/input/Checkbox";
import Label from "../../../../../components/form/Label";
import Input from "../../../../../components/form/input/InputField";
import DropDown from "../../../../../components/form/input/DropDown";
/* ----------------------------------
   Types
---------------------------------- */
type EmailRecord = {
  id: number;
  name: string;
  email: string;
};

type EmailOption = {
  value: number;
  label: string;
  raw: {
    id: number;
    name: string;
    address: string;
  };
};

export default function ContactDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
}: ContactAddProps) {
  const dispatch = useDispatch();
  const location = useLocation();
  const routeState = (location.state as any) || {};

  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;
  const [linkedLists, setLinkedLists] = useState<Record<string, any[]>>({});
  const [selectedValues, setSelectedValues] = useState<string[]>([]);
  const [emailOptions, setEmailOptions] = useState<EmailOption[]>([]);
  const [selectedEmails, setSelectedEmails] = useState<EmailOption[]>([]);

  /* ----------------------------------
     React Hook Form
  ---------------------------------- */
  const {
    register,
    control,
    handleSubmit,
    setValue,
    getValues,
    reset,
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
          email: [], // OBJECTS
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
     Watch linked emails (OBJECTS)
  ---------------------------------- */
  const linkedEmails = useWatch({
    control,
    name: "refs.links.email",
  });

  /* ----------------------------------
     Load edit data
  ---------------------------------- */
  // useEffect(() => {
  //   if (data?.refs) {
  //     setValue("refs", data.refs);
  //   }
  // }, [data, setValue]);

  useEffect(() => {
    if (mode === "add") {
      reset();
      if (data?.refs) {
        setValue("refs", data.refs);
      }
    } else if (data) {
      Object.keys(data).forEach((key: any) => {
        if (data[key] !== undefined) {
          setValue(key, data[key]);
        }
      });
      if (data?.refs) {
        setValue("refs", data.refs);
      }
      // Fetch linked lists by ids if present: data.refs.links
      // Commented out as linked data is not displayed
    } else {
      reset({});
      setLinkedLists({});
    }

    if (mode === "edit") {
      setValue("password", "");
      setValue("cnf_password", "");
    }
  }, [data, reset, setValue, mode]);

  /* ----------------------------------
     Fetch emails
  ---------------------------------- */
  useEffect(() => {
    (async () => {
      const res = await fetchEmails();
      if (res?.status === 200) {
        const results = res.data.data.results as EmailRecord[];
        setEmailOptions(
          results
            .map((e) => ({
              value: e.id,
              label: e.email && `${e.email} (${e.name})`,
              raw: {
                id: e.id,
                name: e.name,
                address: e.email || "",
              },
            }))
            .filter((item: { label: string }) => item.label.trim() !== "")
        );
      }
    })();
  }, []);

  /* ----------------------------------
     Add emails (OBJECT BASED)
  ---------------------------------- */
  const addEmails = () => {
    const selected = selectedEmails.map((e) => e.raw);
    const current = getValues("refs.links.email") || [];

    const merged = [
      ...current,
      ...selected.filter((s) => !current.some((c: any) => c.id === s.id)),
    ];

    setValue("refs.links.email", merged);
    setSelectedEmails([]);
  };
  console.log("getValues", getValues("refs.links.email") || []);
  /* ----------------------------------
     Remove email
  ---------------------------------- */
  const removeEmail = (id: number) => {
    setValue(
      "refs.links.email",
      linkedEmails?.filter((e: any) => e.id !== id)
    );
  };

  /* ----------------------------------
     Submit
  ---------------------------------- */
  const onSubmit = async (formData: any) => {
    try {
      const res =
        mode === "add"
          ? await createContact(formData)
          : await updateContact({ ...formData, id: data.id });

      dispatch(
        showToast({
          message: `Contact ${
            mode === "add" ? "created" : "updated"
          } successfully`,
          type: "success",
        })
      );

      onSaved?.();
    } catch (e: any) {
      dispatch(showToast({ message: e.message, type: "error" }));
    }
  };
  const options = [
    { value: "user", label: "User" },
    { value: "admin", label: "Administrator" },
    { value: "manager", label: "Manager" },
    { value: "staff", label: "Staff" },
    { value: "guest", label: "Guest" },
  ];
  return (
    <>
      {!hideBreadcrumb && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Contact"
              : mode === "view"
              ? "View Contact"
              : "Add Contact"
          }
        />
      )}

      <ComponentCard>
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
                    options={options}
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

          {/* SELECT */}
          <div>
            <Label htmlFor="ref_email">Ref Email</Label>
            <div className="flex items-center gap-2">
              <div className="flex-1">
                <Select
                  id="ref_email"
                  isMulti
                  options={emailOptions}
                  value={selectedEmails}
                  onChange={(v) => setSelectedEmails(v as EmailOption[])}
                  placeholder="Select email(s)"
                />
              </div>

              <button
                type="button"
                onClick={addEmails}
                className="h-[38px] w-[38px] flex items-center justify-center
                         border rounded-md hover:text-blue-600"
              >
                <FaPlus />
              </button>
            </div>
          </div>

          {/* LINKED EMAILS */}
          {linkedEmails?.map((email: any) => (
            <div
              key={email.id}
              className="flex justify-between items-center text-blue-500"
            >
              <span>{email.address}</span>
              <span>{email.name}</span>

              <button type="button" onClick={() => removeEmail(email.id)}>
                <FaTrash className="text-red-600 hover:scale-110 transition" />
              </button>
            </div>
          ))}

          {/* SUBMIT */}
          {mode !== "view" && (
            <button
              type="submit"
              className="px-4 py-2 bg-blue-500 text-white rounded"
            >
              {mode === "edit" ? "Update" : "Submit"}
            </button>
          )}
        </form>
      </ComponentCard>
    </>
  );
}
