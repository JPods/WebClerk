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

export default function ActionAdd({ modeProp, dataProp, hideBreadcrumb, onSaved, inline = false, onCancelInline }: ContactAddProps) {
  
  const dispatch = useDispatch();
  const { user } = useAppSelector((state) => state.auth);

  const { register, setValue, handleSubmit, formState: { errors }, reset } = useForm<z.infer<typeof actionSchema>>({
    resolver: zodResolver(actionSchema),
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

  const onSubmit = async (formData: z.infer<typeof actionSchema>) => {
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
      {!hideBreadcrumb && !inline && <PageBreadcrumb pageTitle={mode === 'edit' ? 'Edit Action' : mode === 'view' ? 'View Action' : 'Add Action'} />}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className=" dark:text-white text-lg font-semibold">
              {mode === 'edit' ? 'Edit Action' : mode === 'view' ? 'View Action' : 'Add New Action'}
            </h3>
            {onCancelInline && (
              <button type="button" onClick={onCancelInline} className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">&times;</button>
            )}
          </div>
        )}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="priority">Priority</Label>
              <Input
                type="text"
                id="priority"
                placeholder="Priority"
                {...register("priority")}
                error={errors.priority && errors.priority.message ? true : false }
                hint={errors.priority && errors.priority.message}
                disabled={mode == 'view'}
              />
            </div>
            <div>
              <Label htmlFor="difficulty">Difficulty</Label>
              <Input
                type="text"
                id="difficulty"
                placeholder="Difficulty"
                {...register("difficulty")}
                error={errors.difficulty && errors.difficulty.message ? true : false }
                hint={errors.difficulty && errors.difficulty.message}
                disabled={mode == 'view'}
              />
            </div>

             <div>
              <Label htmlFor="hours">Hours</Label>
              <Input
                type="number"
                id="hours"
                placeholder="Hours"
                {...register("hours")}
                error={errors.hours && errors.hours.message ? true : false }
                hint={errors.hours && errors.hours.message}
                disabled={mode == 'view'}
              />
            </div>
              <div>
              <Label htmlFor="percent">Percent</Label>
              <Input
                type="number"
                id="percent"
                placeholder="Percent"
                {...register("percent")}
                error={errors.percent && errors.percent.message ? true : false }
                hint={errors.percent && errors.percent.message}
                disabled={mode == 'view'}
              />
            </div>
              <div>
              <Label htmlFor="status">Status</Label>
              <Input
                type="text"
                id="status"
                placeholder="Status"
                {...register("status")}
                disabled={mode == 'view'}
              />
            </div>
              <div>
              <Label htmlFor="quality">Quality</Label>
              <Input
                type="text"
                id="quality"
                placeholder="Quality"
                {...register("quality")}
                disabled={mode == 'view'}
              />
            </div>  
          </div>
           <div className="grid grid-cols-1 gap-4">
              <div>
              <Label htmlFor="description">Description</Label>
               <TextArea 
                  placeholder="description"
                  register={register("description")} // This is the fix!
                  error={errors.description} // Pass the error object from useForm
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
      </ComponentCard>
    </>
  );
}

