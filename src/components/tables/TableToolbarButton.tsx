import React, { useState } from "react";


type Props = {
  label: string;
  children: React.ReactNode;
  className?: string;
};

const TableToolbarButton = ({ label, children, className = "" }: Props) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-md shadow hover:bg-blue-600 transition"
      >
        {label}
        {expanded ? 
           <svg width="7" height="12" viewBox="0 0 7 12" fill="none" xmlns="http://www.w3.org/2000/svg">
             <path fill-rule="evenodd" clip-rule="evenodd" d="M0.317185 11.6704C0.52034 11.8813 0.795841 11.9998 1.0831 11.9998C1.37036 11.9998 1.64586 11.8813 1.84902 11.6704L6.18235 7.17037C6.38545 6.9594 6.49954 6.67331 6.49954 6.375C6.49954 6.07669 6.38545 5.79059 6.18235 5.57962L1.84902 1.07962C1.6447 0.874693 1.37105 0.761299 1.087 0.763863C0.802954 0.766425 0.531241 0.884741 0.330382 1.09333C0.129523 1.30191 0.0155903 1.58407 0.013122 1.87905C0.0106537 2.17402 0.119848 2.45819 0.317185 2.67037L3.8846 6.375L0.317185 10.0796C0.114092 10.2906 0 10.5767 0 10.875C0 11.1733 0.114092 11.4594 0.317185 11.6704Z" fill="#1EC108"/>
           </svg>
        : 
           <svg width="7" height="12" viewBox="0 0 7 12" fill="none" xmlns="http://www.w3.org/2000/svg">
             <path fill-rule="evenodd" clip-rule="evenodd" d="M6.68281 11.6704C6.47966 11.8813 6.20416 11.9998 5.9169 11.9998C5.62964 11.9998 5.35414 11.8813 5.15098 11.6704L0.817648 7.17037C0.614554 6.9594 0.500463 6.67331 0.500463 6.375C0.500463 6.07669 0.614554 5.79059 0.817648 5.57962L5.15098 1.07962C5.3553 0.874693 5.62895 0.761299 5.913 0.763863C6.19705 0.766425 6.46876 0.884741 6.66962 1.09333C6.87048 1.30191 6.98441 1.58407 6.98688 1.87905C6.98935 2.17402 6.88015 2.45819 6.68281 2.67037L3.1154 6.375L6.68281 10.0796C6.88591 10.2906 7 10.5767 7 10.875C7 11.1733 6.88591 11.4594 6.68281 11.6704Z" fill="#408BFF"/>
           </svg>
        }
      </button>
      {expanded && (
        <div className="absolute mt-2 w-full bg-white border rounded shadow z-10">
          {children}
        </div>
      )}
    </div>
  );
};

export default TableToolbarButton;
