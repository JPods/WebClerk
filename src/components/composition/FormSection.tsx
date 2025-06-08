import React from 'react';

interface FormSectionProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

const FormSection: React.FC<FormSectionProps> = ({ title, children, className = '' }) => {
  return (
    <div className={`bg-white border border-[#B6B6B6] rounded-2xl p-4 lg:p-6 shadow-sm ${className}`}>
      <h3 className="poppins-text-600 text-base sm:text-lg lg:text-[20px] mb-4 border-b pb-3 text-[#2E87F8]">
        {title}
      </h3>
      {children}
    </div>
  );
};

export default FormSection;