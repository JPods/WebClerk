import React from 'react';

interface TextareaFieldProps {
  name?: string;
  value?: string;
  placeholder?: string;
  label?: string;
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  disabled?: boolean;
  required?: boolean;
  rows?: number;
  className?: string;
}

export const TextareaField: React.FC<TextareaFieldProps> = ({
  name = 'text',
  value = '',
  placeholder = '',
  label = '',
  onChange,
  disabled = false,
  required = false,
  rows = 4,
  className = '',
}) => {
  return (
    <div className={`textarea-field ${className}`}>
      {label && (
        <label htmlFor={name} className="block text-sm font-medium text-gray-700 mb-1">
          {label}
        </label>
      )}
      <textarea
        id={name}
        name={name}
        value={value}
        placeholder={placeholder}
        onChange={onChange}
        disabled={disabled}
        required={required}
        rows={rows}
        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
      />
    </div>
  );
};

export default TextareaField;