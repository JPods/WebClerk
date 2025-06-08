import { forwardRef, useId, TextareaHTMLAttributes } from "react";
import { UseFormRegisterReturn } from "react-hook-form";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  className?: string;
  labelClass?: string;
  isrequred?: string;
  onChangeHandler?: (e: any) => void;
  registerProps?: UseFormRegisterReturn;
  msg?:string;
}

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  function Textarea(
    { label, registerProps, labelClass = "", isrequred = "", className = "",msg="", ...props },
    ref
  ) {
    const id = useId();
    return (
      <div className="w-full">
        {label && (
          <div className="flex">
          <label className={labelClass} htmlFor={id}>
            {label}
            {isrequred == "required" ? (
            <sup className="text-red-500 font-medium text-sm">*</sup>
          ) : (
            ""
          )}   
          </label>
          {msg && (<p className={`text-red-500 text-sm ml-1`}>{msg}</p>)}
          </div>
        )}
        <textarea
          {...registerProps}
          className={`px-3 py-2 rounded-lg bg-white text-black outline-none focus:bg-gray-50 duration-200 border border-gray-200 w-full ${className}`}
          ref={ref}
          {...props}
          id={id}
        />
      </div>
    );
  }
);

export default Textarea;
