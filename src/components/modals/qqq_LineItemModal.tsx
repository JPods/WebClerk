/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React from "react";

interface LineField {
  label: string;
  value?: React.ReactNode;
}

interface LineItemModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  fields: LineField[];
  imageUrl?: string | null;
}

const LineItemModal: React.FC<LineItemModalProps> = ({ isOpen, onClose, title, fields, imageUrl }) => {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="relative w-full max-w-2xl rounded-2xl bg-white shadow-xl dark:bg-gray-900">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 text-2xl text-gray-400 transition hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
          aria-label="close line item modal"
        >
          &times;
        </button>
        <div className="flex flex-col gap-6 p-6">
          {title && <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h2>}
          <div className="grid gap-6 md:grid-cols-2">
            <dl className="space-y-3 text-sm text-gray-700 dark:text-gray-200">
              {fields.map((field) => (
                <div key={field.label} className="flex flex-col">
                  <dt className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">{field.label}</dt>
                  <dd className="font-medium">{field.value ?? ""}</dd>
                </div>
              ))}
            </dl>
            {imageUrl ? (
              <div className="flex items-center justify-center">
                <img
                  src={imageUrl}
                  alt={title || "line item image"}
                  className="h-48 w-48 rounded-xl object-cover"
                />
              </div>
            ) : null}
          </div>
          <div className="flex justify-end">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-100 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
            >
              close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LineItemModal;
