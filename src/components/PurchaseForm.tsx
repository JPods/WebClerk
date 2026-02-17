import { useEffect } from "react";
import { useDispatch } from "react-redux";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import ComponentCard from "./common/ComponentCard";
import Label from "./form/Label";
import { Input } from "./wrapper";

import { saveRecord } from "../api/wcapi";
import { showToast } from "../store/slices/toastSlice";

const purchaseSchema = z.object({
  receipt_id: z.string().optional(),
  vendor_pack_list: z.string().optional(),
  vendor_pack_date: z.string().optional(),
});

type PurchaseFormValues = z.infer<typeof purchaseSchema>;

interface PurchaseFormProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: Record<string, any> | null;
  onSaved?: () => void;
}

export default function PurchaseForm({ modeProp, dataProp, onSaved }: PurchaseFormProps) {
  const dispatch = useDispatch();
  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<PurchaseFormValues>({
    resolver: zodResolver(purchaseSchema),
    defaultValues: {},
  });

  const mode: "add" | "edit" | "view" = modeProp || "add";
  const data = dataProp || null;

  useEffect(() => {
    if (mode === "add") {
      reset();
    } else if (data) {
      (Object.keys(purchaseSchema.shape) as Array<keyof PurchaseFormValues>).forEach((key) => {
        const value = data[key as string];
        if (value !== undefined && value !== null) {
          setValue(key, value);
        }
      });
    } else {
      reset({});
    }
  }, [data, mode, reset, setValue]);

  const onSubmit = async (formData: PurchaseFormValues) => {
    try {
      const payload = { ...formData, id: data?.id };
      const res = await saveRecord("purchase", payload);
      if (res) {
        dispatch(
          showToast({
            message: `purchase ${mode === "add" ? "saved" : "updated"} successfully`,
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        }
      }
    } catch (error: any) {
      dispatch(
        showToast({
          message: error?.message || "failed to save purchase",
          type: "error",
        })
      );
    }
  };

  return (
    <ComponentCard>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div>
            <Label htmlFor="receipt_id">receipt_id</Label>
            <Input
              type="text"
              id="receipt_id"
              placeholder="receipt_id"
              {...register("receipt_id")}
              error={Boolean(errors.receipt_id)}
              hint={errors.receipt_id?.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="vendor_pack_list">vendor_pack_list</Label>
            <Input
              type="text"
              id="vendor_pack_list"
              placeholder="vendor_pack_list"
              {...register("vendor_pack_list")}
              error={Boolean(errors.vendor_pack_list)}
              hint={errors.vendor_pack_list?.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="vendor_pack_date">vendor_pack_date</Label>
            <Input
              type="date"
              id="vendor_pack_date"
              placeholder="vendor_pack_date"
              {...register("vendor_pack_date")}
              error={Boolean(errors.vendor_pack_date)}
              hint={errors.vendor_pack_date?.message}
              disabled={mode === "view"}
            />
          </div>
        </div>
        {mode !== "view" && (
          <div className="flex items-center gap-4">
            <button
              type="submit"
              className="flex items-center rounded-md bg-blue-500 px-4 py-2 text-white hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
            >
              {mode === "edit" ? "update" : "submit"}
            </button>
          </div>
        )}
      </form>
    </ComponentCard>
  );
}
