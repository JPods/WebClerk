import Label from "@/components/form/Label";

interface HorizontalFieldProps {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
  error?: string;
  required?: boolean;
  labelAddon?: React.ReactNode;
}
export function HorizontalField({
  label,
  htmlFor,
  children,
  error,
  required,
  labelAddon,
}: HorizontalFieldProps) {
  return (
    <div className="flex items-center gap-2 py-1.5">
      <Label
        htmlFor={htmlFor}
        className="w-32 shrink-0 text-left text-sm font-medium text-slate-600 dark:text-slate-400"
      >
        <span className="inline-flex items-center gap-1">
          {labelAddon ? labelAddon : label}
          {required && <span className="text-red-500 ml-0.5">*</span>}
        </span>
      </Label>
      <div className="flex-1 min-w-0">
        {children}
        {error && <p className="mt-0.5 text-xs text-red-500">{error}</p>}
      </div>
    </div>
  );
}
