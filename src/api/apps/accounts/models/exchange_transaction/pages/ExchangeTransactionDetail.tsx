import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../../components/common/ComponentCard";
import Label from "../../../../../../components/form/Label";
import { Input, DropDown } from "../../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import { createExchangeTransaction, updateExchangeTransaction } from "../services/exchangeTransactionApi";
import { showToast } from "../../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { exchangeTransactionSchema } from "../utils/exchangeTransactionSchema";
import { ExchangeTransactionAddProps } from "../types/exchangeTransactionType";

export default function ExchangeTransactionDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ExchangeTransactionAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<z.infer<typeof exchangeTransactionSchema>>({
    resolver: zodResolver(exchangeTransactionSchema),
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

  const onSubmit = async (formData: z.infer<typeof exchangeTransactionSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createExchangeTransaction({
              from_currency: formData.from_currency,
              to_currency: formData.to_currency,
              amount: formData.amount,
              rate: formData.rate,
              date: formData.date,
              status: formData.status,
            })
          : await updateExchangeTransaction({
              id: data.id,
              from_currency: formData.from_currency,
              to_currency: formData.to_currency,
              amount: formData.amount,
              rate: formData.rate,
              date: formData.date,
              status: formData.status,
            });
      if (res) {
        dispatch(
          showToast({
            message: `Exchange Transaction ${
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

  const currencyOptions = [
    { value: "USD", label: "USD" },
    { value: "EUR", label: "EUR" },
    { value: "GBP", label: "GBP" },
    { value: "JPY", label: "JPY" },
  ];

  const statusOptions = [
    { value: "pending", label: "Pending" },
    { value: "completed", label: "Completed" },
    { value: "failed", label: "Failed" },
  ];

  const handleFromCurrencyChange = (value: string) => {
    setValue("from_currency", value);
  };

  const handleToCurrencyChange = (value: string) => {
    setValue("to_currency", value);
  };

  const handleStatusChange = (value: string) => {
    setValue("status", value);
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Exchange Transaction"
              : mode === "view"
              ? "View Exchange Transaction"
              : "Exchange Transaction Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Exchange Transaction"
                : mode === "view"
                ? "View Exchange Transaction"
                : "Add New Exchange Transaction"}
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
              <Label htmlFor="from_currency">from_currency</Label>
              <DropDown
                id="from_currency"
                options={currencyOptions}
                placeholder="Select From Currency"
                value={watch("from_currency")}
                onChange={handleFromCurrencyChange}
                className="dark:bg-dark-900"
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="to_currency">to_currency</Label>
              <DropDown
                id="to_currency"
                options={currencyOptions}
                placeholder="Select To Currency"
                value={watch("to_currency")}
                onChange={handleToCurrencyChange}
                className="dark:bg-dark-900"
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="amount">amount</Label>
              <Input
                type="number"
                id="amount"
                placeholder="Amount"
                {...register("amount", { valueAsNumber: true })}
                error={errors.amount && errors.amount.message ? true : false}
                hint={errors.amount && errors.amount.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="rate">rate</Label>
              <Input
                type="number"
                id="rate"
                placeholder="Exchange Rate"
                {...register("rate", { valueAsNumber: true })}
                error={errors.rate && errors.rate.message ? true : false}
                hint={errors.rate && errors.rate.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="date">date</Label>
              <Input
                type="date"
                id="date"
                placeholder="Date"
                {...register("date")}
                error={errors.date && errors.date.message ? true : false}
                hint={errors.date && errors.date.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="status">status</Label>
              <DropDown
                id="status"
                options={statusOptions}
                placeholder="Select Status"
                value={watch("status")}
                onChange={handleStatusChange}
                className="dark:bg-dark-900"
                disabled={mode === "view"}
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