import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input, DropDown } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import {
  getByTypeAndId,
  patchAction,
  postAction,
} from "../../../../../api/userProfile";
import { createContact } from "../services/contactApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useAppSelector } from "../../../../../store/hooks";
import { useLocation } from "react-router";
import { contactSchema } from "../utils/contactSchema";
import { ContactAddProps } from "../types/contactType";
import Checkbox from "../../../../../components/form/input/Checkbox";

export default function ContactAdd({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ContactAddProps) {
  const dispatch = useDispatch();
  const { user } = useAppSelector((state) => state.auth);

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<z.infer<typeof contactSchema>>({
    resolver: zodResolver(contactSchema),
    defaultValues: { is_staff: false, is_active: false },
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;
  const [linkedLists, setLinkedLists] = useState<Record<string, any[]>>({});
  useEffect(() => {
    if (mode === "add") {
      reset();
    } else if (data) {
      Object.keys(data).forEach((key: any) => {
        if (data[key] !== undefined) {
          setValue(key, data[key]);
        }
      });
      // Fetch linked lists by ids if present: data.refs.links
      const links = (data as any)?.refs?.links as
        | Record<string, (string | number)[]>
        | undefined;
      if (links) {
        const fetchAll = async () => {
          const entries: Array<[string, any[]]> = await Promise.all(
            Object.entries(links).map(
              async ([key, ids]): Promise<[string, any[]]> => {
                if (!Array.isArray(ids) || ids.length === 0) return [key, []];
                // Fetch each id and flatten
                const results = await Promise.all(
                  ids.map((id) => getByTypeAndId(key, id))
                );
                const flat = (results as any[]).flat().filter(Boolean) as any[];
                return [key, flat];
              }
            )
          );
          const map: Record<string, any[]> = {};
          entries.forEach(([k, v]) => {
            map[k] = v;
          });
          setLinkedLists(map);
        };
        fetchAll();
      } else {
        setLinkedLists({});
      }
    } else {
      reset({});
      setLinkedLists({});
    }
  }, [data, reset, setValue, mode]);
  console.log("errors", errors);
  const onSubmit = async (formData: z.infer<typeof contactSchema>) => {
    console.log("formData", formData);
    try {
      const res = mode === "add" ? await createContact(formData) : "";
      //: await patchAction(user?.name_first);
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
    } catch (error: any) {
      dispatch(showToast({ message: error.message, type: "error" }));
    }
  };

  const options = [
    { value: "user", label: "User" },
    { value: "admin", label: "Administrator" },
    { value: "manager", label: "Manager" },
    { value: "staff", label: "Staff" },
    { value: "guest", label: "Guest" },
  ];

  const handleSelectChange = (value: string) => {
    console.log("Selected value:", value);
  };
  return (
    <>
      {!hideBreadcrumb && !inline && (
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
              <Label htmlFor="email">Email</Label>
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Label htmlFor="password">Password</Label>
              <Input
                type="password"
                id="password"
                placeholder="Password"
                {...register("password")}
                error={
                  errors.password && errors.password.message ? true : false
                }
                hint={
                  "Your password can’t be too similar to your other personal information. Your password must contain at least 8 characters.  Your password can’t be a commonly used password. Your password can’t be entirely numeric."
                }
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Label htmlFor="cnf_password">Confirm Password</Label>
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
                  (errors.cnf_password && errors.cnf_password.message) ||
                  "Enter the same password as before, for verification."
                }
                disabled={mode === "view"}
              />
            </div>
          </div>
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
              <DropDown
                id="role"
                options={options}
                placeholder="Select Role"
                {...register("role")}
                onChange={handleSelectChange}
                className="dark:bg-dark-900"
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Checkbox
                id="is_active"
                checked={watch("is_active")}
                onChange={(checked) => setValue("is_active", checked)}
                label="Is Active"
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <Checkbox
                id="is_staff"
                checked={watch("is_staff")}
                onChange={(checked) => setValue("is_staff", checked)}
                label="Is Staff"
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
        {/* Linked data lists */}
        {mode !== "add" && (
          <div className="mt-6 space-y-4">
            {Object.keys(linkedLists).length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No linked data.
              </p>
            ) : (
              Object.entries(linkedLists).map(([section, items]) => (
                <div key={section}>
                  <h4 className="text-md font-semibold capitalize dark:text-white mb-2">
                    {section.split("_").join(" ")}
                  </h4>
                  <ul className="text-sm divide-y divide-gray-200 dark:divide-gray-700 rounded-md overflow-hidden border border-gray-200 dark:border-gray-700">
                    {(items as any[]).map((item, idx) => (
                      <li
                        key={idx}
                        className="p-2 flex items-center justify-between"
                      >
                        <span className="truncate text-gray-500 dark:text-white">
                          {item?.data?.record?.name ||
                            item?.data?.record?.title ||
                            item?.data?.record?.email ||
                            item?.data?.record?.phone ||
                            item?.data?.record?.id}
                        </span>
                        <span className="text-gray-400 text-xs">
                          ID: {item?.data?.record?.id}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))
            )}
          </div>
        )}
      </ComponentCard>
    </>
  );
}
