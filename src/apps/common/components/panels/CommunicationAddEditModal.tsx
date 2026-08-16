/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React, { useState } from "react";
import { createPortal } from "react-dom";
import { FaSpinner } from "react-icons/fa";
import { formatAddressFull } from "@/utils/addressFull";

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

    if (type === "address") {
      payload.full = formatAddressFull({
        address1: payload.address1,
        address2: payload.address2,
        city: payload.city,
        state: payload.state,
        zip: payload.zip,
        country: payload.country,
      });
    }

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
        className="rounded-lg p-4 w-80 max-w-full mx-4 db-bg-surface"
        onClick={handleModalClick}
      >
        <h3 className="text-sm font-semibold mb-2 capitalize db-text">
          {data ? "Edit" : "Add"} {type}
        </h3>
        {contactId !== undefined && (
          <p className="text-xs mb-4 db-text-muted">
            Contact ID:{" "}
            <strong className="db-text-accent">{contactId ?? "NOT SET"}</strong>
          </p>
        )}

        <form onSubmit={handleSubmit} className="space-y-3">
          {type === "email" && (
            <>
              <div>
                <label className="block text-xs mb-1 db-text-muted">
                  Email
                </label>
                <input
                  type="email"
                  value={(formData.email as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, email: e.target.value })
                  }
                  className="w-full px-2 py-1.5 text-sm rounded db-panel-input"
                  required
                />
              </div>
              <div>
                <label className="block text-xs mb-1 db-text-muted">
                  Label
                </label>
                <input
                  type="text"
                  value={(formData.name as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="Work, Personal, etc."
                  className="w-full px-2 py-1.5 text-sm rounded db-panel-input"
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
                <label className="block text-xs mb-1 db-text-muted">
                  Number
                </label>
                <input
                  type="tel"
                  value={(formData.number as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, number: e.target.value })
                  }
                  className="w-full px-2 py-1.5 text-sm rounded db-panel-input"
                  required
                />
              </div>
              <div>
                <label className="block text-xs mb-1 db-text-muted">
                  Label
                </label>
                <input
                  type="text"
                  value={(formData.name as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="Mobile, Office, etc."
                  className="w-full px-2 py-1.5 text-sm rounded db-panel-input"
                />
              </div>
            </>
          )}

          {type === "address" && (
            <>
              <div>
                <label className="block text-xs mb-1 db-text-muted">
                  Street Address
                </label>
                <input
                  type="text"
                  value={(formData.address1 as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, address1: e.target.value })
                  }
                  className="w-full px-2 py-1.5 text-sm rounded db-panel-input"
                  required
                />
              </div>
              <div>
                <label className="block text-xs mb-1 db-text-muted">
                  Address 2
                </label>
                <input
                  type="text"
                  value={(formData.address2 as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, address2: e.target.value })
                  }
                  className="w-full px-2 py-1.5 text-sm rounded db-panel-input"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs mb-1 db-text-muted">
                    City
                  </label>
                  <input
                    type="text"
                    value={(formData.city as string) || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, city: e.target.value })
                    }
                    className="w-full px-2 py-1.5 text-sm rounded db-panel-input"
                  />
                </div>
                <div>
                  <label className="block text-xs mb-1 db-text-muted">
                    State
                  </label>
                  <input
                    type="text"
                    value={(formData.state as string) || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, state: e.target.value })
                    }
                    className="w-full px-2 py-1.5 text-sm rounded db-panel-input"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs mb-1 db-text-muted">
                    Zip
                  </label>
                  <input
                    type="text"
                    value={(formData.zip as string) || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, zip: e.target.value })
                    }
                    className="w-full px-2 py-1.5 text-sm rounded db-panel-input"
                  />
                </div>
                <div>
                  <label className="block text-xs mb-1 db-text-muted">
                    Country
                  </label>
                  <input
                    type="text"
                    value={(formData.country as string) || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, country: e.target.value })
                    }
                    placeholder="US"
                    className="w-full px-2 py-1.5 text-sm rounded db-panel-input"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs mb-1 db-text-muted">
                  full
                </label>
                <input
                  type="text"
                  value={formatAddressFull({
                    address1: formData.address1 as string,
                    address2: formData.address2 as string,
                    city: formData.city as string,
                    state: formData.state as string,
                    zip: formData.zip as string,
                    country: formData.country as string,
                  })}
                  readOnly
                  className="w-full px-2 py-1.5 text-sm rounded db-surface-alt-text db-panel-input"
                />
              </div>
            </>
          )}

          {type === "domain" && (
            <>
              <div>
                <label className="block text-xs mb-1 db-text-muted">
                  Domain
                </label>
                <input
                  type="text"
                  value={(formData.domain as string) || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, domain: e.target.value })
                  }
                  placeholder="example.com"
                  className="w-full px-2 py-1.5 text-sm rounded db-panel-input"
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
              className="px-3 py-1.5 text-sm rounded disabled:opacity-50 db-text-muted"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="px-3 py-1.5 text-sm rounded disabled:opacity-50 flex items-center gap-1.5 db-btn db-btn--primary"
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
