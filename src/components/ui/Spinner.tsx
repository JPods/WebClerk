type SpinnerProps = {
  size?: "xs" | "sm" | "md" | "lg";
  className?: string;
};

const sizeMap: Record<NonNullable<SpinnerProps["size"]>, string> = {
  xs: "h-3 w-3 border-2",
  sm: "h-4 w-4 border-2",
  md: "h-6 w-6 border-3",
  lg: "h-8 w-8 border-4",
};

export default function Spinner({ size = "sm", className = "" }: SpinnerProps) {
  const base = sizeMap[size] || sizeMap.sm;
  return (
    <div
      className={`${base} animate-spin rounded-full border-current border-t-transparent text-white ${className}`.trim()}
      role="status"
      aria-live="polite"
    />
  );
}
