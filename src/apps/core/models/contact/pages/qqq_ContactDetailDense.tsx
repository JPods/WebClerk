/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect, useMemo, useState, useCallback } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Input from "../../../../../components/form/input/InputField";
import DropDown from "../../../../../components/form/input/DropDown";
import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createContact, updateContact } from "../services/contactApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import {
  contactSchema,
  updateContactSchema,
  mapRefsFormToApi,
} from "../utils/contactSchema";
import {
  ContactAddProps,
  CreateContactRequest,
  UpdateContactRequest,
} from "../types/contactType";
import Checkbox from "../../../../../components/form/input/Checkbox";
import {
  FaPlus,
  FaSave,
  FaTrash,
  FaEnvelope,
  FaPhone,
  FaMapMarkerAlt,
  FaGlobe,
  FaChevronDown,
  FaChevronRight,
} from "react-icons/fa";
import {
  createEmail,
  updateEmail,
  deleteEmail,
} from "@/apps/communications/models/email/services/emailApi";
import {
  CreateEmailRequest,
  UpdateEmailRequest,
} from "@/apps/communications/models/email/types/emailType";
import {
  createPhone,
  updatePhone,
  deletePhone,
} from "@/apps/communications/models/phone/services/phoneApi";
import { CreatePhoneRequest } from "@/apps/communications/models/phone/types/phoneType";
import {
  createAddress,
  updateAddress,
  deleteAddress,
} from "@/apps/communications/models/address/services/addressApi";
import { CreateAddressRequest } from "@/apps/communications/models/address/types/addressType";
import {
  createUrl,
  updateUrl,
  deleteUrl,
} from "@/apps/communications/models/url/services/urlApi";
import { CreateUrlRequest } from "@/apps/communications/models/url/types/urlType";
import { useReferenceData } from "../../../../../hooks/useReferenceData";

// ------------------------------------
// Communication Record Types
// ------------------------------------
interface EmailRecord {
  id: number;
  email_address: string;
  email_type: string;
  is_primary: boolean;
  is_active: boolean;
  _isNew?: boolean;
  _isDeleted?: boolean;
  _isDirty?: boolean;
}

interface PhoneRecord {
  id: number;
  phone_number: string;
  phone_type: string;
  is_primary: boolean;
  is_active: boolean;
  _isNew?: boolean;
  _isDeleted?: boolean;
  _isDirty?: boolean;
}

interface AddressRecord {
  id: number;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  address_type: string;
  is_primary: boolean;
  is_active: boolean;
  _isNew?: boolean;
  _isDeleted?: boolean;
  _isDirty?: boolean;
}

interface UrlRecord {
  id: number;
  url: string;
  url_type: string;
  is_primary: boolean;
  is_active: boolean;
  _isNew?: boolean;
  _isDeleted?: boolean;
  _isDirty?: boolean;
}

// ------------------------------------
// Inline Field Component - Label to Left of Input
// ------------------------------------
interface InlineFieldProps {
  label: string;
  children: React.ReactNode;
  required?: boolean;
  error?: string;
  labelWidth?: string;
}

function InlineField({
  label,
  children,
  required,
  error,
  labelWidth = "w-20",
}: InlineFieldProps) {
  return (
    <div className="flex items-center gap-1.5">
      <label
        className={`${labelWidth} flex-shrink-0 text-right text-[11px] font-medium text-slate-500 dark:text-slate-400 leading-tight`}
      >
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <div className="flex-1 min-w-0">
        {children}
        {error && <p className="text-[10px] text-red-500 mt-0.5">{error}</p>}
      </div>
    </div>
  );
}

// ------------------------------------
// Section Header Component
// ------------------------------------
interface SectionHeaderProps {
  icon: React.ReactNode;
  title: string;
  count?: number;
  isOpen: boolean;
  onToggle: () => void;
  onAdd?: () => void;
}

function SectionHeader({
  icon,
  title,
  count,
  isOpen,
  onToggle,
  onAdd,
}: SectionHeaderProps) {
  return (
    <div
      className="flex items-center justify-between py-1 px-2 bg-slate-100 dark:bg-slate-700/50 rounded cursor-pointer"
      onClick={onToggle}
    >
      <div className="flex items-center gap-1.5">
        <span className="text-slate-400">
          {isOpen ? (
            <FaChevronDown className="w-2.5 h-2.5" />
          ) : (
            <FaChevronRight className="w-2.5 h-2.5" />
          )}
        </span>
        <span className="text-slate-500 dark:text-slate-400">{icon}</span>
        <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-300">
          {title}
        </span>
        {count !== undefined && count > 0 && (
          <span className="text-[10px] bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 px-1 py-0.5 rounded-full">
            {count}
          </span>
        )}
      </div>
      {onAdd && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onAdd();
          }}
          className="p-0.5 text-blue-600 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded"
          title={`Add ${title.slice(0, -1)}`}
        >
          <FaPlus className="w-2.5 h-2.5" />
        </button>
      )}
    </div>
  );
}

// ------------------------------------
// Compact Inline Edit Row
// ------------------------------------
interface InlineRowProps {
  children: React.ReactNode;
  onDelete?: () => void;
  isPrimary?: boolean;
}

function InlineRow({ children, onDelete, isPrimary }: InlineRowProps) {
  return (
    <div
      className={`flex items-center gap-1.5 py-0.5 px-2 ${isPrimary ? "bg-blue-50/50 dark:bg-blue-900/10" : ""} hover:bg-slate-50 dark:hover:bg-slate-700/30 rounded`}
    >
      <div className="flex-1 flex items-center gap-1.5 flex-wrap">{children}</div>
      {onDelete && (
        <button
          type="button"
          onClick={onDelete}
          className="p-0.5 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 rounded opacity-50 hover:opacity-100"
        >
          <FaTrash className="w-2.5 h-2.5" />
        </button>
      )}
    </div>
  );
}

// ------------------------------------
// Main Component
// ------------------------------------
export default function ContactDetailDense({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ContactAddProps) {
  const dispatch = useDispatch();
  const location = useLocation();
  const routeState = (location.state as any) || {};
  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;

  // Section collapse state
  const [sectionsOpen, setSectionsOpen] = useState({
    emails: true,
    phones: true,
    addresses: false,
    urls: false,
  });

  const toggleSection = (section: keyof typeof sectionsOpen) => {
    setSectionsOpen((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  // Communication records state
  const [emails, setEmails] = useState<EmailRecord[]>([]);
  const [phones, setPhones] = useState<PhoneRecord[]>([]);
  const [addresses, setAddresses] = useState<AddressRecord[]>([]);
  const [urls, setUrls] = useState<UrlRecord[]>([]);

  // Reference data
  const { data: prefixOptions = [] } = useReferenceData("prefix");
  const { data: suffixOptions = [] } = useReferenceData("suffix");
  const { data: emailTypeOptions = [] } = useReferenceData("email_type");
  const { data: phoneTypeOptions = [] } = useReferenceData("phone_type");
  const { data: addressTypeOptions = [] } = useReferenceData("address_type");
  const { data: urlTypeOptions = [] } = useReferenceData("url_type");
  const { data: contactTypeOptions = [] } = useReferenceData("contact_type");
  const { data: contactStatusOptions = [] } = useReferenceData("contact_status");

  // Active counts
  const activeEmailCount = useMemo(
    () => emails.filter((e) => !e._isDeleted).length,
    [emails]
  );
  const activePhoneCount = useMemo(
    () => phones.filter((p) => !p._isDeleted).length,
    [phones]
  );
  const activeAddressCount = useMemo(
    () => addresses.filter((a) => !a._isDeleted).length,
    [addresses]
  );
  const activeUrlCount = useMemo(
    () => urls.filter((u) => !u._isDeleted).length,
    [urls]
  );

  const currentSchema = mode === "edit" ? updateContactSchema : contactSchema;
  type FormData = z.infer<typeof currentSchema>;

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(currentSchema),
    defaultValues: {
      prefix: "",
      first_name: "",
      middle_name: "",
      last_name: "",
      suffix: "",
      nickname: "",
      job_title: "",
      department: "",
      notes: "",
      contact_type: "",
      contact_status: "",
      is_active: true,
    },
  });

  // Initialize form from data
  useEffect(() => {
    if (data && (mode === "edit" || mode === "view")) {
      reset({
        prefix: data.prefix || "",
        first_name: data.first_name || "",
        middle_name: data.middle_name || "",
        last_name: data.last_name || "",
        suffix: data.suffix || "",
        nickname: data.nickname || "",
        job_title: data.job_title || "",
        department: data.department || "",
        notes: data.notes || "",
        contact_type: data.contact_type || "",
        contact_status: data.contact_status || "",
        is_active: data.is_active ?? true,
      });

      if (data.emails) {
        setEmails(
          data.emails.map((e: any) => ({
            ...e,
            _isNew: false,
            _isDeleted: false,
            _isDirty: false,
          }))
        );
      }
      if (data.phones) {
        setPhones(
          data.phones.map((p: any) => ({
            ...p,
            _isNew: false,
            _isDeleted: false,
            _isDirty: false,
          }))
        );
      }
      if (data.addresses) {
        setAddresses(
          data.addresses.map((a: any) => ({
            ...a,
            _isNew: false,
            _isDeleted: false,
            _isDirty: false,
          }))
        );
      }
      if (data.urls) {
        setUrls(
          data.urls.map((u: any) => ({
            ...u,
            _isNew: false,
            _isDeleted: false,
            _isDirty: false,
          }))
        );
      }
    }
  }, [data, mode, reset]);

  // Add handlers
  const addEmail = useCallback(() => {
    setEmails((prev) => [
      ...prev,
      {
        id: -Date.now(),
        email_address: "",
        email_type: "",
        is_primary: prev.filter((e) => !e._isDeleted).length === 0,
        is_active: true,
        _isNew: true,
        _isDeleted: false,
        _isDirty: true,
      },
    ]);
    setSectionsOpen((prev) => ({ ...prev, emails: true }));
  }, []);

  const addPhone = useCallback(() => {
    setPhones((prev) => [
      ...prev,
      {
        id: -Date.now(),
        phone_number: "",
        phone_type: "",
        is_primary: prev.filter((p) => !p._isDeleted).length === 0,
        is_active: true,
        _isNew: true,
        _isDeleted: false,
        _isDirty: true,
      },
    ]);
    setSectionsOpen((prev) => ({ ...prev, phones: true }));
  }, []);

  const addAddress = useCallback(() => {
    setAddresses((prev) => [
      ...prev,
      {
        id: -Date.now(),
        address_line1: "",
        address_line2: "",
        city: "",
        state: "",
        postal_code: "",
        country: "US",
        address_type: "",
        is_primary: prev.filter((a) => !a._isDeleted).length === 0,
        is_active: true,
        _isNew: true,
        _isDeleted: false,
        _isDirty: true,
      },
    ]);
    setSectionsOpen((prev) => ({ ...prev, addresses: true }));
  }, []);

  const addUrl = useCallback(() => {
    setUrls((prev) => [
      ...prev,
      {
        id: -Date.now(),
        url: "",
        url_type: "",
        is_primary: prev.filter((u) => !u._isDeleted).length === 0,
        is_active: true,
        _isNew: true,
        _isDeleted: false,
        _isDirty: true,
      },
    ]);
    setSectionsOpen((prev) => ({ ...prev, urls: true }));
  }, []);

  // Update/Delete handlers
  const updateEmailRecord = useCallback(
    (id: number, field: keyof EmailRecord, value: any) => {
      setEmails((prev) =>
        prev.map((e) => (e.id === id ? { ...e, [field]: value, _isDirty: true } : e))
      );
    },
    []
  );

  const deleteEmailRecord = useCallback((id: number) => {
    setEmails((prev) => prev.map((e) => (e.id === id ? { ...e, _isDeleted: true } : e)));
  }, []);

  const updatePhoneRecord = useCallback(
    (id: number, field: keyof PhoneRecord, value: any) => {
      setPhones((prev) =>
        prev.map((p) => (p.id === id ? { ...p, [field]: value, _isDirty: true } : p))
      );
    },
    []
  );

  const deletePhoneRecord = useCallback((id: number) => {
    setPhones((prev) => prev.map((p) => (p.id === id ? { ...p, _isDeleted: true } : p)));
  }, []);

  const updateAddressRecord = useCallback(
    (id: number, field: keyof AddressRecord, value: any) => {
      setAddresses((prev) =>
        prev.map((a) => (a.id === id ? { ...a, [field]: value, _isDirty: true } : a))
      );
    },
    []
  );

  const deleteAddressRecord = useCallback((id: number) => {
    setAddresses((prev) =>
      prev.map((a) => (a.id === id ? { ...a, _isDeleted: true } : a))
    );
  }, []);

  const updateUrlRecord = useCallback(
    (id: number, field: keyof UrlRecord, value: any) => {
      setUrls((prev) =>
        prev.map((u) => (u.id === id ? { ...u, [field]: value, _isDirty: true } : u))
      );
    },
    []
  );

  const deleteUrlRecord = useCallback((id: number) => {
    setUrls((prev) => prev.map((u) => (u.id === id ? { ...u, _isDeleted: true } : u)));
  }, []);

  // Form submission
  const onSubmit = async (formData: FormData) => {
    try {
      const apiData = mapRefsFormToApi(formData);
      let contactId: number;

      if (mode === "edit" && data?.id) {
        await updateContact(data.id, apiData as UpdateContactRequest);
        contactId = data.id;
        dispatch(showToast({ message: "Contact updated successfully", type: "success" }));
      } else {
        const response = await createContact(apiData as CreateContactRequest);
        contactId = response.id;
        dispatch(showToast({ message: "Contact created successfully", type: "success" }));
      }

      await saveCommunicationRecords(contactId);

      if (onSaved) onSaved();
    } catch (error: any) {
      dispatch(
        showToast({ message: error.message || "Failed to save contact", type: "error" })
      );
    }
  };

  const saveCommunicationRecords = async (contactId: number) => {
    // Save emails
    for (const email of emails) {
      if (email._isDeleted && !email._isNew && email.id > 0) {
        await deleteEmail(email.id);
      } else if (email._isNew && !email._isDeleted && email.email_address) {
        await createEmail({
          contact: contactId,
          email_address: email.email_address,
          email_type: email.email_type,
          is_primary: email.is_primary,
          is_active: email.is_active,
        } as CreateEmailRequest);
      } else if (email._isDirty && !email._isNew && !email._isDeleted && email.id > 0) {
        await updateEmail(email.id, {
          email_address: email.email_address,
          email_type: email.email_type,
          is_primary: email.is_primary,
          is_active: email.is_active,
        } as UpdateEmailRequest);
      }
    }

    // Save phones
    for (const phone of phones) {
      if (phone._isDeleted && !phone._isNew && phone.id > 0) {
        await deletePhone(phone.id);
      } else if (phone._isNew && !phone._isDeleted && phone.phone_number) {
        await createPhone({
          contact: contactId,
          phone_number: phone.phone_number,
          phone_type: phone.phone_type,
          is_primary: phone.is_primary,
          is_active: phone.is_active,
        } as CreatePhoneRequest);
      } else if (phone._isDirty && !phone._isNew && !phone._isDeleted && phone.id > 0) {
        await updatePhone(phone.id, {
          phone_number: phone.phone_number,
          phone_type: phone.phone_type,
          is_primary: phone.is_primary,
          is_active: phone.is_active,
        });
      }
    }

    // Save addresses
    for (const address of addresses) {
      if (address._isDeleted && !address._isNew && address.id > 0) {
        await deleteAddress(address.id);
      } else if (address._isNew && !address._isDeleted && address.address_line1) {
        await createAddress({
          contact: contactId,
          address_line1: address.address_line1,
          address_line2: address.address_line2,
          city: address.city,
          state: address.state,
          postal_code: address.postal_code,
          country: address.country,
          address_type: address.address_type,
          is_primary: address.is_primary,
          is_active: address.is_active,
        } as CreateAddressRequest);
      } else if (
        address._isDirty &&
        !address._isNew &&
        !address._isDeleted &&
        address.id > 0
      ) {
        await updateAddress(address.id, {
          address_line1: address.address_line1,
          address_line2: address.address_line2,
          city: address.city,
          state: address.state,
          postal_code: address.postal_code,
          country: address.country,
          address_type: address.address_type,
          is_primary: address.is_primary,
          is_active: address.is_active,
        });
      }
    }

    // Save URLs
    for (const url of urls) {
      if (url._isDeleted && !url._isNew && url.id > 0) {
        await deleteUrl(url.id);
      } else if (url._isNew && !url._isDeleted && url.url) {
        await createUrl({
          contact: contactId,
          url: url.url,
          url_type: url.url_type,
          is_primary: url.is_primary,
          is_active: url.is_active,
        } as CreateUrlRequest);
      } else if (url._isDirty && !url._isNew && !url._isDeleted && url.id > 0) {
        await updateUrl(url.id, {
          url: url.url,
          url_type: url.url_type,
          is_primary: url.is_primary,
          is_active: url.is_active,
        });
      }
    }
  };

  const isViewMode = mode === "view";

  // Compact input styling
  const inputClass = "h-6 text-xs py-0.5 px-1.5";
  const selectClass =
    "h-6 text-xs py-0.5 px-1.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800";

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Contact"
              : mode === "view"
                ? "View Contact"
                : "Contact Detail"
          }
        />
      )}

      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-2 pb-1.5 border-b border-slate-200 dark:border-slate-700">
            <h3 className="text-xs font-semibold text-slate-800 dark:text-white">
              {mode === "edit"
                ? "Edit Contact"
                : mode === "view"
                  ? "View Contact"
                  : "Add New Contact"}
            </h3>
            {onCancelInline && (
              <button
                type="button"
                onClick={onCancelInline}
                className="text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 text-xs"
              >
                ✕
              </button>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-2">
          {/* Row 1: Prefix, First, Middle */}
          <div className="grid grid-cols-3 gap-x-3 gap-y-1">
            <InlineField label="Prefix">
              <Controller
                name="prefix"
                control={control}
                render={({ field }) => (
                  <DropDown
                    {...field}
                    options={prefixOptions}
                    disabled={isViewMode}
                    className={inputClass}
                  />
                )}
              />
            </InlineField>
            <InlineField label="First" required error={errors.first_name?.message}>
              <Controller
                name="first_name"
                control={control}
                render={({ field }) => (
                  <Input {...field} disabled={isViewMode} className={inputClass} />
                )}
              />
            </InlineField>
            <InlineField label="Middle">
              <Controller
                name="middle_name"
                control={control}
                render={({ field }) => (
                  <Input {...field} disabled={isViewMode} className={inputClass} />
                )}
              />
            </InlineField>

            {/* Row 2: Last, Suffix, Nickname */}
            <InlineField label="Last" required error={errors.last_name?.message}>
              <Controller
                name="last_name"
                control={control}
                render={({ field }) => (
                  <Input {...field} disabled={isViewMode} className={inputClass} />
                )}
              />
            </InlineField>
            <InlineField label="Suffix">
              <Controller
                name="suffix"
                control={control}
                render={({ field }) => (
                  <DropDown
                    {...field}
                    options={suffixOptions}
                    disabled={isViewMode}
                    className={inputClass}
                  />
                )}
              />
            </InlineField>
            <InlineField label="Nickname">
              <Controller
                name="nickname"
                control={control}
                render={({ field }) => (
                  <Input {...field} disabled={isViewMode} className={inputClass} />
                )}
              />
            </InlineField>

            {/* Row 3: Job Title, Department, Type */}
            <InlineField label="Job Title">
              <Controller
                name="job_title"
                control={control}
                render={({ field }) => (
                  <Input {...field} disabled={isViewMode} className={inputClass} />
                )}
              />
            </InlineField>
            <InlineField label="Dept">
              <Controller
                name="department"
                control={control}
                render={({ field }) => (
                  <Input {...field} disabled={isViewMode} className={inputClass} />
                )}
              />
            </InlineField>
            <InlineField label="Type">
              <Controller
                name="contact_type"
                control={control}
                render={({ field }) => (
                  <DropDown
                    {...field}
                    options={contactTypeOptions}
                    disabled={isViewMode}
                    className={inputClass}
                  />
                )}
              />
            </InlineField>

            {/* Row 4: Status, Active */}
            <InlineField label="Status">
              <Controller
                name="contact_status"
                control={control}
                render={({ field }) => (
                  <DropDown
                    {...field}
                    options={contactStatusOptions}
                    disabled={isViewMode}
                    className={inputClass}
                  />
                )}
              />
            </InlineField>
            <InlineField label="Active">
              <Controller
                name="is_active"
                control={control}
                render={({ field }) => (
                  <Checkbox
                    checked={field.value}
                    onChange={field.onChange}
                    disabled={isViewMode}
                  />
                )}
              />
            </InlineField>
          </div>

          {/* Communication Sections */}
          <div className="space-y-1.5 pt-1.5 border-t border-slate-200 dark:border-slate-700">
            {/* Emails */}
            <div>
              <SectionHeader
                icon={<FaEnvelope className="w-2.5 h-2.5" />}
                title="Emails"
                count={activeEmailCount}
                isOpen={sectionsOpen.emails}
                onToggle={() => toggleSection("emails")}
                onAdd={!isViewMode ? addEmail : undefined}
              />
              {sectionsOpen.emails && (
                <div className="mt-0.5 space-y-0.5">
                  {emails
                    .filter((e) => !e._isDeleted)
                    .map((email) => (
                      <InlineRow
                        key={email.id}
                        onDelete={
                          !isViewMode ? () => deleteEmailRecord(email.id) : undefined
                        }
                        isPrimary={email.is_primary}
                      >
                        <input
                          type="email"
                          value={email.email_address}
                          onChange={(e) =>
                            updateEmailRecord(email.id, "email_address", e.target.value)
                          }
                          placeholder="email@example.com"
                          disabled={isViewMode}
                          className="flex-1 min-w-[160px] h-6 text-xs px-1.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800"
                        />
                        <select
                          value={email.email_type}
                          onChange={(e) =>
                            updateEmailRecord(email.id, "email_type", e.target.value)
                          }
                          disabled={isViewMode}
                          className={`${selectClass} w-20`}
                        >
                          <option value="">Type</option>
                          {emailTypeOptions.map((opt: any) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                        <label className="flex items-center gap-0.5 text-[10px] text-slate-500">
                          <input
                            type="checkbox"
                            checked={email.is_primary}
                            onChange={(e) =>
                              updateEmailRecord(email.id, "is_primary", e.target.checked)
                            }
                            disabled={isViewMode}
                            className="w-3 h-3"
                          />
                          Pri
                        </label>
                      </InlineRow>
                    ))}
                  {activeEmailCount === 0 && (
                    <p className="text-[10px] text-slate-400 px-2 py-0.5">No emails</p>
                  )}
                </div>
              )}
            </div>

            {/* Phones */}
            <div>
              <SectionHeader
                icon={<FaPhone className="w-2.5 h-2.5" />}
                title="Phones"
                count={activePhoneCount}
                isOpen={sectionsOpen.phones}
                onToggle={() => toggleSection("phones")}
                onAdd={!isViewMode ? addPhone : undefined}
              />
              {sectionsOpen.phones && (
                <div className="mt-0.5 space-y-0.5">
                  {phones
                    .filter((p) => !p._isDeleted)
                    .map((phone) => (
                      <InlineRow
                        key={phone.id}
                        onDelete={
                          !isViewMode ? () => deletePhoneRecord(phone.id) : undefined
                        }
                        isPrimary={phone.is_primary}
                      >
                        <input
                          type="tel"
                          value={phone.phone_number}
                          onChange={(e) =>
                            updatePhoneRecord(phone.id, "phone_number", e.target.value)
                          }
                          placeholder="(555) 123-4567"
                          disabled={isViewMode}
                          className="flex-1 min-w-[120px] h-6 text-xs px-1.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800"
                        />
                        <select
                          value={phone.phone_type}
                          onChange={(e) =>
                            updatePhoneRecord(phone.id, "phone_type", e.target.value)
                          }
                          disabled={isViewMode}
                          className={`${selectClass} w-20`}
                        >
                          <option value="">Type</option>
                          {phoneTypeOptions.map((opt: any) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                        <label className="flex items-center gap-0.5 text-[10px] text-slate-500">
                          <input
                            type="checkbox"
                            checked={phone.is_primary}
                            onChange={(e) =>
                              updatePhoneRecord(phone.id, "is_primary", e.target.checked)
                            }
                            disabled={isViewMode}
                            className="w-3 h-3"
                          />
                          Pri
                        </label>
                      </InlineRow>
                    ))}
                  {activePhoneCount === 0 && (
                    <p className="text-[10px] text-slate-400 px-2 py-0.5">No phones</p>
                  )}
                </div>
              )}
            </div>

            {/* Addresses */}
            <div>
              <SectionHeader
                icon={<FaMapMarkerAlt className="w-2.5 h-2.5" />}
                title="Addresses"
                count={activeAddressCount}
                isOpen={sectionsOpen.addresses}
                onToggle={() => toggleSection("addresses")}
                onAdd={!isViewMode ? addAddress : undefined}
              />
              {sectionsOpen.addresses && (
                <div className="mt-0.5 space-y-1">
                  {addresses
                    .filter((a) => !a._isDeleted)
                    .map((address) => (
                      <div
                        key={address.id}
                        className={`p-1.5 rounded border ${address.is_primary ? "border-blue-200 bg-blue-50/30 dark:border-blue-800 dark:bg-blue-900/10" : "border-slate-200 dark:border-slate-700"}`}
                      >
                        <div className="flex justify-between items-center mb-1">
                          <select
                            value={address.address_type}
                            onChange={(e) =>
                              updateAddressRecord(
                                address.id,
                                "address_type",
                                e.target.value
                              )
                            }
                            disabled={isViewMode}
                            className={`${selectClass} w-20`}
                          >
                            <option value="">Type</option>
                            {addressTypeOptions.map((opt: any) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                          <div className="flex items-center gap-1.5">
                            <label className="flex items-center gap-0.5 text-[10px] text-slate-500">
                              <input
                                type="checkbox"
                                checked={address.is_primary}
                                onChange={(e) =>
                                  updateAddressRecord(
                                    address.id,
                                    "is_primary",
                                    e.target.checked
                                  )
                                }
                                disabled={isViewMode}
                                className="w-3 h-3"
                              />
                              Pri
                            </label>
                            {!isViewMode && (
                              <button
                                type="button"
                                onClick={() => deleteAddressRecord(address.id)}
                                className="p-0.5 text-red-500 hover:bg-red-100 rounded"
                              >
                                <FaTrash className="w-2.5 h-2.5" />
                              </button>
                            )}
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-0.5">
                          <input
                            value={address.address_line1}
                            onChange={(e) =>
                              updateAddressRecord(
                                address.id,
                                "address_line1",
                                e.target.value
                              )
                            }
                            placeholder="Address 1"
                            disabled={isViewMode}
                            className="col-span-2 h-5 text-[11px] px-1.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800"
                          />
                          <input
                            value={address.address_line2}
                            onChange={(e) =>
                              updateAddressRecord(
                                address.id,
                                "address_line2",
                                e.target.value
                              )
                            }
                            placeholder="Address 2"
                            disabled={isViewMode}
                            className="col-span-2 h-5 text-[11px] px-1.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800"
                          />
                          <input
                            value={address.city}
                            onChange={(e) =>
                              updateAddressRecord(address.id, "city", e.target.value)
                            }
                            placeholder="City"
                            disabled={isViewMode}
                            className="h-5 text-[11px] px-1.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800"
                          />
                          <div className="flex gap-0.5">
                            <input
                              value={address.state}
                              onChange={(e) =>
                                updateAddressRecord(address.id, "state", e.target.value)
                              }
                              placeholder="ST"
                              disabled={isViewMode}
                              className="w-10 h-5 text-[11px] px-1 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800"
                            />
                            <input
                              value={address.postal_code}
                              onChange={(e) =>
                                updateAddressRecord(
                                  address.id,
                                  "postal_code",
                                  e.target.value
                                )
                              }
                              placeholder="ZIP"
                              disabled={isViewMode}
                              className="flex-1 h-5 text-[11px] px-1 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800"
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  {activeAddressCount === 0 && (
                    <p className="text-[10px] text-slate-400 px-2 py-0.5">No addresses</p>
                  )}
                </div>
              )}
            </div>

            {/* URLs */}
            <div>
              <SectionHeader
                icon={<FaGlobe className="w-2.5 h-2.5" />}
                title="URLs"
                count={activeUrlCount}
                isOpen={sectionsOpen.urls}
                onToggle={() => toggleSection("urls")}
                onAdd={!isViewMode ? addUrl : undefined}
              />
              {sectionsOpen.urls && (
                <div className="mt-0.5 space-y-0.5">
                  {urls
                    .filter((u) => !u._isDeleted)
                    .map((url) => (
                      <InlineRow
                        key={url.id}
                        onDelete={!isViewMode ? () => deleteUrlRecord(url.id) : undefined}
                        isPrimary={url.is_primary}
                      >
                        <input
                          type="url"
                          value={url.url}
                          onChange={(e) =>
                            updateUrlRecord(url.id, "url", e.target.value)
                          }
                          placeholder="https://example.com"
                          disabled={isViewMode}
                          className="flex-1 min-w-[180px] h-6 text-xs px-1.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800"
                        />
                        <select
                          value={url.url_type}
                          onChange={(e) =>
                            updateUrlRecord(url.id, "url_type", e.target.value)
                          }
                          disabled={isViewMode}
                          className={`${selectClass} w-20`}
                        >
                          <option value="">Type</option>
                          {urlTypeOptions.map((opt: any) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                        <label className="flex items-center gap-0.5 text-[10px] text-slate-500">
                          <input
                            type="checkbox"
                            checked={url.is_primary}
                            onChange={(e) =>
                              updateUrlRecord(url.id, "is_primary", e.target.checked)
                            }
                            disabled={isViewMode}
                            className="w-3 h-3"
                          />
                          Pri
                        </label>
                      </InlineRow>
                    ))}
                  {activeUrlCount === 0 && (
                    <p className="text-[10px] text-slate-400 px-2 py-0.5">No URLs</p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Notes */}
          <div className="pt-1.5 border-t border-slate-200 dark:border-slate-700">
            <InlineField label="Notes" labelWidth="w-14">
              <Controller
                name="notes"
                control={control}
                render={({ field }) => (
                  <textarea
                    {...field}
                    disabled={isViewMode}
                    rows={2}
                    className="w-full text-xs px-1.5 py-1 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 resize-none"
                  />
                )}
              />
            </InlineField>
          </div>

          {/* Action Buttons */}
          {!isViewMode && (
            <div className="flex justify-end gap-1.5 pt-2 border-t border-slate-200 dark:border-slate-700">
              {onCancelInline && (
                <button
                  type="button"
                  onClick={onCancelInline}
                  className="px-2 py-1 text-[11px] font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded"
                >
                  Cancel
                </button>
              )}
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex items-center gap-1 px-3 py-1 text-[11px] font-medium text-white bg-blue-600 hover:bg-blue-700 rounded disabled:opacity-50"
              >
                <FaSave className="w-2.5 h-2.5" />
                {isSubmitting ? "Saving..." : "Save"}
              </button>
            </div>
          )}
        </form>
      </ComponentCard>
    </>
  );
}
