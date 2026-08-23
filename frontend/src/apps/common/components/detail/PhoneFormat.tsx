import { defaultCountries, usePhoneInput } from "react-international-phone";
/**
 * PhoneDisplay - Format and display phone numbers using react-international-phone
 * Uses the library's formatting logic for consistent display with the input component
 */
export const PhoneFormat: React.FC<{ value?: string | null }> = ({ value }) => {
  const { inputValue } = usePhoneInput({
    value: value || "",
    countries: defaultCountries,
    defaultCountry: "us",
    forceDialCode: true,
  });

  if (!value) return null;
  return (
    <>
      <a
        href={`tel:${inputValue}`}
        className="text-xs font-mono text-blue-600 dark:text-blue-400 cursor-pointer hover:underline"
      >
        {inputValue}
      </a>
    </>
  );
};
export const PhoneLable: React.FC<{
  value?: string | null;
  labelText?: string;
}> = ({ value, labelText = "phone" }) => {
  const { inputValue } = usePhoneInput({
    value: value || "",
    countries: defaultCountries,
    defaultCountry: "us",
    forceDialCode: true,
  });

  if (!value) return labelText;
  return (
    <>
      <a
        href={`tel:${inputValue}`}
        title={inputValue}
        className=" text-blue-600 dark:text-blue-400 cursor-pointer hover:underline"
      >
        {labelText}
      </a>
    </>
  );
};
