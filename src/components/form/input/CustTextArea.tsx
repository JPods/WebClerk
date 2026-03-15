/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// src/components/form/input/CustTextArea.tsx
import React from "react";
import type { FC } from "react";
interface TextareaProps {
  id?: string;
  name?: string;
  value?: string | number | readonly string[];
  placeholder?: string;
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  rows?: number;
  className?: string;
  disabled?: boolean;
  success?: boolean;
  error?: boolean; // Use react-hook-form's FieldError type
  hint?: string;
  ref?: React.Ref<HTMLTextAreaElement>;
}

const CustTextArea: FC<TextareaProps> = ({
  id,
  name,
  placeholder = "Enter your message",
  rows = 6,
  value,
  onChange,
  className = "",
  disabled = false,
  success = false,
  error = false,
  hint = "",
  ref,
  ...rest
}) => {
  let textareaClasses = `w-full rounded-lg border px-4 py-2.5 text-sm shadow-theme-xs focus:outline-hidden ${className}`;

  if (disabled) {
    textareaClasses += ` bg-gray-100 opacity-50 text-gray-500 border-gray-300 cursor-not-allowed dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700`;
  } else if (error) {
    textareaClasses += ` bg-transparent border-gray-300 focus:border-error-300 focus:ring-3 focus:ring-error-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-error-800`;
  } else {
    textareaClasses += ` bg-transparent text-gray-900 dark:text-gray-300 border-gray-300 focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800`;
  }

  return (
    <div className={`relative ${className}`}>
      <textarea
        id={id}
        name={name}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        rows={rows}
        disabled={disabled}
        className={textareaClasses}
        ref={ref}
        {...rest}
      />
      {hint && (
        <p
          className={`mt-1.5 text-xs ${
            error
              ? "text-error-500"
              : success
              ? "text-success-500"
              : "text-gray-500"
          }`}
        >
          {hint}
        </p>
      )}
    </div>
  );
};

export default CustTextArea;
