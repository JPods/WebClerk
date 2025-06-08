import React from 'react';

interface RadioOption {
  value: string;
  label: string;
}

interface RadioGroupProps {
  label?: string;
  name: string;
  options: RadioOption[];
  selectedValue: string;
  onChange: (value: string) => void;
  required?: boolean;
}

const RadioGroup: React.FC<RadioGroupProps> = ({
  label,
  name,
  options,
  selectedValue,
  onChange,
  required = false,
}) => {
  return (
    <div className="mb-4">
      {label && (
        <label className="poppins-text-400 block text-sm sm:text-base lg:text-lg text-[#4F4F4F] mb-4">
          {label}
          {required && <span className="text-red-500">*</span>}
        </label>
      )}
      <div className="flex items-center space-x-4">
        {options.map((option) => (
          <label key={option.value} className="inline-flex items-center cursor-pointer">
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={selectedValue === option.value}
              onChange={() => onChange(option.value)}
              required={required}
              className="form-radio h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500"
            />
            <span className="ml-2 poppins-text-400 text-xs md:text-sm text-[#4F4F4F]">{option.label}</span>
          </label>
        ))}
      </div>
    </div>
  );
};

export default RadioGroup;