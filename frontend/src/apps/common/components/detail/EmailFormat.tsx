export const EmailFormat: React.FC<{ value?: string | null }> = ({ value }) => {
  if (!value) return null;
  return (
    <>
      <a
        href={`mailto:${value}`}
        className="text-xs font-mono text-blue-900 dark:text-blue-400 cursor-pointer hover:underline"
      >
        {value}
      </a>
    </>
  );
};

export const EmailLable: React.FC<{
  value?: string | null;
  labelText?: string;
}> = ({ value, labelText = "email" }) => {
  if (!value) return labelText;
  return (
    <>
      <a
        href={`mailto:${value}`}
        title={value}
        className="text-blue-900 dark:text-blue-400 cursor-pointer hover:underline"
      >
        {labelText}
      </a>
    </>
  );
};
