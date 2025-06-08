import React from 'react';

interface InputFieldProps {
  label: string;
  id: string;
  type?: 'text' | 'number' | 'date' | 'email' | 'password';
  placeholder?: string;
  value?: string | number;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  required?: boolean;
  icon?: React.ReactNode; // For calendar icon etc.
  className?: string; // Additional classes for the input container
}

const InputField: React.FC<InputFieldProps> = ({
  label,
  id,
  type = 'text',
  placeholder,
  value,
  onChange,
  required = false,
  icon,
  className = '',
}) => {
  return (
    <div className={`mb-4 ${className}`}>
      <label htmlFor={id} className="poppins-text-400 block text-sm sm:text-base lg:text-lg font-medium text-[#4F4F4F] mb-1">
        {label}
        {required && <span className="text-red-500">*</span>}
      </label>
      <div className="relative">
        <input
          type={type}
          id={id}
          name={id}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          required={required}
          className="block w-full px-3 py-2 lg:py-3 border border-[#B6B6B6] rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm pr-10" // pr-10 for icon space
        />
        {type === 'date' && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              <svg width="14" height="15" viewBox="0 0 14 15" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M5.0416 0.708313V2.12498H8.95114V0.708313H10.2543V2.12498H12.8607C13.2205 2.12498 13.5123 2.44211 13.5123 2.83331V14.1666C13.5123 14.5579 13.2205 14.875 12.8607 14.875H1.13206C0.772198 14.875 0.480469 14.5579 0.480469 14.1666V2.83331C0.480469 2.44211 0.772198 2.12498 1.13206 2.12498H3.73842V0.708313H5.0416ZM12.2091 7.79165H1.78365V13.4583H12.2091V7.79165ZM3.73842 3.54165H1.78365V6.37498H12.2091V3.54165H10.2543V4.95831H8.95114V3.54165H5.0416V4.95831H3.73842V3.54165Z" fill="#333333"/>
              </svg>
          </div>
        )}

        {icon && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              {icon} 
          </div>
        )}
      </div>
    </div>
  );
};

export default InputField;