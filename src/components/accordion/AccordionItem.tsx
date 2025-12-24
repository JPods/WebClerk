import React from "react";

interface AccordionItemProps {
  title?: string;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

const AccordionItem: React.FC<AccordionItemProps> = ({
  title,
  isOpen,
  onToggle,
  children,
}) => {
  return (
    <div
      className={`my-3 border transition-all duration-300 ${
        isOpen
          ? "border-purple-500 dark:!border-white bg-blue-50 shadow-sm"
          : "border-gray-200 bg-white"
      }`}
    >
      <button
        className={`flex justify-between items-center w-full p-2 text-left font-medium transition ${
          isOpen
            ? "bg-blue-100 cus-bg-theme-purple-medium"
            : "cus-bg-theme-purple-medium hover:bg-gray-200"
        }`}
        onClick={onToggle}
      >
        <span className="ps-2">{title}</span>

        <svg
          className={`w-4 h-4 transition-transform duration-300 ${
            isOpen ? "rotate-180 text-blue-600" : "rotate-0"
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      <div
        className={`transition-all duration-300 ease-in-out overflow-hidden ${
          isOpen ? "max-h-[500px] opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        <div className="p-4 bg-white">{children}</div>
      </div>
    </div>
  );
};

export default AccordionItem;
