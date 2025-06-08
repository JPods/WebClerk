import { forwardRef, useId, InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  className?: string;
  labelClass?: string;
}

const Checkbox = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, type = 'checkbox', labelClass = '' , className = '', ...props },
  ref
) {
  const id = useId();
  return (
    <div className='w-full'>
      {label && (
        <label className={labelClass} htmlFor={id}>
          {label}
        </label>
      )}
      <input
        type={type}
        className={`px-3 py-2 rounded-lg bg-white text-black outline-none focus:bg-gray-50 duration-200 border border-gray-200 w-full ${className}`}
        ref={ref}
        {...props}
        id={id}
      />
    </div>
  );
});

export default Checkbox;