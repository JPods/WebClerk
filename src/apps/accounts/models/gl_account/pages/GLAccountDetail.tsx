import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Hash, FileText, Layers, Building2, MessageSquare, DollarSign, ArrowRightLeft, Tag } from "lucide-react";

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
import { createGLAccount, updateGLAccount } from "../services/glAccountApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { glAccountSchema } from "../utils/glAccountSchema";
import { GLAccountAddProps } from "../types/glAccountType";

const STORAGE_KEY = "glAccountDetail_columnCount";

export default function GLAccountDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: GLAccountAddProps) {
  const dispatch = useDispatch();
  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<z.infer<typeof glAccountSchema>>({
    resolver: zodResolver(glAccountSchema),
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  const [isSaving, setIsSaving] = useState(false);
  const data = dataProp || routeState.data || null;

  // Tab state - default to comments
  const { activeTab, setActiveTab } = useDetailTabs("glAccount", "comments");

  const handleEdit = () => setCurrentMode("edit");
  const handleCancel = () => {
    if (inline && onCancelInline) {
      onCancelInline();
    } else if (initialMode === "add") {
      // Navigate back
    } else {
      setCurrentMode("view");
    }
  };
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

  const onSubmit = async (formData: z.infer<typeof glAccountSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createGLAccount(formData)
          : await updateGLAccount({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `GL Account ${
              currentMode === "add" ? "created" : "updated"
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
    } finally {
      setIsSaving(false);
    }
  };

  const accountTypes = [
    { value: "asset", label: "Asset" },
    { value: "liability", label: "Liability" },
    { value: "equity", label: "Equity" },
    { value: "revenue", label: "Revenue" },
    { value: "expense", label: "Expense" },
  ];

  const handleTypeChange = (value: string) => {
    setValue("type", value);
  };

  // Tab content renderer
  const renderTabContent = () => {
    switch (activeTab) {
      case "comments":
        return (
          <CommentsPanel
            entityType="gl_account"
            entityId={data?.id}
            comments={data?.comments}
            isEditing={currentMode === "edit"}
            currentUser="Current User"
          />
        );
      case "actions":
        return (
          <ActionsPanel
            entityType="gl_account"
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
              ? "Edit GL Account"
              : currentMode === "view"
              ? "View GL Account"
              : "GL Account Detail"
          }
        />
      )}

      <SimpleDetailHeader
        entityName="GL Account"
        recordId={data?.id}
        recordName={data?.name || data?.code}
        mode={currentMode}
        backUrl={inline ? undefined : "/accounts/gl-accounts"}
        onClose={inline ? onCancelInline : undefined}
      />

      <SimpleDetailToolbar
        mode={currentMode}
        isSaving={isSaving}
        onSave={handleSubmit(onSubmit)}
        onCancel={handleCancel}
        onEdit={handleEdit}
      />

      <ComponentCard>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="flex justify-end mb-4">
            <ColumnSelector value={columnCount} onChange={setColumnCount} />
          </div>
          {/* Account Identification Section */}
          <fieldset className="border rounded-lg p-4 bg-slate-50 dark:bg-slate-800/50">
            <legend className="text-sm font-semibold text-slate-700 dark:text-slate-300 px-2">
              Account Identification
            </legend>
            <div className={getGridClassName(columnCount)}>
              <HorizontalField label="Account #" htmlFor="code" required icon={<Hash size={14} />} error={errors.code?.message}>
                <Input
                  type="text"
                  id="code"
                  placeholder="10101-000-000"
                  {...register("code")}
                  disabled={currentMode === "view"}
                  className="h-8"
                />
              </HorizontalField>

              <HorizontalField label="Name" htmlFor="name" required icon={<FileText size={14} />} error={errors.name?.message}>
                <Input
                  type="text"
                  id="name"
                  placeholder="Account Name"
                  {...register("name")}
                  disabled={currentMode === "view"}
                  className="h-8"
                />
              </HorizontalField>

              <HorizontalField label="Used For" htmlFor="used_for" icon={<Tag size={14} />}>
                <Input
                  type="text"
                  id="used_for"
                  placeholder="AR, AP, Inventory..."
                  {...register("used_for")}
                  disabled={currentMode === "view"}
                  className="h-8"
                />
              </HorizontalField>
            </div>
          </fieldset>

          {/* Classification Section */}
          <fieldset className="border rounded-lg p-4 bg-slate-50 dark:bg-slate-800/50">
            <legend className="text-sm font-semibold text-slate-700 dark:text-slate-300 px-2">
              Classification
            </legend>
            <div className={getGridClassName(columnCount)}>
              <HorizontalField label="Type" htmlFor="type" required icon={<Layers size={14} />}>
                <DropDown
                  id="type"
                  options={accountTypes}
                  placeholder="Select Account Type"
                  value={watch("type")}
                  onChange={handleTypeChange}
                  className="dark:bg-dark-900 h-8"
                  disabled={currentMode === "view"}
                />
              </HorizontalField>

              <HorizontalField label="Category" htmlFor="category" icon={<Tag size={14} />}>
                <Input
                  type="text"
                  id="category"
                  placeholder="Current, Fixed, etc."
                  {...register("category")}
                  disabled={currentMode === "view"}
                  className="h-8"
                />
              </HorizontalField>

              <HorizontalField label="Division" htmlFor="division" icon={<Building2 size={14} />}>
                <Input
                  type="text"
                  id="division"
                  placeholder="000"
                  {...register("division")}
                  disabled={currentMode === "view"}
                  className="h-8"
                />
              </HorizontalField>
            </div>
          </fieldset>

          {/* Financial Details Section */}
          <fieldset className="border rounded-lg p-4 bg-slate-50 dark:bg-slate-800/50">
            <legend className="text-sm font-semibold text-slate-700 dark:text-slate-300 px-2">
              Financial Details
            </legend>
            <div className={getGridClassName(columnCount)}>
              <HorizontalField label="Balance" htmlFor="balance" icon={<DollarSign size={14} />}>
                <Input
                  type="number"
                  id="balance"
                  placeholder="0.00"
                  {...register("balance", { valueAsNumber: true })}
                  disabled={currentMode === "view"}
                  className="h-8"
                />
              </HorizontalField>

              <HorizontalField label="Debit Acct" htmlFor="account_debit" icon={<ArrowRightLeft size={14} />}>
                <Input
                  type="number"
                  id="account_debit"
                  placeholder="Related debit account"
                  {...register("account_debit", { valueAsNumber: true })}
                  disabled={currentMode === "view"}
                  className="h-8"
                />
              </HorizontalField>

              <HorizontalField label="Credit Acct" htmlFor="account_credit" icon={<ArrowRightLeft size={14} />}>
                <Input
                  type="number"
                  id="account_credit"
                  placeholder="Related credit account"
                  {...register("account_credit", { valueAsNumber: true })}
                  disabled={currentMode === "view"}
                  className="h-8"
                />
              </HorizontalField>
            </div>
          </fieldset>

          {/* Notes Section */}
          <fieldset className="border rounded-lg p-4 bg-slate-50 dark:bg-slate-800/50">
            <legend className="text-sm font-semibold text-slate-700 dark:text-slate-300 px-2">
              Notes
            </legend>
            <div className="grid grid-cols-1 gap-x-6 gap-y-1">
              <HorizontalField label="Comment" htmlFor="comment" icon={<MessageSquare size={14} />}>
                <Input
                  type="text"
                  id="comment"
                  placeholder="Internal notes about this account"
                  {...register("comment")}
                  disabled={currentMode === "view"}
                  className="h-8"
                />
              </HorizontalField>
            </div>
          </fieldset>

          {/* Action Buttons */}
          {currentMode !== "view" && (
            <div className="flex items-center gap-2 pt-2 border-t">
              <button
                type="submit"
                className="flex items-center px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
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
            title="GL Account Fields"
            icon={<DollarSign size={14} />}
            fields={[
              { label: "code", value: data.code },
              { label: "name", value: data.name },
              { label: "used_for", value: data.used_for },
              { label: "type", value: data.type },
              { label: "category", value: data.category },
              { label: "division", value: data.division },
              { label: "balance", value: data.balance, isCurrency: true },
              { label: "account_debit", value: data.account_debit },
              { label: "account_credit", value: data.account_credit },
              { label: "comment", value: data.comment },
            ]}
            columns={columnCount as 1 | 2 | 3}
          />
          <BaseModelCards data={data as Record<string, unknown>} />
        </div>
      )}

      {/* Tab Navigation */}
      <DetailTabs
        entityType="glAccount"
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