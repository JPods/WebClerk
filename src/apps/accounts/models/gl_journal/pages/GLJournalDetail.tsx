import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Calendar, FileText, DollarSign, List } from "lucide-react";

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
import { createGLJournal, updateGLJournal } from "../services/glJournalApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { glJournalSchema } from "../utils/glJournalSchema";
import { GLJournalAddProps } from "../types/glJournalType";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

const STORAGE_KEY = "glJournalDetail_columnCount";

function GLJournalDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: GLJournalAddProps) {
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
  } = useForm<z.infer<typeof glJournalSchema>>({
    resolver: zodResolver(glJournalSchema),
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  const data = dataProp || routeState.data || null;

  // Tab state - default to comments
  const { activeTab, setActiveTab } = useDetailTabs("glJournal", "comments");

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

  const onSubmit = async (formData: z.infer<typeof glJournalSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createGLJournal(formData)
          : await updateGLJournal({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `GL Journal ${
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

  const journalTypes = [
    { value: "debit", label: "Debit" },
    { value: "credit", label: "Credit" },
    { value: "adjustment", label: "Adjustment" },
  ];

  const handleTypeChange = (value: string) => {
    setValue("type", value);
  };

  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  // Tab content renderer
  const renderTabContent = () => {
    switch (activeTab) {
      case "comments":
        return (
          <CommentsPanel
            entityType="gl_journal"
            entityId={data?.id}
            comments={data?.comments}
            isEditing={currentMode === "edit"}
            currentUser="Current User"
          />
        );
      case "actions":
        return (
          <ActionsPanel
            entityType="gl_journal"
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
              ? "Edit GL Journal"
              : currentMode === "view"
              ? "View GL Journal"
              : "GL Journal Detail"
          }
        />
      )}

      {!inline && (
        <SimpleDetailHeader
          entityName="GL Journal"
          recordId={data?.id}
          recordName={data?.description}
          mode={currentMode}
          backUrl="/accounts/gl-journals"
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
                ? "Edit GL Journal"
                : currentMode === "view"
                ? "View GL Journal"
                : "Add New GL Journal"}
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
            <HorizontalField label="Type" htmlFor="type" icon={<List size={14} />}>
              <DropDown
                id="type"
                options={journalTypes}
                placeholder="Select Type"
                value={watch("type")}
                onChange={handleTypeChange}
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
            <HorizontalField label="Description" htmlFor="description" error={errors.description?.message} icon={<FileText size={14} />}>
              <Input
                type="text"
                id="description"
                placeholder="Description"
                {...register("description")}
                error={
                  errors.description && errors.description.message ? true : false
                }
                hint={errors.description && errors.description.message}
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
            title="GL Journal Fields"
            icon={<Calendar size={14} />}
            fields={[
              { label: "date", value: data.date },
              { label: "type", value: data.type },
              { label: "amount", value: data.amount, isCurrency: true },
              { label: "description", value: data.description },
            ]}
            columns={columnCount as 1 | 2 | 3}
          />
          <BaseModelCards data={data as Record<string, unknown>} />
        </div>
      )}

      {/* Tab Navigation */}
      <DetailTabs
        entityType="glJournal"
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

export default withDevIdentifier(GLJournalDetail, 'GLJournalDetail');
