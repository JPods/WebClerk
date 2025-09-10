import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../components/common/ComponentCard";
import Label from "../../components/form/Label";
import { Input } from "../../components/wrapper";

import PageBreadcrumb from "../../components/common/PageBreadCrumb";

import { contactSchema } from "../../validations/action";
import { getByTypeAndId, patchAction, postAction } from "../../api/userProfile";
import { showToast } from "../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useAppSelector } from "../../store/hooks";
import { useLocation } from "react-router";

interface ContactAddProps {
  modeProp?: 'add' | 'edit' | 'view';
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export default function ContactAdd({ modeProp, dataProp, hideBreadcrumb, onSaved, inline = false, onCancelInline }: ContactAddProps) {
  
  const dispatch = useDispatch();
  const { user } = useAppSelector((state) => state.auth);

  const { register, setValue, handleSubmit, formState: { errors }, reset } = useForm<z.infer<typeof contactSchema>>({
    resolver: zodResolver(contactSchema),
    defaultValues: {},
  }); 
  
  const location = useLocation();
  const routeState = (location.state as any) || {};
  const mode: 'add' | 'edit' | 'view' = modeProp || routeState.mode || 'add';
  const data = dataProp || routeState.data || null;
  const [linkedLists, setLinkedLists] = useState<Record<string, any[]>>({});
   useEffect(() => {
    if (mode === 'add') {
      reset();
    } else if (data) {
      Object.keys(data).forEach((key: any) => {
        if (data[key] !== undefined) {
          setValue(key, data[key]);
        }
      });
      // Fetch linked lists by ids if present: data.refs.links
      const links = (data as any)?.refs?.links as Record<string, (string|number)[]> | undefined;
      if (links) {
        const fetchAll = async () => {
          const entries: Array<[string, any[]]> = await Promise.all(
            Object.entries(links).map(async ([key, ids]): Promise<[string, any[]]> => {
              if (!Array.isArray(ids) || ids.length === 0) return [key, []];
              // Fetch each id and flatten
              const results = await Promise.all(ids.map((id) => getByTypeAndId(key, id)));
              const flat = (results as any[]).flat().filter(Boolean) as any[];
              return [key, flat];
            })
          );
          const map: Record<string, any[]> = {};
          entries.forEach(([k, v]) => { map[k] = v; });
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
      const res = mode === 'add' ? await postAction(formData) : await patchAction(user?.name_first, formData);
      if (res.status === 201 || res.status === 200) {
        dispatch(showToast({ message: `Action ${mode === 'add' ? 'saved' : 'updated'} successfully`, type: "success" }));
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
      {!hideBreadcrumb && !inline && <PageBreadcrumb pageTitle={mode === 'edit' ? 'Edit Action' : mode === 'view' ? 'View Action' : 'Add Contact'} />}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className=" dark:text-white text-lg font-semibold">
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
              <Label htmlFor="FirstName">FirstName</Label>
              <Input
                type="text"
                id="FirstName"
                placeholder="First Name"
                {...register("name_first")}
                error={errors.name_first && errors.name_first.message ? true : false }
                hint={errors.name_first && errors.name_first.message}
                disabled={mode == 'view'}
              />
            </div>
            <div>
              <Label htmlFor="name_last">LastName</Label>
              <Input
                type="text"
                id="name_last"
                placeholder="Last Name"
                {...register("name_last")}
                error={errors.name_last && errors.name_last.message ? true : false }
                hint={errors.name_last && errors.name_last.message}
                disabled={mode == 'view'}
              />
            </div>

             <div>
              <Label htmlFor="name_middle">MiddleName</Label>
              <Input
                type="text"
                id="name_middle"
                placeholder="Middle Name"
                {...register("name_middle")}
                error={errors.name_middle && errors.name_middle.message ? true : false }
                hint={errors.name_middle && errors.name_middle.message}
                disabled={mode == 'view'}
              />
            </div>
              <div>
              <Label htmlFor="email">Email</Label>
              <Input
                type="email"
                id="email"
                placeholder="Email"
                {...register("email")}
                error={errors.email && errors.email.message ? true : false }
                hint={errors.email && errors.email.message}
                disabled={mode == 'view'}
              />
            </div>
            <div>
              <Label htmlFor="phone">Phone</Label>
              <Input
                type="tel"
                id="phone"
                placeholder="Phone"
                {...register("phone")}
                error={errors.phone && errors.phone.message ? true : false }
                hint={errors.phone && errors.phone.message}
                disabled={mode == 'view'}
              />
            </div>
              <div>
              <Label htmlFor="company">Company</Label>
              <Input
                type="text"
                id="company"
                placeholder="Company"
                {...register("company")}
                error={errors.company && errors.company.message ? true : false }
                hint={errors.company && errors.company.message}
                disabled={mode == 'view'}
              />
            </div>
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
        {/* Linked data lists */}
        {mode !== 'add' && (
          <div className="mt-6 space-y-4">
            {Object.keys(linkedLists).length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">No linked data.</p>
            ) : (
              Object.entries(linkedLists).map(([section, items]) => (
                <div key={section}>
                  <h4 className="text-md font-semibold capitalize dark:text-white mb-2">{section.split('_').join(' ')}</h4>
                  <ul className="text-sm divide-y divide-gray-200 dark:divide-gray-700 rounded-md overflow-hidden border border-gray-200 dark:border-gray-700">
                    {(items as any[]).map((item, idx) => (
                      <li key={idx} className="p-2 flex items-center justify-between">
                        <span className="truncate text-gray-500 dark:text-white">
                          {item?.data?.record?.name || item?.data?.record?.title || item?.data?.record?.email || item?.data?.record?.phone || item?.data?.record?.id}
                        </span>
                        <span className="text-gray-400 text-xs">ID: {item?.data?.record?.id}</span>
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

