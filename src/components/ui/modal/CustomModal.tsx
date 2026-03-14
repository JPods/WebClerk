/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { FormEvent, ReactNode } from "react";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

interface ModalProps {
  mode: "add" | "edit" | "view";
  isOpen: boolean;
  title: string;
  description: string;
  isSaving?: boolean;
  submitLabel?: string;
  onClose?: () => void;
  onSubmit?: (event: FormEvent<HTMLFormElement>) => void;
  modalError?: string | null;
  extraContent?: ReactNode;
  isPageTitle: boolean;
}
export const CustomeModal: React.FC<ModalProps> = ({
  mode,
  isOpen,
  title,
  description,
  isSaving,
  submitLabel,
  onClose,
  onSubmit,
  modalError,
  extraContent,
  isPageTitle = false,
}) => {
  if (!isOpen) {
    return null;
  }
  return (
    <div className="fixed inset-0 z-[200000] flex items-center justify-center bg-black/30 px-4 py-6 backdrop-blur-sm">
      <div className="w-full  max-h-[calc(100vh-4rem)] overflow-y-auto rounded-3xl border border-gray-200 bg-white p-6 shadow-xl no-scrollbar dark:border-gray-800 dark:bg-gray-900">
        <div
          className={`mb-4 flex items-start ${
            isPageTitle ? "justify-between" : "justify-end"
          }`}
        >
          {isPageTitle ? (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {mode === "edit" ? "Edit" : mode === "view" ? "View" : "Add"}{" "}
                {title}
              </h2>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                {description}
              </p>
            </div>
          ) : null}

          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
            aria-label="Close modal"
            disabled={isSaving}
          >
            <svg
              className="h-5 w-5"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M6 6l8 8M14 6l-8 8"
                stroke="currentColor"
                strokeWidth={1.6}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>

        <form className="space-y-5" onSubmit={onSubmit}>
          {modalError && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/40 dark:text-rose-200">
              {modalError}
            </div>
          )}
          {extraContent}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:text-gray-400 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
            >
              Close
            </button>
            {isSaving ? (
              <button
                type="submit"
                disabled={isSaving}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-400"
              >
                {submitLabel}
              </button>
            ) : null}
          </div>
        </form>
      </div>
    </div>
  );
};
export default withDevIdentifier(CustomeModal, 'CustomeModal', 'rose');