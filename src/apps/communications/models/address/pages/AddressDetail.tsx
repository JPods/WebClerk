import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { MapPin, Home, Building2, Map, Navigation, Hash, Globe, Compass } from "lucide-react";

import ComponentCard from "../../../../../components/common/ComponentCard";
import HorizontalField from "../../../../../components/form/HorizontalField";
import { useColumnCount, ColumnSelector, getGridClassName } from "../../../../../components/form/useColumnCount";
import { Input, CustTextArea } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";
import { DetailTabs, useDetailTabs } from "../../../../../components/common/DetailTabs";
import ContactLinksPanel from "../../../../common/components/panels/ContactLinksPanel";
import CommentsPanel from "../../../../common/components/panels/CommentsPanel";
import ActionsPanel from "../../../../common/components/panels/ActionsPanel";
import DocumentsPanel from "../../../../common/components/panels/DocumentsPanel";
import { createAddress, updateAddress } from "../services/addressApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { addressSchema } from "../utils/addressSchema";
import { AddressAddProps } from "../types/addressType";

const STORAGE_KEY = "addressDetail_columnCount";

export default function AddressDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: AddressAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof addressSchema>>({
    resolver: zodResolver(addressSchema),
  });

  const location = useLocation();
  const navigate = useNavigate();
  const routeState = (location.state as any) || {};
  const [isSaving, setIsSaving] = useState(false);
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  const data = dataProp || routeState.data || null;

  // Tab state - default to contacts since overview is persistent
  const { activeTab, setActiveTab } = useDetailTabs("address", "contacts");
  
  // Column count for responsive layout
  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

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

  const onSubmit = async (formData: z.infer<typeof addressSchema>) => {
    setIsSaving(true);
    try {
      const res =
        currentMode === "add"
          ? await createAddress(formData)
          : await updateAddress({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Address ${
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

  // Render tab content (no overview - it's persistent above)
  const renderTabContent = () => {
    switch (activeTab) {
      case "contacts":
        return (
          <ContactLinksPanel
            entityType="address"
            entityId={data?.id}
            data={data?.refs?.links?.contact}
            isEditing={currentMode === "edit"}
          />
        );

      case "comments":
        return (
          <CommentsPanel
            entityType="address"
            entityId={data?.id}
            comments={data?.comments}
            isEditing={currentMode === "edit"}
            currentUser="Current User"
          />
        );

      case "actions":
        return (
          <ActionsPanel
            entityType="address"
            entityId={data?.id}
            data={data?.actions?.items}
            isEditing={currentMode === "edit"}
          />
        );

      case "documents":
        return (
          <DocumentsPanel
            parentType="address"
            parentId={data?.id}
            data={data?.refs?.links?.document}
            isEditing={currentMode === "edit"}
          />
        );

      case "history":
        return (
          <div className="text-slate-500 dark:text-slate-400 py-8 text-center">
            <p>History log will appear here</p>
          </div>
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
      {/* Breadcrumb */}
      {!hideBreadcrumb && (
        <PageBreadcrumb
          pageTitle={
            currentMode === "edit"
              ? "Edit Address"
              : currentMode === "view"
              ? "View Address"
              : "Address Detail"
          }
        />
      )}

      {/* Header */}
      <SimpleDetailHeader
        entityName="Address"
        recordId={data?.id}
        recordName={data?.name || data?.address1 || data?.full}
        mode={currentMode}
        backUrl="/communications/addresses"
      />

      {/* Toolbar */}
      <SimpleDetailToolbar
        mode={currentMode}
        isSaving={isSaving}
        onSave={handleSubmit(onSubmit)}
        onCancel={handleCancel}
        onEdit={handleEdit}
      />

      {/* Persistent Overview Form */}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {currentMode === "edit"
                ? "Edit Address"
                : currentMode === "view"
                ? "View Address"
                : "Add New Address"}
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
            <HorizontalField label="Address 1" htmlFor="address1" error={errors.address1?.message} icon={<Home size={14} />}>
              <Input
                type="text"
                id="address1"
                placeholder="Street address"
                {...register("address1")}
                error={errors.address1?.message ? true : false}
                hint={errors.address1?.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Address 2" htmlFor="address2" error={errors.address2?.message} icon={<Building2 size={14} />}>
              <Input
                type="text"
                id="address2"
                placeholder="Apt, suite, unit"
                {...register("address2")}
                error={errors.address2?.message ? true : false}
                hint={errors.address2?.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Type" htmlFor="address_type" error={errors.address_type?.message} icon={<Hash size={14} />}>
              <Input
                type="text"
                id="address_type"
                placeholder="Billing, Shipping, etc."
                {...register("address_type")}
                error={errors.address_type?.message ? true : false}
                hint={errors.address_type?.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="City" htmlFor="city" error={errors.city?.message} icon={<MapPin size={14} />}>
              <Input
                type="text"
                id="city"
                placeholder="City"
                {...register("city")}
                error={errors.city?.message ? true : false}
                hint={errors.city?.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="State" htmlFor="state" error={errors.state?.message} icon={<Map size={14} />}>
              <Input
                type="text"
                id="state"
                placeholder="State / Province"
                {...register("state")}
                error={errors.state?.message ? true : false}
                hint={errors.state?.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="ZIP" htmlFor="zip" error={errors.zip?.message} icon={<Navigation size={14} />}>
              <Input
                type="text"
                id="zip"
                placeholder="ZIP / Postal Code"
                {...register("zip")}
                error={errors.zip?.message ? true : false}
                hint={errors.zip?.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Country" htmlFor="country" error={errors.country?.message} icon={<Globe size={14} />}>
              <Input
                type="text"
                id="country"
                placeholder="Country"
                {...register("country")}
                error={errors.country?.message ? true : false}
                hint={errors.country?.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Latitude" htmlFor="latitude" error={errors.latitude?.message} icon={<Compass size={14} />}>
              <Input
                type="text"
                id="latitude"
                placeholder="e.g. 40.7128"
                {...register("latitude")}
                error={errors.latitude?.message ? true : false}
                hint={errors.latitude?.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Longitude" htmlFor="longitude" error={errors.longitude?.message} icon={<Compass size={14} />}>
              <Input
                type="text"
                id="longitude"
                placeholder="e.g. -74.0060"
                {...register("longitude")}
                error={errors.longitude?.message ? true : false}
                hint={errors.longitude?.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
          </div>

          {/* Full Address - spans full width */}
          <div className="mt-4">
            <HorizontalField label="Full Address" htmlFor="full" error={errors.full?.message} icon={<MapPin size={14} />}>
              <CustTextArea
                id="full"
                placeholder="Complete formatted address"
                {...register("full")}
                error={errors.full?.message ? true : false}
                hint={errors.full?.message}
                disabled={currentMode === "view"}
                rows={2}
              />
            </HorizontalField>
          </div>

          {/* Inline mode buttons */}
          {currentMode !== "view" && inline && (
            <div className="flex items-center gap-2 pt-4 border-t border-slate-200 dark:border-slate-700">
              <button
                type="submit"
                className="flex items-center px-4 py-2 text-white bg-brand-500 rounded-md hover:bg-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
              >
                {currentMode === "edit" ? "Update" : "Submit"}
              </button>
              {onCancelInline && (
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

      {/* Tab Navigation (below persistent overview) */}
      <DetailTabs
        entityType="address"
        activeTab={activeTab}
        onTabChange={setActiveTab}
        standardTabs={["contacts", "comments", "actions", "documents", "history", "raw"]}
      />

      {/* Tab Content */}
      <ComponentCard>
        {renderTabContent()}
      </ComponentCard>
    </>
  );
}
