import React from 'react';

interface SelectFieldProps {
  label: string;
  id: string;
  options: { value: string; label: string }[];
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  required?: boolean;
  placeholder?: string; // For the initial disabled option
  className?: string;
}

const SelectField: React.FC<SelectFieldProps> = ({
  label,
  id,
  options,
  value,
  onChange,
  required = false,
  placeholder,
  className = '',
}) => {

  const newSvgContent = encodeURIComponent(`
    <svg width="13" height="9" viewBox="0 0 13 9" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M11.8528 3.25842L7.46167 7.64957C7.30482 7.80674 7.11851 7.93143 6.91341 8.01651C6.70831 8.10159 6.48844 8.14539 6.26639 8.14539C6.04434 8.14539 5.82448 8.10159 5.61938 8.01651C5.41428 7.93143 5.22797 7.80674 5.07112 7.64957L0.67997 3.25842C-0.388147 2.1903 0.374794 0.359247 1.88372 0.359247L10.666 0.359247C12.1749 0.359247 12.9209 2.1903 11.8528 3.25842Z" fill="#989898"/>
    </svg>
  `.replace(/\s+/g, ' ').trim());

  return (
    <div className={`mb-4 ${className}`}>
      <label htmlFor={id} className="poppins-text-400 block text-sm sm:text-base lg:text-lg text-[#4F4F4F] mb-1">
        {label}
        {required && <span className="text-red-500">*</span>}
      </label>
      <select
        id={id}
        name={id}
        value={value}
        onChange={onChange}
        required={required}
        className="block w-full pl-3 pr-10 py-2 lg:py-3 border border-[#B6B6B6] rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm appearance-none bg-white bg-no-repeat bg-right-center"
        // bg-right-center for custom arrow icon if needed
        // For a simple dropdown arrow, you might use bg-chevron-down custom utility or an icon
        style={{
          backgroundImage: `url("data:image/svg+xml, ${newSvgContent}")`,
          backgroundSize: '1rem',
          backgroundPosition: 'right 0.5rem center',
        }}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
};

export default SelectField;