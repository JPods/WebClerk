export const AddressFormat: React.FC<{ value?: string | null }> = ({
  value,
}) => {
  if (!value) return null;
  const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
    value,
  )}`;
  return (
    <>
      <a
        href={mapUrl}
        target="_blank"
        rel="noreferrer"
        className="text-xs font-mono text-green-900 dark:text-green-400 cursor-pointer hover:underline"
      >
        {value}
      </a>
    </>
  );
};

export const AddressLable: React.FC<{
  value?: string | null;
  labelText?: string;
}> = ({ value, labelText = "address_full" }) => {
  if (!value) return labelText;
  const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
    value,
  )}`;
  return (
    <>
      <a
        href={mapUrl}
        title={value}
        target="_blank"
        rel="noreferrer"
        className="text-green-900 dark:text-green-400 cursor-pointer hover:underline"
      >
        {labelText}
      </a>
    </>
  );
};
