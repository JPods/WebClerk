/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowRightLeft, ArrowLeftRight, DollarSign, TrendingUp, Calendar, Activity } from "lucide-react";

import ComponentCard from "../../../../../components/common/ComponentCard";
import HorizontalField from "../../../../../components/form/HorizontalField";
import { useColumnCount, ColumnSelector, getGridClassName } from "../../../../../components/form/useColumnCount";
import { Input, DropDown } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";
import { DetailTabs, useDetailTabs } from "../../../../../components/common/DetailTabs";
import CommentsPanel from "../../../../common/components/panels/CommentsPanel";
import ActionsPanel from "../../../../common/components/panels/ActionsPanel";
import { ScalarCard, BaseModelCards } from "@/apps/common/components/detail";
import { createExchangeTransaction, updateExchangeTransaction } from "../services/exchangeTransactionApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { exchangeTransactionSchema } from "../utils/exchangeTransactionSchema";
import { ExchangeTransactionAddProps } from "../types/exchangeTransactionType";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

const STORAGE_KEY = "exchangeTransactionDetail_columnCount";

function ExchangeTransactionDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ExchangeTransactionAddProps) {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [isSaving, setIsSaving] = useState(false);

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
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  const data = dataProp || routeState.data || null;

  // Tab state - default to comments
  const { activeTab, setActiveTab } = useDetailTabs("exchangeTransaction", "comments");

  useEffect(() => {
    if (currentMode === "add") {
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
  }, [data, reset, setValue, currentMode]);

  const onSubmit = async (formData: z.infer<typeof exchangeTransactionSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
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
              currentMode === "add" ? "created" : "updated"
            } successfully`,
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        } else {
          setCurrentMode("view");
        }
      }
    } catch (error: any) {
      dispatch(showToast({ message: error.message, type: "error" }));
    } finally {
      setIsSaving(false);
    }
  };

  const handleEdit = () => {
    setCurrentMode("edit");
  };

  const handleCancel = () => {
    if (inline && onCancelInline) {
      onCancelInline();
    } else if (initialMode === "add") {
      navigate(-1);
    } else {
      if (data) {
        Object.keys(data).forEach((key: any) => {
          if (data[key] !== undefined) {
            setValue(key, data[key]);
          }
        });
      }
      setCurrentMode("view");
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

  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  // Tab content renderer
  const renderTabContent = () => {
    switch (activeTab) {
      case "comments":
        return (
          <CommentsPanel
            entityType="exchange_transaction"
            entityId={data?.id}
            comments={data?.comments}
            isEditing={currentMode === "edit"}
            currentUser="Current User"
          />
        );
      case "actions":
        return (
          <ActionsPanel
            entityType="exchange_transaction"
            entityId={data?.id}
            data={data?.actions?.items}
            isEditing={currentMode === "edit"}
          />
        );
      case "raw":
        return (
          <pre className="text-xs font-mono bg-slate-100 dark:bg-slate-800 p-4 rounded overflow-auto">
            {JSON.stringify(data, null, 2)}
          </pre>
        );
      default:
        return null;
    }
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            currentMode === "edit"
              ? "Edit Exchange Transaction"
              : currentMode === "view"
              ? "View Exchange Transaction"
              : "Exchange Transaction Detail"
          }
        />
      )}

      {!inline && (
        <SimpleDetailHeader
          entityName="Exchange Transaction"
          recordId={data?.id}
          recordName={data?.from_currency && data?.to_currency ? `${data.from_currency} → ${data.to_currency}` : undefined}
          mode={currentMode}
          backUrl="/accounts/exchange-transactions"
        />
      )}

      {!inline && (
        <SimpleDetailToolbar
          mode={currentMode}
          isSaving={isSaving}
          onSave={handleSubmit(onSubmit)}
          onCancel={handleCancel}
          onEdit={handleEdit}
        />
      )}

      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {currentMode === "edit"
                ? "Edit Exchange Transaction"
                : currentMode === "view"
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
          <div className="flex justify-end mb-4">
            <ColumnSelector value={columnCount} onChange={setColumnCount} />
          </div>
          <div className={getGridClassName(columnCount)}>
            <HorizontalField label="From Currency" htmlFor="from_currency" icon={<ArrowRightLeft size={14} />}>
              <DropDown
                id="from_currency"
                options={currencyOptions}
                placeholder="Select From Currency"
                value={watch("from_currency")}
                onChange={handleFromCurrencyChange}
                className="dark:bg-dark-900"
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="To Currency" htmlFor="to_currency" icon={<ArrowLeftRight size={14} />}>
              <DropDown
                id="to_currency"
                options={currencyOptions}
                placeholder="Select To Currency"
                value={watch("to_currency")}
                onChange={handleToCurrencyChange}
                className="dark:bg-dark-900"
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Amount" htmlFor="amount" error={errors.amount?.message} icon={<DollarSign size={14} />}>
              <Input
                type="number"
                id="amount"
                placeholder="Amount"
                {...register("amount", { valueAsNumber: true })}
                error={errors.amount && errors.amount.message ? true : false}
                hint={errors.amount && errors.amount.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Rate" htmlFor="rate" error={errors.rate?.message} icon={<TrendingUp size={14} />}>
              <Input
                type="number"
                id="rate"
                placeholder="Exchange Rate"
                {...register("rate", { valueAsNumber: true })}
                error={errors.rate && errors.rate.message ? true : false}
                hint={errors.rate && errors.rate.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Date" htmlFor="date" error={errors.date?.message} icon={<Calendar size={14} />}>
              <Input
                type="date"
                id="date"
                placeholder="Date"
                {...register("date")}
                error={errors.date && errors.date.message ? true : false}
                hint={errors.date && errors.date.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Status" htmlFor="status" icon={<Activity size={14} />}>
              <DropDown
                id="status"
                options={statusOptions}
                placeholder="Select Status"
                value={watch("status")}
                onChange={handleStatusChange}
                className="dark:bg-dark-900"
                disabled={currentMode === "view"}
              />
            </HorizontalField>
          </div>
          {currentMode !== "view" && (
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4 flex items-center gap-2">
              <button
                type="submit"
                className="flex items-center px-4 py-2 text-white bg-brand-500 rounded-md hover:bg-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
              >
                {currentMode === "edit" ? "Update" : "Submit"}
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

      {currentMode === "view" && data && (
        <div className="mt-4 space-y-0">
          <ScalarCard
            title="Exchange Transaction Fields"
            icon={<ArrowRightLeft size={14} />}
            fields={[
              { label: "from_currency", value: data.from_currency },
              { label: "to_currency", value: data.to_currency },
              { label: "amount", value: data.amount, isCurrency: true },
              { label: "rate", value: data.rate },
              { label: "date", value: data.date },
              { label: "status", value: data.status },
            ]}
            columns={columnCount as 1 | 2 | 3}
          />
          <BaseModelCards data={data as Record<string, unknown>} />
        </div>
      )}

      {/* Tab Navigation */}
      <DetailTabs
        entityType="exchangeTransaction"
        activeTab={activeTab}
        onTabChange={setActiveTab}
        standardTabs={["comments", "actions", "raw"]}
      />

      {/* Tab Content */}
      <ComponentCard>
        {renderTabContent()}
      </ComponentCard>
    </>
  );
}

export default withDevIdentifier(ExchangeTransactionDetail, 'ExchangeTransactionDetail');
