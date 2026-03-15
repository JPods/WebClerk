/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect, useMemo, useState, useCallback } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
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
import { FaEdit, FaPlus, FaSave, FaTrash, FaEnvelope, FaPhone, FaMapMarkerAlt, FaGlobe, FaChevronDown, FaChevronRight } from "react-icons/fa";
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
import {
  CreatePhoneRequest,
} from "@/apps/communications/models/phone/types/phoneType";
import {
  createAddress,
  updateAddress,
  deleteAddress,
} from "@/apps/communications/models/address/services/addressApi";
import {
  CreateAddressRequest,
} from "@/apps/communications/models/address/types/addressType";
import {
  createDomain,
  updateDomain,
  deleteDomain,
} from "@/apps/communications/models/domain/services/domainApi";
import {
  CreateDomainRequest,
} from "@/apps/communications/models/domain/types/domainType";
import { useDetailFieldAccess } from "@/hooks/useDetailFieldAccess";

// ------------------------------------
// Communication Table Types
// ------------------------------------
interface EmailRecord {
  id: number;
  address: string;
  name?: string;
  type?: string;
  is_primary?: boolean;
  is_verified?: boolean;
}

interface PhoneRecord {
  id: number;
  number: string;
  name?: string;
  type?: string;
  is_primary?: boolean;
}

interface AddressRecord {
  id: number;
  name?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  type?: string;
}

interface DomainRecord {
  id: number;
  domain: string;
  name?: string;
  is_primary?: boolean;
}

// ------------------------------------
// Communication Table Component
// ------------------------------------
interface CommunicationTableProps<T> {
  title: string;
  icon: React.ReactNode;
  data: T[];
  columns: { key: keyof T | string; label: string; render?: (item: T) => React.ReactNode }[];
  onAdd: () => void;
  onEdit: (item: T) => void;
  onDelete: (item: T) => void;
  onSave: (item: T) => void;
  editingItem: T | null;
  onEditChange: (field: keyof T, value: any) => void;
  onCancelEdit: () => void;
  disabled?: boolean;
}

function CommunicationTable<T extends { id: number }>({
  title,
  icon,
  data,
  columns,
  onAdd,
  onEdit,
  onDelete,
  onSave,
  editingItem,
  onEditChange,
  onCancelEdit,
  disabled = false,
}: CommunicationTableProps<T>) {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="border rounded-lg dark:border-slate-700 overflow-hidden mb-4">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-800 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          {isExpanded ? <FaChevronDown className="text-slate-400" /> : <FaChevronRight className="text-slate-400" />}
          {icon}
          <span className="font-semibold text-slate-700 dark:text-slate-200">{title}</span>
          <span className="text-xs text-slate-500 dark:text-slate-400">({data.length})</span>
        </div>
        {!disabled && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onAdd();
            }}
            className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-white bg-blue-500 rounded hover:bg-blue-600"
          >
            <FaPlus className="w-3 h-3" /> Add
          </button>
        )}
      </div>

      {/* Table Content */}
      {isExpanded && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-100 dark:bg-slate-700">
              <tr>
                {columns.map((col) => (
                  <th key={String(col.key)} className="px-4 py-2 text-left text-xs font-medium text-slate-600 dark:text-slate-300 uppercase">
                    {col.label}
                  </th>
                ))}
                {!disabled && <th className="px-4 py-2 text-right text-xs font-medium text-slate-600 dark:text-slate-300 uppercase w-24">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {data.length === 0 ? (
                <tr>
                  <td colSpan={columns.length + 1} className="px-4 py-6 text-center text-slate-400 dark:text-slate-500">
                    No records found
                  </td>
                </tr>
              ) : (
                data.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                    {editingItem && editingItem.id === item.id ? (
                      // Editing row
                      <>
                        {columns.map((col) => (
                          <td key={String(col.key)} className="px-4 py-2">
                            <input
                              type="text"
                              value={String((editingItem as any)[col.key] ?? '')}
                              onChange={(e) => onEditChange(col.key as keyof T, e.target.value)}
                              className="w-full px-2 py-1 text-sm border rounded dark:bg-slate-700 dark:border-slate-600 dark:text-white"
                            />
                          </td>
                        ))}
                        <td className="px-4 py-2 text-right">
                          <div className="flex justify-end gap-2">
                            <button
                              type="button"
                              onClick={() => onSave(editingItem)}
                              className="p-1 text-green-600 hover:text-green-700"
                              title="Save"
                            >
                              <FaSave />
                            </button>
                            <button
                              type="button"
                              onClick={onCancelEdit}
                              className="p-1 text-slate-500 hover:text-slate-700"
                              title="Cancel"
                            >
                              ✕
                            </button>
                          </div>
                        </td>
                      </>
                    ) : (
                      // View row
                      <>
                        {columns.map((col) => (
                          <td key={String(col.key)} className="px-4 py-2 text-slate-700 dark:text-slate-300">
                            {col.render ? col.render(item) : String((item as any)[col.key] ?? '--')}
                          </td>
                        ))}
                        {!disabled && (
                          <td className="px-4 py-2 text-right">
                            <div className="flex justify-end gap-2">
                              <button
                                type="button"
                                onClick={() => onEdit(item)}
                                className="p-1 text-blue-600 hover:text-blue-700"
                                title="Edit"
                              >
                                <FaEdit />
                              </button>
                              <button
                                type="button"
                                onClick={() => onDelete(item)}
                                className="p-1 text-red-600 hover:text-red-700"
                                title="Delete"
                              >
                                <FaTrash />
                              </button>
                            </div>
                          </td>
                        )}
                      </>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const CONTACT_DETAIL_FIELDS = [
  "email",
  "password",
  "cnf_password",
  "name_first",
  "name_last",
  "name_middle",
  "name_prefix",
  "name_suffix",
  "company",
  "title",
  "department",
  "customer_id",
  "rep_id",
  "vendor_id",
  "employee_id",
  "manufacturer_id",
  "other_id",
  "role",
  "is_active",
  "is_staff",
] as const;
/* ----------------------------------
   Types
---------------------------------- */

const normalizeNumber = (value: any): number | undefined => {
  if (value === null || value === undefined || value === "") return undefined;
  const num = Number(value);
  return isNaN(num) ? undefined : num;
};
export default function ContactDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ContactAddProps) {
  // Communication records state
  const [emails, setEmails] = useState<EmailRecord[]>([]);
  const [phones, setPhones] = useState<PhoneRecord[]>([]);
  const [addresses, setAddresses] = useState<AddressRecord[]>([]);
  const [domains, setDomains] = useState<DomainRecord[]>([]);
  
  // Editing state for each type
  const [editingEmail, setEditingEmail] = useState<EmailRecord | null>(null);
  const [editingPhone, setEditingPhone] = useState<PhoneRecord | null>(null);
  const [editingAddress, setEditingAddress] = useState<AddressRecord | null>(null);
  const [editingDomain, setEditingDomain] = useState<DomainRecord | null>(null);

  const dispatch = useDispatch();
  const location = useLocation();
  const routeState = (location.state as any) || {};

  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;
  const contactFieldNames = useMemo(() => CONTACT_DETAIL_FIELDS.slice(), []);
  const {
    isAdmin,
    loading: fieldAccessLoading,
    saving: fieldAccessSaving,
    error: fieldAccessError,
    config: fieldAccessConfig,
    isFieldVisible,
    isFieldReadOnly,
    setFieldVisible,
    setFieldReadOnly,
    resetConfig: resetFieldAccess,
    saveConfig: saveFieldAccess,
    isDirty: fieldAccessDirty,
  } = useDetailFieldAccess("contact", contactFieldNames);

  const isFieldDisabled = (fieldName: string) => {
    if (mode === "view") return true;
    if (!isAdmin && isFieldReadOnly(fieldName)) return true;
    return false;
  };

  const shouldRenderField = (fieldName: string) => {
    if (isAdmin) return true;
    return isFieldVisible(fieldName);
  };

  const fieldAccessBusy = fieldAccessLoading || fieldAccessSaving;

  /* ----------------------------------
     React Hook Form
  ---------------------------------- */
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(
      mode === "edit" ? updateContactSchema : contactSchema
    ),
    defaultValues: {
      refs: {
        tags: [],
        categories: [],
        keywords: [],
        depends_on: {},
        related_ids: [],
        links: {
          rep: [],
          item: [],
          email: [],
          order: [],
          phone: [],
          domain: [],
          contact: [],
          customer: [],
          document: [],
          address: [],
          manufacturer: [],
          project: [],
          vendor: [],
        },
      },
    },
  });

  /* ----------------------------------
     Load Edit Data
  ---------------------------------- */
  useEffect(() => {
    if (!data) {
      reset({});
      return;
    }

    // Normalize ALL fields that must be strings
    const normalizedContact = {
      ...data,

      customer_id: normalizeNumber(data.customer_id),
      rep_id: normalizeNumber(data.rep_id),
      vendor_id: normalizeNumber(data.vendor_id),
      employee_id: normalizeNumber(data.employee_id),
      manufacturer_id: normalizeNumber(data.manufacturer_id),
      other_id: normalizeNumber(data.other_id),

      refs: {
        ...data.refs,
        links: {
          ...data.refs?.links,

          // EMAIL
          email: (data.refs?.links?.email ?? []).map((e: any) => ({
            id: e.id ?? 0,
            name: e.name ?? "",
            address: e.address ?? "",
          })),

          // PHONE
          phone: (data.refs?.links?.phone ?? []).map((p: any) => ({
            id: p.id ?? 0,
            name: p.name ?? "",
            number: p.number ?? "",
          })),

          // ADDRESS — REQUIRED FIX
          address: (data.refs?.links?.address ?? []).map((l: any) => ({
            id: l.id ?? 0,
            name: l.name ?? "",
            address: l.address ?? "",
          })),

          // String-only refs
          rep: data.refs?.links?.rep ?? [],
          item: data.refs?.links?.item ?? [],
          order: data.refs?.links?.order ?? [],
          domain: data.refs?.links?.domain ?? [],
          contact: data.refs?.links?.contact ?? [],
          customer: data.refs?.links?.customer ?? [],
          document: data.refs?.links?.document ?? [],
          manufacturer: data.refs?.links?.manufacturer ?? [],
          project: data.refs?.links?.project ?? [],
          vendor: data.refs?.links?.vendor ?? [],
        },
      },
    };

    reset(normalizedContact);
    
    // Load communication records from refs.links
    if (data.refs?.links) {
      setEmails((data.refs.links.email ?? []).map((e: any) => ({
        id: e.id ?? 0,
        address: e.address ?? e.email ?? '',
        name: e.name ?? '',
        type: e.type ?? '',
        is_primary: e.is_primary ?? false,
        is_verified: e.is_verified ?? false,
      })));
      
      setPhones((data.refs.links.phone ?? []).map((p: any) => ({
        id: p.id ?? 0,
        number: p.number ?? '',
        name: p.name ?? '',
        type: p.type ?? '',
        is_primary: p.is_primary ?? false,
      })));
      
      setAddresses((data.refs.links.address ?? []).map((l: any) => ({
        id: l.id ?? 0,
        name: l.name ?? '',
        address_line1: l.address_line1 ?? l.address ?? '',
        address_line2: l.address_line2 ?? '',
        city: l.city ?? '',
        state: l.state ?? '',
        postal_code: l.postal_code ?? '',
        country: l.country ?? '',
        type: l.type ?? '',
      })));
      
      setDomains((data.refs.links.domain ?? []).map((d: any) => ({
        id: d.id ?? 0,
        domain: d.domain ?? d.name ?? '',
        name: d.name ?? '',
        is_primary: d.is_primary ?? false,
      })));
    }
  }, [data, reset]);

  /* ----------------------------------
     Communication Record Handlers
  ---------------------------------- */
  
  // EMAIL HANDLERS
  const handleAddEmail = useCallback(() => {
    const newEmail: EmailRecord = { id: 0, address: '', name: '', type: '', is_primary: false, is_verified: false };
    setEditingEmail(newEmail);
    setEmails(prev => [...prev, newEmail]);
  }, []);

  const handleEditEmail = useCallback((email: EmailRecord) => {
    setEditingEmail({ ...email });
  }, []);

  const handleDeleteEmail = useCallback(async (email: EmailRecord) => {
    if (!window.confirm('Delete this email?')) return;
    try {
      if (email.id > 0) {
        await deleteEmail('email', email.id);
      }
      setEmails(prev => prev.filter(e => e.id !== email.id || (e.id === 0 && e.address !== email.address)));
      dispatch(showToast({ message: 'Email deleted', type: 'success' }));
    } catch (error) {
      dispatch(showToast({ message: 'Failed to delete email', type: 'error' }));
    }
  }, [dispatch]);

  const handleSaveEmail = useCallback(async (email: EmailRecord) => {
    try {
      if (!email.address) {
        dispatch(showToast({ message: 'Email address is required', type: 'error' }));
        return;
      }
      const payload = {
        id: email.id || 0,
        email: email.address,
        name: email.name || '',
        type: email.type,
        is_primary: email.is_primary ?? false,
        is_verified: email.is_verified ?? false,
        contact_id: data?.id,
      };
      const res = email.id > 0 
        ? await updateEmail(payload as UpdateEmailRequest)
        : await createEmail(payload as CreateEmailRequest);
      
      if (res) {
        const savedId = (res as any).id || email.id;
        setEmails(prev => prev.map(e => 
          (e.id === email.id || (e.id === 0 && e.address === email.address)) 
            ? { ...email, id: savedId } 
            : e
        ));
        setEditingEmail(null);
        dispatch(showToast({ message: 'Email saved', type: 'success' }));
      }
    } catch (error) {
      dispatch(showToast({ message: 'Failed to save email', type: 'error' }));
    }
  }, [data?.id, dispatch]);

  const handleEmailChange = useCallback((field: keyof EmailRecord, value: any) => {
    setEditingEmail(prev => prev ? { ...prev, [field]: value } : null);
  }, []);

  // PHONE HANDLERS
  const handleAddPhone = useCallback(() => {
    const newPhone: PhoneRecord = { id: 0, number: '', name: '', type: '', is_primary: false };
    setEditingPhone(newPhone);
    setPhones(prev => [...prev, newPhone]);
  }, []);

  const handleEditPhone = useCallback((phone: PhoneRecord) => {
    setEditingPhone({ ...phone });
  }, []);

  const handleDeletePhone = useCallback(async (phone: PhoneRecord) => {
    if (!window.confirm('Delete this phone?')) return;
    try {
      if (phone.id > 0) {
        await deletePhone(phone.id);
      }
      setPhones(prev => prev.filter(p => p.id !== phone.id || (p.id === 0 && p.number !== phone.number)));
      dispatch(showToast({ message: 'Phone deleted', type: 'success' }));
    } catch (error) {
      dispatch(showToast({ message: 'Failed to delete phone', type: 'error' }));
    }
  }, [dispatch]);

  const handleSavePhone = useCallback(async (phone: PhoneRecord) => {
    try {
      if (!phone.number) {
        dispatch(showToast({ message: 'Phone number is required', type: 'error' }));
        return;
      }
      const payload = {
        number: phone.number,
        name: phone.name || '',
        country_code: '',
        opt_out: false,
        attention: '',
        format: '',
        contact_id: data?.id,
      };
      const res = phone.id > 0
        ? await updatePhone({ ...payload, id: String(phone.id) })
        : await createPhone(payload as CreatePhoneRequest);
      
      if (res) {
        const savedId = (res as any).id || phone.id;
        setPhones(prev => prev.map(p => 
          (p.id === phone.id || (p.id === 0 && p.number === phone.number))
            ? { ...phone, id: savedId }
            : p
        ));
        setEditingPhone(null);
        dispatch(showToast({ message: 'Phone saved', type: 'success' }));
      }
    } catch (error) {
      dispatch(showToast({ message: 'Failed to save phone', type: 'error' }));
    }
  }, [data?.id, dispatch]);

  const handlePhoneChange = useCallback((field: keyof PhoneRecord, value: any) => {
    setEditingPhone(prev => prev ? { ...prev, [field]: value } : null);
  }, []);

  // ADDRESS HANDLERS
  const handleAddAddress = useCallback(() => {
    const newAddress: AddressRecord = { id: 0, name: '', address_line1: '', city: '', state: '', postal_code: '', country: '', type: '' };
    setEditingAddress(newAddress);
    setAddresses(prev => [...prev, newAddress]);
  }, []);

  const handleEditAddress = useCallback((addr: AddressRecord) => {
    setEditingAddress({ ...addr });
  }, []);

  const handleDeleteAddress = useCallback(async (addr: AddressRecord) => {
    if (!window.confirm('Delete this address?')) return;
    try {
      if (addr.id > 0) {
        await deleteAddress(addr.id);
      }
      setAddresses(prev => prev.filter(l => l.id !== addr.id || (l.id === 0 && l.address_line1 !== addr.address_line1)));
      dispatch(showToast({ message: 'Address deleted', type: 'success' }));
    } catch (error) {
      dispatch(showToast({ message: 'Failed to delete address', type: 'error' }));
    }
  }, [dispatch]);

  const handleSaveAddress = useCallback(async (addr: AddressRecord) => {
    try {
      const payload = {
        address1: addr.address_line1 || '',
        address2: addr.address_line2 || '',
        address_type: addr.type || '',
        full: '',
        city: addr.city || '',
        state: addr.state || '',
        zip: addr.postal_code || '',
        country: addr.country || '',
        latitude: 0,
        longitude: 0,
        contact_id: data?.id,
      };
      const res = addr.id > 0
        ? await updateAddress({ ...payload, id: String(addr.id) })
        : await createAddress(payload as CreateAddressRequest);
      
      if (res) {
        const savedId = (res as any).id || addr.id;
        setAddresses(prev => prev.map(l => 
          (l.id === addr.id || (l.id === 0 && l.address_line1 === addr.address_line1))
            ? { ...addr, id: savedId }
            : l
        ));
        setEditingAddress(null);
        dispatch(showToast({ message: 'Address saved', type: 'success' }));
      }
    } catch (error) {
      dispatch(showToast({ message: 'Failed to save address', type: 'error' }));
    }
  }, [data?.id, dispatch]);

  const handleAddressChange = useCallback((field: keyof AddressRecord, value: any) => {
    setEditingAddress(prev => prev ? { ...prev, [field]: value } : null);
  }, []);

  // DOMAIN HANDLERS
  const handleAddDomain = useCallback(() => {
    const newDomain: DomainRecord = { id: 0, domain: '', name: '', is_primary: false };
    setEditingDomain(newDomain);
    setDomains(prev => [...prev, newDomain]);
  }, []);

  const handleEditDomain = useCallback((domain: DomainRecord) => {
    setEditingDomain({ ...domain });
  }, []);

  const handleDeleteDomain = useCallback(async (domain: DomainRecord) => {
    if (!window.confirm('Delete this domain?')) return;
    try {
      if (domain.id > 0) {
        await deleteDomain(domain.id);
      }
      setDomains(prev => prev.filter(d => d.id !== domain.id || (d.id === 0 && d.domain !== domain.domain)));
      dispatch(showToast({ message: 'Domain deleted', type: 'success' }));
    } catch (error) {
      dispatch(showToast({ message: 'Failed to delete domain', type: 'error' }));
    }
  }, [dispatch]);

  const handleSaveDomain = useCallback(async (domain: DomainRecord) => {
    try {
      if (!domain.domain) {
        dispatch(showToast({ message: 'Domain is required', type: 'error' }));
        return;
      }
      const payload = {
        path: domain.domain,
        type: '',
        contact_id: data?.id,
      };
      const res = domain.id > 0
        ? await updateDomain({ ...payload, id: String(domain.id) })
        : await createDomain(payload as CreateDomainRequest);
      
      if (res) {
        const savedId = (res as any).id || domain.id;
        setDomains(prev => prev.map(d => 
          (d.id === domain.id || (d.id === 0 && d.domain === domain.domain))
            ? { ...domain, id: savedId }
            : d
        ));
        setEditingDomain(null);
        dispatch(showToast({ message: 'Domain saved', type: 'success' }));
      }
    } catch (error) {
      dispatch(showToast({ message: 'Failed to save domain', type: 'error' }));
    }
  }, [data?.id, dispatch]);

  const handleDomainChange = useCallback((field: keyof DomainRecord, value: any) => {
    setEditingDomain(prev => prev ? { ...prev, [field]: value } : null);
  }, []);

  /* ----------------------------------
     Submit
  ---------------------------------- */
  console.log("errors", errors);

  const onSubmit = async (
    formData:
      | z.infer<typeof contactSchema>
      | z.infer<typeof updateContactSchema>
  ) => {
    console.log("formData", formData);
    try {
      const mappedRefs = formData.refs
        ? mapRefsFormToApi(formData.refs)
        : undefined;
      const basePayload = {
        email: formData.email,
        name_first: formData.name_first,
        name_last: formData.name_last,
        name_middle: formData.name_middle,
        name_prefix: formData.name_prefix,
        name_suffix: formData.name_suffix,
        company: formData.company,
        title: formData.title,
        department: formData.department,
        role: formData.role,
        is_active: formData.is_active,
        is_staff: formData.is_staff,
        customer_id: formData.customer_id,
        rep_id: formData.rep_id,
        vendor_id: formData.vendor_id,
        employee_id: formData.employee_id,
        manufacturer_id: formData.manufacturer_id,
        other_id: formData.other_id,
        refs: mappedRefs,
      };

      const payload =
        mode === "add"
          ? {
              ...basePayload,
              password: (formData as z.infer<typeof contactSchema>).password,
              cnf_password: (formData as z.infer<typeof contactSchema>)
                .cnf_password,
            }
          : basePayload;

      const res =
        mode === "add"
          ? await createContact(payload as CreateContactRequest)
          : await updateContact({
              ...payload,
              id: data?.id,
            } as UpdateContactRequest);
      if (res) {
        dispatch(
          showToast({
            message: `Action ${
              mode === "add" ? "saved" : "updated"
            } successfully`,
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        }
      }
    } catch (error: unknown) {
      if (error instanceof Error) {
        dispatch(showToast({ message: error.message, type: "error" }));
      }
    }
  };

  const roleOptions = [
    { value: "user", label: "User" },
    { value: "admin", label: "Administrator" },
    { value: "manager", label: "Manager" },
    { value: "staff", label: "Staff" },
    { value: "guest", label: "Guest" },
  ];

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
          <div className="flex justify-between items-center mb-4">
            <h3 className=" dark:text-white text-lg font-semibold">
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
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                &times;
              </button>
            )}
          </div>
        )}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
            {shouldRenderField("email") && (
              <div>
                <Label htmlFor="email">email</Label>
                <Input
                  type="email"
                  id="email"
                  placeholder="Primary email address for login"
                  {...register("email")}
                  error={errors.email && errors.email.message ? true : false}
                  hint={errors.email && errors.email.message}
                  disabled={isFieldDisabled("email")}
                />
              </div>
            )}
          </div>
          {mode === "add" && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
                {shouldRenderField("password") && (
                  <div>
                    <Label htmlFor="password">password</Label>
                    <Input
                      type="password"
                      id="password"
                      placeholder="Password"
                      {...register("password" as any)}
                      error={
                        (errors as any).password &&
                        (errors as any).password.message
                          ? true
                          : false
                      }
                      hint={
                        (errors as any).password?.message ||
                        "Your password can't be too similar to your other personal information. Your password must contain at least 8 characters. Your password can't be a commonly used password. Your password can't be entirely numeric."
                      }
                      disabled={isFieldDisabled("password")}
                    />
                  </div>
                )}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
                {shouldRenderField("cnf_password") && (
                  <div>
                    <Label htmlFor="cnf_password">cnf_password</Label>
                    <Input
                      type="password"
                      id="cnf_password"
                      placeholder="Confirm Password"
                      {...register("cnf_password" as any)}
                      error={
                        (errors as any).cnf_password &&
                        (errors as any).cnf_password.message
                          ? true
                          : false
                      }
                      hint={
                        (errors as any).cnf_password?.message ||
                        "Enter the same password as before, for verification."
                      }
                      disabled={isFieldDisabled("cnf_password")}
                    />
                  </div>
                )}
              </div>
            </>
          )}
          <h5 className=" dark:text-white text-md font-semibold mt-6 mb-3 custom-header-inner">
            Personal info
          </h5>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
            {shouldRenderField("name_first") && (
              <div>
                <Label htmlFor="name_first">name_first</Label>
                <Input
                  type="text"
                  id="name_first"
                  placeholder="First Name"
                  {...register("name_first")}
                  error={
                    errors.name_first && errors.name_first.message
                      ? true
                      : false
                  }
                  hint={errors.name_first && errors.name_first.message}
                  disabled={isFieldDisabled("name_first")}
                />
              </div>
            )}
            {shouldRenderField("name_last") && (
              <div>
                <Label htmlFor="name_last">name_last</Label>
                <Input
                  type="text"
                  id="name_last"
                  placeholder="Last Name"
                  {...register("name_last")}
                  error={
                    errors.name_last && errors.name_last.message ? true : false
                  }
                  hint={errors.name_last && errors.name_last.message}
                  disabled={isFieldDisabled("name_last")}
                />
              </div>
            )}
            {shouldRenderField("name_middle") && (
              <div>
                <Label htmlFor="name_middle">name_middle</Label>
                <Input
                  type="text"
                  id="name_middle"
                  placeholder="Middle Name"
                  {...register("name_middle")}
                  error={
                    errors.name_middle && errors.name_middle.message
                      ? true
                      : false
                  }
                  hint={errors.name_middle && errors.name_middle.message}
                  disabled={isFieldDisabled("name_middle")}
                />
              </div>
            )}
            {shouldRenderField("name_prefix") && (
              <div>
                <Label htmlFor="name_prefix">name_prefix</Label>
                <Input
                  type="text"
                  id="name_prefix"
                  placeholder="Title (Mr., Ms., Dr.)"
                  {...register("name_prefix")}
                  error={
                    errors.name_prefix && errors.name_prefix.message
                      ? true
                      : false
                  }
                  hint={errors.name_prefix && errors.name_prefix.message}
                  disabled={isFieldDisabled("name_prefix")}
                />
              </div>
            )}
            {shouldRenderField("name_suffix") && (
              <div>
                <Label htmlFor="name_suffix">name_suffix</Label>
                <Input
                  type="text"
                  id="name_suffix"
                  placeholder="Suffix (Jr., Sr., III)"
                  {...register("name_suffix")}
                  error={
                    errors.name_suffix && errors.name_suffix.message
                      ? true
                      : false
                  }
                  hint={errors.name_suffix && errors.name_suffix.message}
                  disabled={isFieldDisabled("name_suffix")}
                />
              </div>
            )}
          </div>
          <h5 className="dark:text-white text-md font-semibold mt-6 mb-3 custom-header-inner">
            Company info
          </h5>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
            {shouldRenderField("company") && (
              <div>
                <Label htmlFor="company">company</Label>
                <Input
                  type="text"
                  id="company"
                  placeholder="Company name"
                  {...register("company")}
                  error={
                    errors.company && errors.company.message ? true : false
                  }
                  hint={errors.company && errors.company.message}
                  disabled={isFieldDisabled("company")}
                />
              </div>
            )}
            {shouldRenderField("title") && (
              <div>
                <Label htmlFor="title">title</Label>
                <Input
                  type="text"
                  id="title"
                  placeholder="Job title"
                  {...register("title")}
                  error={errors.title && errors.title.message ? true : false}
                  hint={errors.title && errors.title.message}
                  disabled={isFieldDisabled("title")}
                />
              </div>
            )}
            {shouldRenderField("department") && (
              <div>
                <Label htmlFor="department">department</Label>
                <Input
                  type="text"
                  id="department"
                  placeholder="Department"
                  {...register("department")}
                  error={
                    errors.department && errors.department.message
                      ? true
                      : false
                  }
                  hint={errors.department && errors.department.message}
                  disabled={isFieldDisabled("department")}
                />
              </div>
            )}
          </div>
          <h5 className="dark:text-white text-md font-semibold mt-6 mb-3 custom-header-inner">
            Related IDs
          </h5>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
            {shouldRenderField("customer_id") && (
              <div>
                <Label htmlFor="customer_id">customer_id</Label>
                <Input
                  type="number"
                  id="customer_id"
                  placeholder="Customer ID"
                  {...register("customer_id", {
                    setValueAs: (value) =>
                      value === "" ? undefined : Number(value),
                  })}
                  error={
                    errors.customer_id && errors.customer_id.message
                      ? true
                      : false
                  }
                  hint={errors.customer_id && errors.customer_id.message}
                  disabled={isFieldDisabled("customer_id")}
                />
              </div>
            )}
            {shouldRenderField("rep_id") && (
              <div>
                <Label htmlFor="rep_id">rep_id</Label>
                <Input
                  type="number"
                  id="rep_id"
                  placeholder="Rep ID"
                  {...register("rep_id", {
                    setValueAs: (value) =>
                      value === "" ? undefined : Number(value),
                  })}
                  error={errors.rep_id && errors.rep_id.message ? true : false}
                  hint={errors.rep_id && errors.rep_id.message}
                  disabled={isFieldDisabled("rep_id")}
                />
              </div>
            )}
            {shouldRenderField("vendor_id") && (
              <div>
                <Label htmlFor="vendor_id">vendor_id</Label>
                <Input
                  type="number"
                  id="vendor_id"
                  placeholder="Vendor ID"
                  {...register("vendor_id", {
                    setValueAs: (value) =>
                      value === "" ? undefined : Number(value),
                  })}
                  error={
                    errors.vendor_id && errors.vendor_id.message ? true : false
                  }
                  hint={errors.vendor_id && errors.vendor_id.message}
                  disabled={isFieldDisabled("vendor_id")}
                />
              </div>
            )}
            {shouldRenderField("employee_id") && (
              <div>
                <Label htmlFor="employee_id">employee_id</Label>
                <Input
                  type="number"
                  id="employee_id"
                  placeholder="Employee ID"
                  {...register("employee_id", {
                    setValueAs: (value) =>
                      value === "" ? undefined : Number(value),
                  })}
                  error={
                    errors.employee_id && errors.employee_id.message
                      ? true
                      : false
                  }
                  hint={errors.employee_id && errors.employee_id.message}
                  disabled={isFieldDisabled("employee_id")}
                />
              </div>
            )}
            {shouldRenderField("manufacturer_id") && (
              <div>
                <Label htmlFor="manufacturer_id">manufacturer_id</Label>
                <Input
                  type="number"
                  id="manufacturer_id"
                  placeholder="Manufacturer ID"
                  {...register("manufacturer_id", {
                    setValueAs: (value) =>
                      value === "" ? undefined : Number(value),
                  })}
                  error={
                    errors.manufacturer_id && errors.manufacturer_id.message
                      ? true
                      : false
                  }
                  hint={
                    errors.manufacturer_id && errors.manufacturer_id.message
                  }
                  disabled={isFieldDisabled("manufacturer_id")}
                />
              </div>
            )}
            {shouldRenderField("other_id") && (
              <div>
                <Label htmlFor="other_id">other_id</Label>
                <Input
                  type="number"
                  id="other_id"
                  placeholder="Other ID"
                  {...register("other_id", {
                    setValueAs: (value) =>
                      value === "" ? undefined : Number(value),
                  })}
                  error={
                    errors.other_id && errors.other_id.message ? true : false
                  }
                  hint={errors.other_id && errors.other_id.message}
                  disabled={isFieldDisabled("other_id")}
                />
              </div>
            )}
          </div>
          <h5 className=" dark:text-white text-md font-semibold mt-6 mb-3 custom-header-inner">
            Permissions
          </h5>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
            {shouldRenderField("role") && (
              <div>
                <Label htmlFor="role">role</Label>
                <Controller
                  name="role"
                  control={control}
                  render={({ field }) => (
                    <DropDown
                      id="role"
                      options={roleOptions}
                      placeholder="Select Role"
                      value={field.value}
                      onChange={field.onChange}
                      className="dark:bg-dark-900"
                      disabled={isFieldDisabled("role")}
                    />
                  )}
                />
              </div>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
            {shouldRenderField("is_active") && (
              <div>
                <Controller
                  name="is_active"
                  control={control}
                  render={({ field }) => (
                    <Checkbox
                      id="is_active"
                      checked={field.value ?? false}
                      onChange={field.onChange}
                      label="is_active"
                      disabled={isFieldDisabled("is_active")}
                    />
                  )}
                />
              </div>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
            {shouldRenderField("is_staff") && (
              <div>
                <Controller
                  name="is_staff"
                  control={control}
                  render={({ field }) => (
                    <Checkbox
                      id="is_staff"
                      checked={field.value ?? false}
                      onChange={field.onChange}
                      label="is_staff"
                      disabled={isFieldDisabled("is_staff")}
                    />
                  )}
                />
              </div>
            )}
          </div>

          {/* ----------------------------------
              COMMUNICATIONS SECTION
          ---------------------------------- */}
          <h5 className="dark:text-white text-md font-semibold mt-6 mb-3 custom-header-inner">
            Communications
          </h5>

          {/* Emails Table */}
          <CommunicationTable<EmailRecord>
            title="Emails"
            icon={<FaEnvelope className="text-blue-500" />}
            data={emails}
            columns={[
              { key: 'id', label: 'ID' },
              { key: 'address', label: 'Email Address' },
              { key: 'name', label: 'Name' },
              { key: 'type', label: 'Type' },
              { key: 'is_primary', label: 'Primary', render: (e) => e.is_primary ? '✓' : '' },
            ]}
            onAdd={handleAddEmail}
            onEdit={handleEditEmail}
            onDelete={handleDeleteEmail}
            onSave={handleSaveEmail}
            editingItem={editingEmail}
            onEditChange={handleEmailChange}
            onCancelEdit={() => {
              if (editingEmail?.id === 0) {
                setEmails(prev => prev.filter(e => e.id !== 0));
              }
              setEditingEmail(null);
            }}
            disabled={mode === 'view'}
          />

          {/* Phones Table */}
          <CommunicationTable<PhoneRecord>
            title="Phones"
            icon={<FaPhone className="text-green-500" />}
            data={phones}
            columns={[
              { key: 'id', label: 'ID' },
              { key: 'number', label: 'Phone Number' },
              { key: 'name', label: 'Name' },
              { key: 'type', label: 'Type' },
              { key: 'is_primary', label: 'Primary', render: (p) => p.is_primary ? '✓' : '' },
            ]}
            onAdd={handleAddPhone}
            onEdit={handleEditPhone}
            onDelete={handleDeletePhone}
            onSave={handleSavePhone}
            editingItem={editingPhone}
            onEditChange={handlePhoneChange}
            onCancelEdit={() => {
              if (editingPhone?.id === 0) {
                setPhones(prev => prev.filter(p => p.id !== 0));
              }
              setEditingPhone(null);
            }}
            disabled={mode === 'view'}
          />

          {/* Addresses Table */}
          <CommunicationTable<AddressRecord>
            title="Addresses"
            icon={<FaMapMarkerAlt className="text-red-500" />}
            data={addresses}
            columns={[
              { key: 'id', label: 'ID' },
              { key: 'name', label: 'Name' },
              { key: 'address_line1', label: 'Address' },
              { key: 'city', label: 'City' },
              { key: 'state', label: 'State' },
              { key: 'postal_code', label: 'Postal Code' },
            ]}
            onAdd={handleAddAddress}
            onEdit={handleEditAddress}
            onDelete={handleDeleteAddress}
            onSave={handleSaveAddress}
            editingItem={editingAddress}
            onEditChange={handleAddressChange}
            onCancelEdit={() => {
              if (editingAddress?.id === 0) {
                setAddresses(prev => prev.filter(l => l.id !== 0));
              }
              setEditingAddress(null);
            }}
            disabled={mode === 'view'}
          />

          {/* Domains Table */}
          <CommunicationTable<DomainRecord>
            title="Domains"
            icon={<FaGlobe className="text-purple-500" />}
            data={domains}
            columns={[
              { key: 'id', label: 'ID' },
              { key: 'domain', label: 'Domain' },
              { key: 'name', label: 'Name' },
              { key: 'is_primary', label: 'Primary', render: (d) => d.is_primary ? '✓' : '' },
            ]}
            onAdd={handleAddDomain}
            onEdit={handleEditDomain}
            onDelete={handleDeleteDomain}
            onSave={handleSaveDomain}
            editingItem={editingDomain}
            onEditChange={handleDomainChange}
            onCancelEdit={() => {
              if (editingDomain?.id === 0) {
                setDomains(prev => prev.filter(d => d.id !== 0));
              }
              setEditingDomain(null);
            }}
            disabled={mode === 'view'}
          />

          {/* SUBMIT */}
          {mode !== "view" && (
            <div className="flex items-center gap-2 mt-6">
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

        {/* ----------------------------------
            ADMIN FIELD CONTROLS (moved to bottom)
        ---------------------------------- */}
        {isAdmin && (
          <div className="mt-8 rounded-md border border-dashed border-blue-200 bg-blue-50 dark:bg-slate-800 dark:border-slate-600 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-300">
                  Admin Field Controls
                </h4>
                <p className="text-xs text-blue-700 dark:text-blue-400">
                  Configure visibility and read-only state for contact fields.
                </p>
                {fieldAccessError && (
                  <p className="mt-1 text-xs text-red-600">
                    {fieldAccessError}
                  </p>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <button
                  type="button"
                  onClick={resetFieldAccess}
                  className="rounded border border-blue-200 px-3 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={fieldAccessBusy || !fieldAccessDirty}
                >
                  Reset
                </button>
                <button
                  type="button"
                  onClick={saveFieldAccess}
                  className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={fieldAccessBusy || !fieldAccessDirty}
                >
                  {fieldAccessSaving ? "Saving..." : "Save"}
                </button>
              </div>
            </div>
            <div className="mt-4 grid gap-2 md:grid-cols-2">
              {contactFieldNames.map((fieldName) => {
                const isVisible = !fieldAccessConfig.hidden.includes(fieldName);
                const isReadOnly =
                  fieldAccessConfig.readOnly.includes(fieldName);
                return (
                  <div
                    key={fieldName}
                    className="flex items-center justify-between rounded-md border border-blue-100 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2"
                  >
                    <span className="text-xs font-semibold uppercase text-blue-700 dark:text-blue-300">
                      {fieldName.replace(/_/g, " ")}
                    </span>
                    <div className="flex items-center gap-4 text-xs">
                      <label className="flex items-center gap-1 text-slate-700 dark:text-slate-300">
                        <input
                          type="checkbox"
                          checked={isVisible}
                          onChange={(event) =>
                            setFieldVisible(fieldName, event.target.checked)
                          }
                          disabled={fieldAccessBusy}
                        />
                        Visible
                      </label>
                      <label className="flex items-center gap-1 text-slate-700 dark:text-slate-300">
                        <input
                          type="checkbox"
                          checked={isReadOnly}
                          onChange={(event) =>
                            setFieldReadOnly(fieldName, event.target.checked)
                          }
                          disabled={fieldAccessBusy}
                        />
                        Read-only
                      </label>
                    </div>
                  </div>
                );
              })}
            </div>
            {fieldAccessBusy && (
              <p className="mt-3 text-xs text-blue-600">
                Syncing field preferences...
              </p>
            )}
          </div>
        )}
      </ComponentCard>
    </>
  );
}
