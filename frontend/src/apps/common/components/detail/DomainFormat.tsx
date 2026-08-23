export const DomainFormat: React.FC<{ value?: string | null }> = ({
  value,
}) => {
  if (!value) return null;
  return (
    <>
      <a
        href={`https://${value}`}
        className="text-xs font-mono text-yellow-900 dark:text-yellow-400 cursor-pointer hover:underline"
        target="_blank"
      >
        {value}
      </a>
    </>
  );
};

export const DomainLable: React.FC<{
  value?: string | null;
  labelText?: string;
}> = ({ value, labelText = "domain" }) => {
  if (!value) return labelText;
  return (
    <>
      <a
        href={`https://${value}`}
        title={value}
        target="_blank"
        className="text-yellow-900 dark:text-yellow-400 cursor-pointer hover:underline"
      >
        {labelText}
      </a>
    </>
  );
};
