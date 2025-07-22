import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../components/common/ComponentCard";
import Label from "../../components/form/Label";
import { Input, Select, TextArea } from "../../components/wrapper";

import PageBreadcrumb from "../../components/common/PageBreadCrumb";

import { actionSchema } from "../../validations/action";
import { getAction, patchAction, postAction } from "../../api/userProfile";
import { showToast } from "../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useAppSelector } from "../../store/hooks";
import { useLocation } from "react-router";


export default function ActionAdd() {
  
  const dispatch = useDispatch()
  const { user } = useAppSelector((state) => state.auth);
 
  const { register, setValue, handleSubmit, control, formState: { errors }, watch, reset } = useForm<z.infer<typeof actionSchema>>({
    resolver: zodResolver(actionSchema),
    defaultValues: {        
    },
  }); 
  
  const location = useLocation()
  const { mode, data} = location.state || {mode:'add', data:null}

   useEffect(() => {
    if (data) {
            Object.keys(data).forEach((key:any) => {
            if (data[key] !== undefined)
              setValue(key, data[key]);
            });
    }
  }, [data]);
 
  // const getActionData = async() => {
  //     try {
  //        const res = await getAction(user?.id)       
  //        if(res.status === 200)
  //        {
  //           setUploadStatus(1)
  //           Object.keys(res.data).forEach((key:any) => {
  //           if (res.data[key] !== undefined)
  //             setValue(key, res.data[key]);
  //           });
  //        }
         
  //     } catch (error) {
        
  //     }
  // }
  

  const onSubmit = async(data: z.infer<typeof actionSchema>) => {
    try {
      const res = mode === 'add' ? await postAction(data) : await patchAction(user?.id,data)
      if(res.status === 201)
      {
          dispatch(showToast({ message: "Action Saved Successfully", type: "success" }));
      }
      else if(res.status === 200)
      {
        dispatch(showToast({ message: "Action updated Successfully", type: "success" }));
      }
    } catch (error:any) {
         dispatch(showToast({ message: error.message, type: "error" }));
    }  
  };

  console.log("error", errors)

  return (
    <>
      <PageBreadcrumb pageTitle={mode === 'edit' ? 'Edit Action' : mode === 'view' ? 'View Action' : 'Add Action'} />
      <ComponentCard>
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
              <button
                type="submit"
                className="flex items-center px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
              >
                Submit
              </button>
          )}          
        </form>
      </ComponentCard>
    </>
  );
}

