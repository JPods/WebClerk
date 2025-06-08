import React from 'react';

interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
  variant: 'primary' | 'secondary' | 'outline'; // <--- UPDATED THIS LINE
  className?: string;
}

const Button: React.FC<ButtonProps> = ({
  children,
  onClick,
  type = 'button',
  variant,
  className = '',
}) => {
  const baseClasses = 'px-6 py-2 poppins-text-400 rounded-lg text-sm md:text-base xl:text-lg focus:outline-none focus:ring-2 focus:ring-offset-2';
  const variants = {
    primary: 'bg-[#2E87F8] text-white hover:bg-blue-700 focus:ring-blue-500 ',
    secondary: 'bg-[#FFE8E8] text-[#C10808] hover:bg-gray-300 focus:ring-gray-500',
    outline: 'border border-gray-300 text-gray-700 hover:bg-gray-50 focus:ring-gray-400', // <--- Add styles for 'outline'
  };

  return (
    <button
      type={type}
      onClick={onClick}
      className={`${baseClasses} ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  );
};

export default Button;