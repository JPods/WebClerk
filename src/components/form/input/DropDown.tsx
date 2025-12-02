import React from "react";
import type { FC } from "react";
interface Option {
  value: string;
  label: string;
}

interface SelectProps {
  id?: string;
  name?: string;
  options: Option[];
  placeholder?: string;
  onChange: (value: string) => void;
  className?: string;
  value?: string;
  ref?: React.Ref<HTMLSelectElement>;
  disabled?: boolean;
  success?: boolean;
  error?: boolean;
}

const DropDown: FC<SelectProps> = ({
  id,
  name,
  options,
  placeholder = "Select an option",
  onChange,
  className = "",
  value,
  ref,
  disabled = false,
  success = false,
  error = false,
  ...rest
}) => {
  let inputClasses = `h-11 w-full rounded-lg border appearance-none px-4 py-2.5 text-sm shadow-theme-xs placeholder:text-gray-400 focus:outline-hidden focus:ring-3 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-white/30 ${className}`;

  if (disabled) {
    inputClasses += ` text-gray-800 border-gray-300 opacity-40 bg-gray-100 cursor-not-allowed dark:bg-gray-800 dark:text-gray-800 dark:border-gray-700 opacity-80`;
  } else if (error) {
    inputClasses += ` border-error-500 focus:border-error-300 focus:ring-error-500/20 dark:text-error-400 dark:border-error-500 dark:focus:border-error-800`;
  } else if (success) {
    inputClasses += ` border-success-500 focus:border-success-300 focus:ring-success-500/20 dark:text-success-400 dark:border-success-500 dark:focus:border-success-800`;
  } else {
    inputClasses += ` bg-transparent text-gray-800 border-gray-300 focus:border-brand-300 focus:ring-blue-500/20 dark:border-gray-700 dark:text-white/90 dark:focus:border-brand-800`;
  }
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedValue = e.target.value;
    onChange(selectedValue); // Trigger parent handler
  };

  return (
    <div className={`relative ${className}`}>
      <select
        value={value}
        id={id}
        name={name}
        onChange={handleChange}
        disabled={disabled}
        className={inputClasses}
        ref={ref}
        {...rest}
      >
        <option
          value=""
          disabled
          className="text-gray-700 dark:bg-gray-900 dark:text-gray-400"
        >
          {placeholder}
        </option>
        {options.map((option) => (
          <option
            key={option.value}
            value={option.value}
            className="text-gray-700 dark:bg-gray-900 dark:text-gray-400"
          >
            {option.label}
          </option>
        ))}
      </select>
      <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none text-gray-700 dark:text-gray-400">
        <svg
          className="stroke-current"
          width="20"
          height="20"
          viewBox="0 0 20 20"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M4.79175 7.396L10.0001 12.6043L15.2084 7.396"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
    </div>
  );
};

export default DropDown;
