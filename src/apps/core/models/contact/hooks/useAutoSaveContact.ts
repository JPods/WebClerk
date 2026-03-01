/**
 * useAutoSaveContact — auto-saves a new contact the first time the user
 * attempts to create a child record (comm, action, document, etc.)
 * before explicitly saving.
 *
 * Returns `ensureContactId()` which:
 *   - If contact already exists → returns its id immediately.
 *   - If in add mode → validates required fields, saves, transitions to
 *     edit mode, and returns the new id.
 *   - If validation fails → shows a toast and returns null.
 *
 * Usage inside ContactDetail3:
 *   const { ensureContactId, autoSaveInProgress } = useAutoSaveContact({
 *     recordMode, activeContactId, getValues, formSetValueRef,
 *     onContactCreated,
 *   });
 *
 *   // Before any child-record operation:
 *   const id = await ensureContactId();
 *   if (!id) return;  // user notified via toast
 *   // ...proceed with child save using `id` as contact_id
 */

import { useCallback, useRef, useState } from "react";
import { useDispatch } from "react-redux";
import { showToast } from "@/store/slices/toastSlice";
import { createContact } from "@/apps/core/models/contact/services/contactApi";
import { mapRefsFormToApi } from "@/apps/core/models/contact/utils/contactSchema";

export interface AutoSaveContactOpts {
  /** "add" or "edit" */
  recordMode: "add" | "edit";
  /** Current contact id (null when unsaved) */
  activeContactId: number | null;
  /** react-hook-form getValues */
  getValues: () => any;
  /** Parent context from URL params */
  parentModel?: string;
  parentId?: number;
  parentCustomerId?: number;
  parentCustomerName?: string;
  /** Callback when auto-save succeeds — caller should transition to edit mode,
   *  update fetchedData, broadcast event, etc. */
  onContactCreated: (newId: number, response: any) => void;
}

export function useAutoSaveContact({
  recordMode,
  activeContactId,
  getValues,
  parentModel,
  parentId,
  parentCustomerId,
  parentCustomerName,
  onContactCreated,
}: AutoSaveContactOpts) {
  const dispatch = useDispatch();
  const [autoSaveInProgress, setAutoSaveInProgress] = useState(false);
  /** Prevent concurrent auto-saves from double-creating. */
  const autoSaveLock = useRef<Promise<number | null> | null>(null);

  const ensureContactId = useCallback(async (): Promise<number | null> => {
    // Already saved — fast path
    if (activeContactId) return activeContactId;

    // Only auto-save in add mode
    if (recordMode !== "add") return null;

    // If already in progress, wait for the same promise
    if (autoSaveLock.current) return autoSaveLock.current;

    const run = async (): Promise<number | null> => {
      const formData = getValues();

      // --- Validate minimum required fields --------------------------------
      const email = (formData.email || "").trim();
      const nameFirst = (formData.name_first || "").trim();
      const nameLast = (formData.name_last || "").trim();

      const missing: string[] = [];
      if (!email) missing.push("email");
      if (!nameFirst) missing.push("name_first");
      if (!nameLast) missing.push("name_last");

      if (missing.length > 0) {
        dispatch(
          showToast({
            message: `Fill in ${missing.join(", ")} before adding related records`,
            type: "error",
          }),
        );
        return null;
      }

      // --- Build payload ---------------------------------------------------
      // Auto-generate a secure random password when none provided (add-mode
      // schema requires it, but user may not have filled it yet).
      let password = (formData.password || "").trim();
      if (!password) {
        password =
          crypto.randomUUID().replace(/-/g, "").slice(0, 16) + "Aa1!";
      }

      const mappedRefs = formData.refs
        ? mapRefsFormToApi(formData.refs)
        : undefined;

      const payload: Record<string, any> = {
        email,
        name_first: nameFirst,
        name_last: nameLast,
        name_middle: formData.name_middle,
        name_prefix: formData.name_prefix,
        name_suffix: formData.name_suffix,
        attention: formData.attention,
        company: formData.company || parentCustomerName,
        title: formData.title,
        department: formData.department,
        role: formData.role,
        is_active: formData.is_active ?? true,
        is_staff: formData.is_staff ?? false,
        password,
        customer_id:
          formData.customer_id ?? parentCustomerId,
        rep_id: formData.rep_id,
        vendor_id: formData.vendor_id,
        employee_id: formData.employee_id,
        manufacturer_id: formData.manufacturer_id,
        other_id: formData.other_id,
        refs: mappedRefs,
      };

      // --- Save ------------------------------------------------------------
      setAutoSaveInProgress(true);
      try {
        const res: any = await createContact(payload as any);
        const newId =
          res?.record?.id ?? res?.id ?? res?.data?.id;

        if (!newId || typeof newId !== "number") {
          dispatch(
            showToast({
              message: "Auto-save failed: no ID returned",
              type: "error",
            }),
          );
          return null;
        }

        dispatch(
          showToast({
            message: "Contact auto-saved",
            type: "success",
          }),
        );

        onContactCreated(newId, res);
        return newId;
      } catch (err: any) {
        const msg =
          err?.response?.data?.error ||
          err?.response?.data?.message ||
          err?.message ||
          "Auto-save failed";
        dispatch(showToast({ message: String(msg), type: "error" }));
        return null;
      } finally {
        setAutoSaveInProgress(false);
        autoSaveLock.current = null;
      }
    };

    autoSaveLock.current = run();
    return autoSaveLock.current;
  }, [
    activeContactId,
    recordMode,
    getValues,
    parentModel,
    parentId,
    parentCustomerId,
    parentCustomerName,
    onContactCreated,
    dispatch,
  ]);

  return { ensureContactId, autoSaveInProgress } as const;
}
