import React, { ButtonHTMLAttributes } from "react";
// import SyncIcon from "@mui/icons-material/Sync";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  bgColor?: string;
  textColor?: string;
  loading?: boolean;
}

const Button: React.FC<ButtonProps> = ({
  children,
  type = "button",
  loading = false,
  bgColor = "bg-blue-600",
  textColor = "text-white",
  className = "",
  ...props
}) => {
  return (
    <button
      disabled={loading}
      type={type}
      className={`px-4 btn-ripple py-2 rounded-3xl ${className}`}
      {...props}
    >
      {/* <SyncIcon className="animate-spin mr-1" /> */}
      {children}
    </button>
  );
};

export default Button;
