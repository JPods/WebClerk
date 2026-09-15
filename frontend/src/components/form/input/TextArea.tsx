/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// src/components/TextArea.tsx

import React from "react";
import { UseFormRegisterReturn, FieldError } from "react-hook-form";

interface TextareaProps {
  placeholder?: string;
  rows?: number;
  className?: string;
  disabled?: boolean;
  error?: FieldError; // Use react-hook-form's FieldError type
  hint?: string;
  // NOTE: Remove the custom 'onChange' prop if you only want to use register's onChange.
  // If you need both, we'll handle it below.

  // We are now passing the entire register object as a single prop.
  register: UseFormRegisterReturn; 
}

const TextArea: React.FC<TextareaProps> = ({
  placeholder = "Enter your message",
  rows = 3,
  className = "",
  disabled = false,
  error,
  hint = "",
  register, // Destructure the register prop
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
    <div className="relative">
      <textarea
        placeholder={placeholder}
        rows={rows}
        disabled={disabled}
        className={textareaClasses}
        {...register} // Correctly spread the register prop here
      />
      {hint && (
        <p
          className={`mt-2 text-sm ${
            error ? "text-error-500" : "text-gray-500 dark:text-gray-400"
          }`}
        >
          {hint}
        </p>
      )}
    </div>
  );
};

export default TextArea;