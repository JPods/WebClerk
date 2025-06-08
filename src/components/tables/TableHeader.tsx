import React, { useState } from "react";
import TableToolbarButton from "./TableToolbarButton";

const TableHeader = () => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [isExpanded2, setIsExpanded2] = useState(false);
    const [isExpanded3, setIsExpanded3] = useState(false);

  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
    setIsExpanded2(false);
    setIsExpanded3(false);
  };

  const toggleExpand2 = () => {
    setIsExpanded2(!isExpanded2);
     setIsExpanded(false);
     setIsExpanded3(false);
  };
  const toggleExpand3 = () => {
    setIsExpanded3(!isExpanded3);
     setIsExpanded2(false);
    setIsExpanded(false);
  };

  const optionButtonStyle = {
  background: 'none',
  borderTop: '1px solid #B3D1FF',
  borderBottom: '1px solid #B3D1FF',
  padding: '7px 16px',
  cursor: 'pointer',
  color: '#333',
};

const optionButtonStyle2 = {
  background: 'none',
  borderTop: '1px solid #A5E69C',
  borderBottom: '1px solid #A5E69C',
  padding: '7px 16px',
  cursor: 'pointer',
  color: '#333',
};

const optionButtonStyle3= {
  background: 'none',
  borderTop: '1px solid #B3D1FF',
  borderBottom: '1px solid #B3D1FF',
  padding: '7px 16px',
  cursor: 'pointer',
  color: '#BDBDBD',
};
  return (
    <div className="flex flex-wrap gap-4 p-4 rounded-t-xl mt-0 lg:mt-0">

            {/*  add new open */}
            <div className=" inline-flex items-center rounded-lg overflow-hidden">
                <button className="roboto-text bg-[#1EC108] text-white flex items-center cursor-pointer py-2 px-4" onClick={toggleExpand2}>
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ marginRight:"8px"}}>
                    <path d="M6 8H0V6H6V0H8V6H14V8H8V14H6V8Z" fill="white"/>
                    </svg>

                    Add New
                </button>
                <div className={`transition-all duration-300 ease-in-out border-l border-gray-300 ${isExpanded2 ? 'opacity-100 flex' : 'opacity-0 hidden'}`}>
                    <button style={optionButtonStyle2}>Add New Quick</button>
                    <div className="border-l border-gray-300 h-6 items-center mt-2"/>
                    <button style={optionButtonStyle2}>Bulk Upload</button>
                    <div className="border-l border-gray-300 h-6 items-center mt-2"/>
                    <button style={optionButtonStyle2}>Bulk Update</button>
                    <div className="border-l border-gray-300 h-6 items-center mt-2"/>
                    <button style={optionButtonStyle2}>Bulk Photos Upload</button>
                </div>
                <div onClick={toggleExpand2} className="bg-[#1EC10866] text-[#757575] p-2 cursor-pointer h-10">
                    <svg width="7" height="12" viewBox="0 0 7 12" fill="none" xmlns="http://www.w3.org/2000/svg" style={{marginTop:'7px'}}>
                    <path fill-rule="evenodd" clip-rule="evenodd" d="M0.317185 11.6704C0.52034 11.8813 0.795841 11.9998 1.0831 11.9998C1.37036 11.9998 1.64586 11.8813 1.84902 11.6704L6.18235 7.17037C6.38545 6.9594 6.49954 6.67331 6.49954 6.375C6.49954 6.07669 6.38545 5.79059 6.18235 5.57962L1.84902 1.07962C1.6447 0.874693 1.37105 0.761299 1.087 0.763863C0.802954 0.766425 0.531241 0.884741 0.330382 1.09333C0.129523 1.30191 0.0155903 1.58407 0.013122 1.87905C0.0106537 2.17402 0.119848 2.45819 0.317185 2.67037L3.8846 6.375L0.317185 10.0796C0.114092 10.2906 0 10.5767 0 10.875C0 11.1733 0.114092 11.4594 0.317185 11.6704Z" fill="#1EC108"/>
                    </svg>
                </div>
            </div>
            {/*  add new close */}

            {/* action open */}
                <div style={{ display: 'inline-flex', alignItems: 'center', borderRadius: '8px', overflow: 'hidden' }}>
            <button
                onClick={toggleExpand3}
                style={{
                background: '#4285F4', // Example blue color
                color: 'white',
                border: 'none',
                padding: '8px 16px',
                display: 'flex',
                alignItems: 'center',
                cursor: 'pointer',
                }}
            >
                <svg width="16" height="18" viewBox="0 0 16 18" fill="none" xmlns="http://www.w3.org/2000/svg" style={{marginLeft:"4px", marginRight:"8px"}}>
                    <path d="M5.11073 10.3775L6.74989 11.8108V4.41667C6.74979 4.25246 6.78202 4.08984 6.84476 3.93809C6.9075 3.78634 6.99951 3.64844 7.11554 3.53225C7.34989 3.29759 7.66785 3.16564 7.99948 3.16542C8.33111 3.1652 8.64925 3.29673 8.8839 3.53107C9.00009 3.6471 9.09229 3.78489 9.15523 3.93655C9.21817 4.08822 9.25062 4.2508 9.25073 4.415L9.25406 8.385L11.4507 8.74084C12.8691 8.9575 13.5782 9.065 14.0774 9.36834C14.9024 9.87 15.4999 10.6667 15.4999 11.7217C15.4999 12.4867 15.3132 13 14.8599 14.38C14.5724 15.255 14.4282 15.6925 14.1932 16.0383C13.8098 16.607 13.2397 17.0238 12.5816 17.2167C12.1832 17.3333 11.7282 17.3333 10.8191 17.3333H10.0474C8.83739 17.3333 8.23323 17.3333 7.69406 17.1083C7.5978 17.0672 7.50353 17.0216 7.41156 16.9717C6.89989 16.69 6.51823 16.2133 5.75573 15.2617L3.28656 12.18C3.1016 11.9493 3.00025 11.6627 2.99903 11.367C2.99782 11.0713 3.09682 10.7839 3.27989 10.5517C3.38583 10.416 3.5183 10.3034 3.66922 10.2206C3.82014 10.1379 3.98634 10.0868 4.15767 10.0704C4.32901 10.054 4.50188 10.0727 4.66574 10.1254C4.8296 10.178 4.98101 10.2644 5.11073 10.3775Z" stroke="white" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M3.83333 5.66667H3.14667C1.9 5.66667 1.275 5.66667 0.888333 5.3C0.5 4.935 0.5 4.34584 0.5 3.16667C0.5 1.98751 0.5 1.39917 0.8875 1.03334C1.275 0.667505 1.9 0.666672 3.14667 0.666672H12.8525C14.1008 0.666672 14.725 0.666672 15.1125 1.03334C15.5 1.39834 15.5 1.98751 15.5 3.16667C15.5 4.34584 15.5 4.93417 15.1125 5.3C14.725 5.66584 14.1 5.66667 12.8525 5.66667H12.1667" stroke="white" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                  Action
            </button>
            <div
                style={{
                display: isExpanded3 ? 'flex' : 'none',
                borderLeft: '1px solid #ccc',
                }}
            >
                <button style={optionButtonStyle3}>View</button>
                <div className="border-l border-gray-300 h-6 items-center mt-2"/>
                <button style={optionButtonStyle3}>Copy</button>
                <div className="border-l border-gray-300 h-6 items-center mt-2"/>
                <button style={optionButtonStyle3}>Edit</button>
                <div className="border-l border-gray-300 h-6 items-center mt-2"/>
                <button style={optionButtonStyle3}>Print</button>
                <div className="border-l border-gray-300 h-6 items-center mt-2"/>
                <button style={optionButtonStyle3}>Delete</button>
            </div>
            <div style={{ background: '#408BFF66', color: '#757575', padding: '8px', cursor: 'pointer', height:'40px' }}>
                <svg width="7" height="12" viewBox="0 0 7 12" fill="none" xmlns="http://www.w3.org/2000/svg" style={{marginTop:'7px'}}>
                    <path fill-rule="evenodd" clip-rule="evenodd" d="M0.317185 11.6704C0.52034 11.8813 0.795841 11.9998 1.0831 11.9998C1.37036 11.9998 1.64586 11.8813 1.84902 11.6704L6.18235 7.17037C6.38545 6.9594 6.49954 6.67331 6.49954 6.375C6.49954 6.07669 6.38545 5.79059 6.18235 5.57962L1.84902 1.07962C1.6447 0.874693 1.37105 0.761299 1.087 0.763863C0.802954 0.766425 0.531241 0.884741 0.330382 1.09333C0.129523 1.30191 0.0155903 1.58407 0.013122 1.87905C0.0106537 2.17402 0.119848 2.45819 0.317185 2.67037L3.8846 6.375L0.317185 10.0796C0.114092 10.2906 0 10.5767 0 10.875C0 11.1733 0.114092 11.4594 0.317185 11.6704Z" fill="#408BFF"/>
                </svg>
            </div>
            </div>

            {/* action close */}

            <div style={{ display: 'inline-flex', alignItems: 'center', borderRadius: '8px', overflow: 'hidden' }}>
            <button
                onClick={toggleExpand}
                style={{
                background: '#4285F4', // Example blue color
                color: 'white',
                border: 'none',
                padding: '8px 16px',
                display: 'flex',
                alignItems: 'center',
                cursor: 'pointer',
                }}
            >
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" style={{marginLeft:"4px", marginRight:"8px"}}>
                <path d="M3.33301 5C3.33301 6.38083 6.31801 7.5 9.99967 7.5C13.6813 7.5 16.6663 6.38083 16.6663 5C16.6663 3.61917 13.6813 2.5 9.99967 2.5C6.31801 2.5 3.33301 3.61917 3.33301 5Z" stroke="white" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M3.33301 5V10C3.33301 11.3808 6.31801 12.5 9.99967 12.5C10.9313 12.5 11.8188 12.4283 12.6247 12.2992M16.6663 10V5" stroke="white" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M3.33301 10V15C3.33301 16.3808 6.31801 17.5 9.99967 17.5C10.1302 17.5 10.2597 17.4986 10.388 17.4958M13.333 15.8333H18.333M18.333 15.8333L15.833 13.3333M18.333 15.8333L15.833 18.3333" stroke="white" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>

                  Export
            </button>
            <div
                style={{
                display: isExpanded ? 'flex' : 'none',
                borderLeft: '1px solid #ccc',
                }}
            >
                <button style={optionButtonStyle}>Csv</button>
                <div className="border-l border-gray-300 h-6 items-center mt-2"/>
                <button style={optionButtonStyle}>Excel</button>
                <div className="border-l border-gray-300 h-6 items-center mt-2"/>
                <button style={optionButtonStyle}>PDF</button>
            </div>
            <div style={{ background: '#408BFF66', color: '#757575', padding: '8px', cursor: 'pointer', height:'40px' }}>
                <svg width="7" height="12" viewBox="0 0 7 12" fill="none" xmlns="http://www.w3.org/2000/svg" style={{marginTop:'7px'}}>
                    <path fill-rule="evenodd" clip-rule="evenodd" d="M0.317185 11.6704C0.52034 11.8813 0.795841 11.9998 1.0831 11.9998C1.37036 11.9998 1.64586 11.8813 1.84902 11.6704L6.18235 7.17037C6.38545 6.9594 6.49954 6.67331 6.49954 6.375C6.49954 6.07669 6.38545 5.79059 6.18235 5.57962L1.84902 1.07962C1.6447 0.874693 1.37105 0.761299 1.087 0.763863C0.802954 0.766425 0.531241 0.884741 0.330382 1.09333C0.129523 1.30191 0.0155903 1.58407 0.013122 1.87905C0.0106537 2.17402 0.119848 2.45819 0.317185 2.67037L3.8846 6.375L0.317185 10.0796C0.114092 10.2906 0 10.5767 0 10.875C0 11.1733 0.114092 11.4594 0.317185 11.6704Z" fill="#408BFF"/>
                </svg>
            </div>
            </div>

    </div>
  );
};

export default TableHeader;
