import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import Label from "../../../../../components/form/Label";
import { Input, DropDown } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createGLAccount, updateGLAccount } from "../services/glAccountApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { glAccountSchema } from "../utils/glAccountSchema";
import { GLAccountAddProps } from "../types/glAccountType";
import { Hash, FileText, Layers, Building2, MessageSquare, DollarSign, ArrowRightLeft, Tag } from "lucide-react";

/* ----------------------------------
   Horizontal Field Row Component
   Label on left, input on right (Enterprise standard)
   Compact version for 3-column grid layout
---------------------------------- */
interface HorizontalFieldProps {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
  error?: string;
  required?: boolean;
  icon?: React.ReactNode;
}

function HorizontalField({ label, htmlFor, children, error, required, icon }: HorizontalFieldProps) {
  return (
    <div className="flex items-center gap-2 py-2">
      <Label htmlFor={htmlFor} className="w-28 shrink-0 text-right text-sm font-medium text-slate-600 dark:text-slate-400 flex items-center justify-end gap-1">
        {icon && <span className="text-slate-400">{icon}</span>}
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </Label>
      <div className="flex-1 min-w-0">
        {children}
        {error && <p className="mt-0.5 text-xs text-red-500">{error}</p>}
      </div>
    </div>
  );
}

// Column layout options
const COLUMN_OPTIONS = [
  { value: 2, label: "2" },
  { value: 3, label: "3" },
];

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
  const [columnCount, setColumnCount] = useState<number>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? parseInt(saved, 10) : 3;
  });

  // Persist column count preference
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(columnCount));
  }, [columnCount]);

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

  const onSubmit = async (formData: z.infer<typeof glAccountSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createGLAccount(formData)
          : await updateGLAccount({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `GL Account ${
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

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit GL Account"
              : mode === "view"
              ? "View GL Account"
              : "GL Account Detail"
          }
        />
      )}
      <div className="p-4 space-y-4 bg-white dark:bg-slate-900 rounded-lg shadow">
        {/* Header with Title and Column Selector */}
        <div className="flex items-center justify-between border-b pb-3">
          <h2 className="text-xl font-semibold text-slate-800 dark:text-slate-200">
            {mode === "edit" ? "Edit GL Account" : mode === "view" ? "View GL Account" : "Add GL Account"}
            {watch("name") && <span className="ml-2 text-slate-500 font-normal">— {watch("name")}</span>}
          </h2>
          
          <div className="flex items-center gap-4">
            {/* Column Selector */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Columns:</span>
              <div className="flex border rounded overflow-hidden">
                {COLUMN_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setColumnCount(opt.value)}
                    className={`px-2 py-1 text-xs font-medium transition-colors ${
                      columnCount === opt.value
                        ? "bg-blue-500 text-white"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
            
            {inline && onCancelInline && (
              <button
                type="button"
                onClick={onCancelInline}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                &times;
              </button>
            )}
          </div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Account Identification Section */}
          <fieldset className="border rounded-lg p-4 bg-slate-50 dark:bg-slate-800/50">
            <legend className="text-sm font-semibold text-slate-700 dark:text-slate-300 px-2">
              Account Identification
            </legend>
            <div className={`grid grid-cols-1 ${columnCount === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2'} gap-x-6 gap-y-1`}>
              <HorizontalField label="Account #" htmlFor="code" required icon={<Hash size={14} />} error={errors.code?.message}>
                <Input
                  type="text"
                  id="code"
                  placeholder="10101-000-000"
                  {...register("code")}
                  disabled={mode === "view"}
                  className="h-8"
                />
              </HorizontalField>

              <HorizontalField label="Name" htmlFor="name" required icon={<FileText size={14} />} error={errors.name?.message}>
                <Input
                  type="text"
                  id="name"
                  placeholder="Account Name"
                  {...register("name")}
                  disabled={mode === "view"}
                  className="h-8"
                />
              </HorizontalField>

              <HorizontalField label="Used For" htmlFor="used_for" icon={<Tag size={14} />}>
                <Input
                  type="text"
                  id="used_for"
                  placeholder="AR, AP, Inventory..."
                  {...register("used_for")}
                  disabled={mode === "view"}
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
            <div className={`grid grid-cols-1 ${columnCount === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2'} gap-x-6 gap-y-1`}>
              <HorizontalField label="Type" htmlFor="type" required icon={<Layers size={14} />}>
                <DropDown
                  id="type"
                  options={accountTypes}
                  placeholder="Select Account Type"
                  value={watch("type")}
                  onChange={handleTypeChange}
                  className="dark:bg-dark-900 h-8"
                  disabled={mode === "view"}
                />
              </HorizontalField>

              <HorizontalField label="Category" htmlFor="category" icon={<Tag size={14} />}>
                <Input
                  type="text"
                  id="category"
                  placeholder="Current, Fixed, etc."
                  {...register("category")}
                  disabled={mode === "view"}
                  className="h-8"
                />
              </HorizontalField>

              <HorizontalField label="Division" htmlFor="division" icon={<Building2 size={14} />}>
                <Input
                  type="text"
                  id="division"
                  placeholder="000"
                  {...register("division")}
                  disabled={mode === "view"}
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
            <div className={`grid grid-cols-1 ${columnCount === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2'} gap-x-6 gap-y-1`}>
              <HorizontalField label="Balance" htmlFor="balance" icon={<DollarSign size={14} />}>
                <Input
                  type="number"
                  id="balance"
                  placeholder="0.00"
                  {...register("balance", { valueAsNumber: true })}
                  disabled={mode === "view"}
                  className="h-8"
                />
              </HorizontalField>

              <HorizontalField label="Debit Acct" htmlFor="account_debit" icon={<ArrowRightLeft size={14} />}>
                <Input
                  type="number"
                  id="account_debit"
                  placeholder="Related debit account"
                  {...register("account_debit", { valueAsNumber: true })}
                  disabled={mode === "view"}
                  className="h-8"
                />
              </HorizontalField>

              <HorizontalField label="Credit Acct" htmlFor="account_credit" icon={<ArrowRightLeft size={14} />}>
                <Input
                  type="number"
                  id="account_credit"
                  placeholder="Related credit account"
                  {...register("account_credit", { valueAsNumber: true })}
                  disabled={mode === "view"}
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
                  disabled={mode === "view"}
                  className="h-8"
                />
              </HorizontalField>
            </div>
          </fieldset>

          {/* Action Buttons */}
          {mode !== "view" && (
            <div className="flex items-center gap-2 pt-2 border-t">
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
      </div>
    </>
  );
}