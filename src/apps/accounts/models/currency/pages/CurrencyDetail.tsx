import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Hash, Type, DollarSign, TrendingUp } from "lucide-react";

import ComponentCard from "../../../../../components/common/ComponentCard";
import HorizontalField from "../../../../../components/form/HorizontalField";
import { useColumnCount, ColumnSelector, getGridClassName } from "../../../../../components/form/useColumnCount";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";
import { DetailTabs, useDetailTabs } from "../../../../../components/common/DetailTabs";
import CommentsPanel from "../../../../common/components/panels/CommentsPanel";
import ActionsPanel from "../../../../common/components/panels/ActionsPanel";
import { ScalarCard, BaseModelCards } from "@/apps/common/components/detail";
import { createCurrency, updateCurrency } from "../services/currencyApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { currencySchema } from "../utils/currencySchema";
import { CurrencyAddProps } from "../types/currencyType";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

const STORAGE_KEY = "currencyDetail_columnCount";

function CurrencyDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: CurrencyAddProps) {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [isSaving, setIsSaving] = useState(false);

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof currencySchema>>({
    resolver: zodResolver(currencySchema),
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  const data = dataProp || routeState.data || null;

  // Tab state - default to comments
  const { activeTab, setActiveTab } = useDetailTabs("currency", "comments");

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

  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  // Tab content renderer
  const renderTabContent = () => {
    switch (activeTab) {
      case "comments":
        return (
          <CommentsPanel
            entityType="currency"
            entityId={data?.id}
            comments={data?.comments}
            isEditing={currentMode === "edit"}
            currentUser="Current User"
          />
        );
      case "actions":
        return (
          <ActionsPanel
            entityType="currency"
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

  const onSubmit = async (formData: z.infer<typeof currencySchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createCurrency(formData)
          : await updateCurrency({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Currency ${
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

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            currentMode === "edit"
              ? "Edit Currency"
              : currentMode === "view"
              ? "View Currency"
              : "Currency Detail"
          }
        />
      )}

      {!inline && (
        <SimpleDetailHeader
          entityName="Currency"
          recordId={data?.id}
          recordName={data?.name}
          mode={currentMode}
          backUrl="/accounts/currencies"
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
                ? "Edit Currency"
                : currentMode === "view"
                ? "View Currency"
                : "Add New Currency"}
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
            <HorizontalField label="Code" htmlFor="code" error={errors.code?.message} icon={<Hash size={14} />}>
              <Input
                type="text"
                id="code"
                placeholder="Currency Code"
                {...register("code")}
                error={errors.code && errors.code.message ? true : false}
                hint={errors.code && errors.code.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Name" htmlFor="name" error={errors.name?.message} icon={<Type size={14} />}>
              <Input
                type="text"
                id="name"
                placeholder="Currency Name"
                {...register("name")}
                error={errors.name && errors.name.message ? true : false}
                hint={errors.name && errors.name.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Symbol" htmlFor="symbol" error={errors.symbol?.message} icon={<DollarSign size={14} />}>
              <Input
                type="text"
                id="symbol"
                placeholder="Currency Symbol"
                {...register("symbol")}
                error={errors.symbol && errors.symbol.message ? true : false}
                hint={errors.symbol && errors.symbol.message}
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
            title="Currency Fields"
            icon={<DollarSign size={14} />}
            fields={[
              { label: "code", value: data.code },
              { label: "name", value: data.name },
              { label: "symbol", value: data.symbol },
              { label: "rate", value: data.rate },
            ]}
            columns={columnCount as 1 | 2 | 3}
          />
          <BaseModelCards data={data as Record<string, unknown>} />
        </div>
      )}

      {/* Tab Navigation */}
      <DetailTabs
        entityType="currency"
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

export default withDevIdentifier(CurrencyDetail, 'CurrencyDetail');
