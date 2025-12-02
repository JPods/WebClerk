import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import {
  Input,
  CustTextArea,
  DropDown,
} from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import {
  getByTypeAndId,
  patchAction,
  postAction,
} from "../../../../../api/userProfile";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useAppSelector } from "../../../../../store/hooks";
import { useLocation } from "react-router";
import { contactSchema } from "../utils/contactSchema";
import { ContactAddProps } from "../types/contactType";

export default function ActionAdd({
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
  } = useForm<z.infer<typeof contactSchema>>({
    resolver: zodResolver(contactSchema),
    defaultValues: {},
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

  const onSubmit = async (formData: z.infer<typeof contactSchema>) => {
    try {
      const res =
        mode === "add"
          ? await postAction(formData)
          : await patchAction(user?.name_first);
      if (res.status === 201 || res.status === 200) {
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
  const comment = { notes: [], public: "", partner: "", process: "" };
  const refs = {
    tags: [],
    links: { items: [], contacts: [] },
    keywords: [],
    categories: [],
    depends_on: {},
    related_ids: [],
  };
  const prefs = { userdefined: {} };
  const metadata = {
    flow: {},
    flags: { schema_rev: 1 },
    access: { edit: [], view: [] },
    health: {
      rating: 0,
      accuracy: 0,
      freshness: 0,
      consistency: 0,
      completeness: 0,
    },
    source: {},
    history: {
      synced: { dt: 0, contact_id: 0 },
      created: { dt: 1764077312019, contact_id: 0 },
      accessed: { dt: 1764077312019, contact_id: 0 },
      modified: { dt: 1764077312019, contact_id: 0 },
      verified: { dt: 0, contact_id: 0 },
    },
    publish: "",
    version: "1.0",
    priority: "",
    security: "",
    resources: { required: {}, allocated: {} },
    undefined: {},
    versioning: {},
  };

  const options = [
    { value: "website", label: "Website" },
    { value: "linkedin", label: "Linkedin" },
    { value: "facebook", label: "Facebook" },
    { value: "twitter", label: "Twitter" },
    { value: "github", label: "GitHub" },
    { value: "other", label: "Other" },
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
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="path">Path</Label>
              <Input
                type="text"
                id="path"
                placeholder="URL or handle (indexed)"
                {...register("path")}
                error={errors.path && errors.path.message ? true : false}
                hint={errors.path && errors.path.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="type">Type</Label>
              <DropDown
                id="type"
                options={options}
                placeholder="Select Option"
                {...register("type")}
                onChange={handleSelectChange}
                className="dark:bg-dark-900"
              />
            </div>
          </div>
          <h3 className=" dark:text-white text-lg font-semibold">
            Additional Information
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="comment">Comments</Label>
              <CustTextArea
                id="comment"
                placeholder="General notes"
                {...register("comment")}
                error={errors.comment && errors.comment.message ? true : false}
                hint={errors.comment && errors.comment.message}
                disabled={mode === "view"}
                value={JSON.stringify(comment, null, 2)}
              />
            </div>
            <div>
              <Label htmlFor="refs">Refs</Label>
              <CustTextArea
                id="refs"
                placeholder="General notes"
                {...register("refs")}
                error={errors.refs && errors.refs.message ? true : false}
                hint={errors.refs && errors.refs.message}
                disabled={mode === "view"}
                value={JSON.stringify(refs, null, 2)}
              />
            </div>
            <div>
              <Label htmlFor="prefs">Prefs</Label>
              <CustTextArea
                id="prefs"
                placeholder="Pprefs"
                {...register("prefs")}
                error={errors.prefs && errors.prefs.message ? true : false}
                hint={errors.prefs && errors.prefs.message}
                disabled={mode === "view"}
                value={JSON.stringify(prefs, null, 2)}
              />
            </div>
            <div>
              <Label htmlFor="metadata">Metadata</Label>
              <CustTextArea
                id="metadata"
                placeholder="Metadata"
                {...register("metadata")}
                error={
                  errors.metadata && errors.metadata.message ? true : false
                }
                hint={errors.metadata && errors.metadata.message}
                disabled={mode === "view"}
                value={JSON.stringify(metadata, null, 2)}
              />
            </div>
          </div>
          {mode !== "view" && (
            <div className="flex items-center gap-4">
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
