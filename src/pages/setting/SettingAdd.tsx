import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../components/common/ComponentCard";
import Label from "../../components/form/Label";
import { Input, TextArea } from "../../components/wrapper";

import PageBreadcrumb from "../../components/common/PageBreadCrumb";

import { actionSchema, contactSchema } from "../../validations/action";
import { patchAction, postAction } from "../../api/userProfile";
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

export default function SettingAdd({ modeProp, dataProp, hideBreadcrumb, onSaved, inline = false, onCancelInline }: ContactAddProps) {
  
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
      {!hideBreadcrumb && !inline && <PageBreadcrumb pageTitle={mode === 'edit' ? 'Edit Setting' : mode === 'view' ? 'View Setting' : 'Add Setting'} />}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className=" dark:text-white text-lg font-semibold">
              {mode === 'edit' ? 'Edit Setting' : mode === 'view' ? 'View Setting' : 'Add New Setting'}
            </h3>
            {onCancelInline && (
              <button type="button" onClick={onCancelInline} className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">&times;</button>
            )}
          </div>
        )}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="name_first">name_first</Label>
              <Input
                type="text"
                id="name_first"
                placeholder="name_first"
                {...register("name_first")}
                error={errors.name_first && errors.name_first.message ? true : false }
                hint={errors.name_first && errors.name_first.message}
                disabled={mode === 'view'}
              />
            </div>
            <div>
              <Label htmlFor="name_last">name_last</Label>
              <Input
                type="text"
                id="name_last"
                placeholder="name_last"
                {...register("name_last")}
                error={errors.name_last && errors.name_last.message ? true : false }
                hint={errors.name_last && errors.name_last.message}
                disabled={mode === 'view'}
              />
            </div>

            <div>
              <Label htmlFor="name_middle">name_middle</Label>
              <Input
                type="text"
                id="name_middle"
                placeholder="name_middle"
                {...register("name_middle")}
                error={errors.name_middle && errors.name_middle.message ? true : false }
                hint={errors.name_middle && errors.name_middle.message}
                disabled={mode === 'view'}
              />
            </div>
            <div>
              <Label htmlFor="email">email</Label>
              <Input
                type="email"
                id="email"
                placeholder="email"
                {...register("email")}
                error={errors.email && errors.email.message ? true : false }
                hint={errors.email && errors.email.message}
                disabled={mode === 'view'}
              />
            </div>
            <div>
              <Label htmlFor="phone">phone</Label>
              <Input
                type="tel"
                id="phone"
                placeholder="phone"
                {...register("phone")}
                error={errors.phone && errors.phone.message ? true : false }
                hint={errors.phone && errors.phone.message}
                disabled={mode === 'view'}
              />
            </div>
            <div>
              <Label htmlFor="company">company</Label>
              <Input
                type="text"
                id="company"
                placeholder="company"
                {...register("company")}
                error={errors.company && errors.company.message ? true : false }
                hint={errors.company && errors.company.message}
                disabled={mode === 'view'}
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
      </ComponentCard>
    </>
  );
}

