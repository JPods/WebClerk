/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import type { CountryIso2 } from "react-international-phone";
import { PhoneInput } from "react-international-phone";
import "react-international-phone/style.css";

interface InternationalPhoneInputProps {
  id?: string;
  name?: string;
  value?: string;
  placeholder?: string;
  defaultCountry?: CountryIso2;
  preferredCountries?: CountryIso2[];
  disabled?: boolean;
  error?: boolean;
  className?: string;
  onBlur?: () => void;
  onChange?: (value: string) => void;
}

export default function InternationalPhoneInput({
  id,
  name,
  value = "",
  placeholder = "+1 (555) 000-0000",
  defaultCountry = "us",
  preferredCountries = ["us", "in", "gb"],
  disabled = false,
  error = false,
  className = "",
  onBlur,
  onChange,
}: InternationalPhoneInputProps) {
  return (
    <div className={className}>
      <PhoneInput
        value={value}
        defaultCountry={defaultCountry}
        preferredCountries={preferredCountries}
        forceDialCode
        placeholder={placeholder}
        disabled={disabled}
        name={name}
        inputProps={{ id }}
        onBlur={onBlur}
        onChange={(phone) => onChange?.(phone)}
        className="w-full"
        inputClassName={`h-8 w-full rounded-lg border px-4 py-2.5 text-xs shadow-theme-xs placeholder:text-gray-400 focus:outline-hidden focus:ring-3 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-white/30 ${
          error
            ? "border-error-500 focus:border-error-300 focus:ring-error-500/20 dark:border-error-500 dark:focus:border-error-800"
            : "bg-transparent text-gray-800 border-gray-300 focus:border-brand-300 focus:ring-blue-500/20 dark:border-gray-700 dark:focus:border-brand-800"
        }`}
        countrySelectorStyleProps={{
          buttonClassName:
            "h-8 rounded-l-lg border border-r-0 border-gray-300 bg-transparent px-2 text-xs dark:border-gray-700",
          dropdownArrowClassName: "text-gray-500",
        }}
      />
    </div>
  );
}
