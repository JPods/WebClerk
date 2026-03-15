/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React, { useState } from "react";
import { createPortal } from "react-dom";
import { FaSpinner } from "react-icons/fa";

export type CommunicationModalType = "email" | "phone" | "address" | "domain";

export type CommunicationModalData = Record<
  string,
  string | boolean | number | null | undefined
> & {
  id?: number;
};

interface CommunicationAddEditModalProps {
  isOpen: boolean;
  type: CommunicationModalType;
  data?: CommunicationModalData;
  onClose: () => void;
  onSave: (data: CommunicationModalData) => Promise<void> | void;
  isSaving?: boolean;
  contactId?: number;
}

export const CommunicationAddEditModal: React.FC<
  CommunicationAddEditModalProps
> = ({ isOpen, type, data, onClose, onSave, isSaving = false, contactId }) => {
  const [formData, setFormData] = useState<Record<string, string | boolean>>(
    {},
  );

  React.useEffect(() => {
    if (data) {
      const normalized: Record<string, string | boolean> = {
        ...(data as any),
      };
      if (type === "email") {
        normalized.email =
          (data as any).email ||
          (data as any).value ||
          (data as any).address ||
          "";
      } else if (type === "phone") {
        normalized.number = (data as any).number || (data as any).value || "";
      } else if (type === "domain") {
        normalized.domain =
          (data as any).domain ||
          (data as any).value ||
          (data as any).path ||
          "";
      }
      setFormData(normalized);
    } else {
      setFormData({});
    }
  }, [data, isOpen, type]);

  if (!isOpen) return null;

  const handleOverlayClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onClose();
  };

  const handleModalClick = (e: React.MouseEvent) => {
    e.stopPropagation();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();

    // Validate required fields based on type
    if (type === "email" && !formData.email) {
      alert("Email is required");
      return;
    }
    if (type === "phone" && !formData.number) {
      alert("Phone number is required");
      return;
    }
    if (type === "address" && !formData.address1) {
      alert("Street address is required");
      return;
    }
    if (type === "domain" && !formData.domain) {
      alert("Domain is required");
      return;
    }

    const payload = data?.id
      ? ({ id: data.id, ...formData } as any)
      : ({ ...formData } as any);

    try {
      // Await the parent's async save handler (which includes refresh)
      await Promise.resolve(onSave(payload));
      // Parent will close modal via state update after refresh completes
      setFormData({});
    } catch (error) {
      console.error("[CommunicationAddEditModal] Save failed:", error);
      // Parent handles error toast, but keep form data for user to retry
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={handleOverlayClick}
    >
      <div
        className="bg-white dark:bg-slate-800 rounded-lg p-4 w-80 max-w-full mx-4"
        onClick={handleModalClick}
      >
        <h3 className="text-sm font-semibold mb-2 text-slate-700 dark:text-slate-200 capitalize">
          {data ? "Edit" : "Add"} {type}
        </h3>
        {contactId !== undefined && (
          <p className="text-xs text-slate-500 mb-4">
            Contact ID:{" "}
            <strong className="text-blue-600">{contactId ?? "NOT SET"}</strong>
          </p>
        )}

        <form onSubmit={handleSubmit} className="space-y-3">
          {type === "email" && (
            <>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  value={(formData.email as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, email: e.target.value })
                  }
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  required
                />
              </div>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                  Label
                </label>
                <input
                  type="text"
                  value={(formData.name as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="Work, Personal, etc."
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={(formData.is_primary as boolean) || false}
                  onChange={(e) =>
                    setFormData({ ...formData, is_primary: e.target.checked })
                  }
                />
                Primary email
              </label>
            </>
          )}

          {type === "phone" && (
            <>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                  Number
                </label>
                <input
                  type="tel"
                  value={(formData.number as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, number: e.target.value })
                  }
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  required
                />
              </div>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                  Label
                </label>
                <input
                  type="text"
                  value={(formData.name as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="Mobile, Office, etc."
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                />
              </div>
            </>
          )}

          {type === "address" && (
            <>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                  Street Address
                </label>
                <input
                  type="text"
                  value={(formData.address1 as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, address1: e.target.value })
                  }
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                    City
                  </label>
                  <input
                    type="text"
                    value={(formData.city as string) || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, city: e.target.value })
                    }
                    className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                    State
                  </label>
                  <input
                    type="text"
                    value={(formData.state as string) || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, state: e.target.value })
                    }
                    className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                    Zip
                  </label>
                  <input
                    type="text"
                    value={(formData.zip as string) || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, zip: e.target.value })
                    }
                    className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                    Country
                  </label>
                  <input
                    type="text"
                    value={(formData.country as string) || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, country: e.target.value })
                    }
                    placeholder="US"
                    className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  />
                </div>
              </div>
            </>
          )}

          {type === "domain" && (
            <>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
                  Domain
                </label>
                <input
                  type="text"
                  value={(formData.domain as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, domain: e.target.value })
                  }
                  placeholder="example.com"
                  className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                  required
                />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={(formData.is_primary as boolean) || false}
                  onChange={(e) =>
                    setFormData({ ...formData, is_primary: e.target.checked })
                  }
                />
                Primary domain
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={(formData.verified as boolean) || false}
                  onChange={(e) =>
                    setFormData({ ...formData, verified: e.target.checked })
                  }
                />
                Verified
              </label>
            </>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700 rounded disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 flex items-center gap-1.5"
            >
              {isSaving && <FaSpinner className="animate-spin" size={12} />}
              {isSaving ? "Saving..." : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  );
};
