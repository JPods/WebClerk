import React from 'react';

interface InputFieldProps {
  name?: string;
  value?: string;
  type?: string;
  placeholder?: string;
  label?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  disabled?: boolean;
  required?: boolean;
  className?: string;
}

export const InputField: React.FC<InputFieldProps> = ({
  name = '',
  value = '',
  type = 'text',
  placeholder = '',
  label = '',
  onChange,
  disabled = false,
  required = false,
  className = '',
}) => {
  return (
    <div className={`input-field ${className}`}>
      {label && (
        <label htmlFor={name} className="block text-sm font-medium text-gray-700 mb-1">
          {label}
        </label>
      )}
      <input
        id={name}
        name={name}
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={onChange}
        disabled={disabled}
        required={required}
        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
      />
    </div>
  );
};

export default InputField;