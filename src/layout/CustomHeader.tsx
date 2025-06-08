import React from "react";

type StatusCardProps = {
  color: string;
  label: string;
  value: number | string;
  icon: React.ReactNode;
};

const StatusCard: React.FC<StatusCardProps> = ({ color, label, value, icon }) => (
  <div className="flex items-center border border-[#DCDCDC] rounded-[14px] bg-[#ECECEC] shadow-md w-full sm:max-w-[200px] overflow-hidden">
    <div className="h-full w-[14px] rounded-l-xl" style={{ backgroundColor: color }} />
    <div className="flex items-center gap-3 px-4 py-2 w-full">
      <div className="text-gray-500 w-4 h-6">{icon}</div>
      <div className="border-l border-gray-300 h-8 items-center mx-2"/>
      <div>
        <p className="text-base inter-text-400 text-gray-500">{label}</p>
        <p className="text-2xl inter-text-700 text-gray-800">{value}</p>
      </div>
    </div>
  </div>
);

const CustomHeader: React.FC = () => {
  return (
    <div className="w-[calc(100%-2.5rem)] md:flex bg-gray-100 p-4 ml-8 rounded-lg">
      {/* Top Row: Status Cards */}
      <div className="md:w-[60%] grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 flex-wrap gap-4 sm:gap-2 xl:gap-1 mb-4">
        <StatusCard
          color="#1E6EE999"
          label="Total"
          value="100"
          icon={
            <svg height={30} width={30} viewBox="0 0 24 34" fill="none" xmlns="http://www.w3.org/2000/svg">
               <path d="M9.5 7H14.5M19.1433 2H4.85667C3.28 2 2 3.34333 2 5V29C2 30.6567 3.28 32 4.85667 32H19.1433C20.7217 32 22 30.6567 22 29V5C22 3.34333 20.7217 2 19.1433 2Z" stroke="#6F6F6F" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          }
        />
        <StatusCard
          color="#FC4B6C99"
          label="Assigned"
          value="25"
          icon={
            <svg height={30} width={30} viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
             <path d="M25.8333 28.5417L34.0833 20.2917C34.3889 19.9861 34.7778 19.8333 35.25 19.8333C35.7222 19.8333 36.1111 19.9861 36.4167 20.2917C36.7222 20.5972 36.875 20.9861 36.875 21.4583C36.875 21.9305 36.7222 22.3194 36.4167 22.625L27 32.0417C26.6667 32.375 26.2778 32.5417 25.8333 32.5417C25.3889 32.5417 25 32.375 24.6667 32.0417L19.9167 27.2917C19.6111 26.9861 19.4583 26.5972 19.4583 26.125C19.4583 25.6528 19.6111 25.2639 19.9167 24.9583C20.2222 24.6528 20.6111 24.5 21.0833 24.5C21.5556 24.5 21.9444 24.6528 22.25 24.9583L25.8333 28.5417ZM8.33333 35C7.41667 35 6.63222 34.6739 5.98 34.0217C5.32778 33.3694 5.00111 32.5844 5 31.6667V8.33332C5 7.41666 5.32667 6.63221 5.98 5.97999C6.63333 5.32777 7.41778 5.0011 8.33333 4.99999H15.2917C15.5972 4.02777 16.1944 3.22943 17.0833 2.60499C17.9722 1.98055 18.9444 1.66777 20 1.66666C21.1111 1.66666 22.1044 1.97943 22.98 2.60499C23.8556 3.23055 24.4456 4.02888 24.75 4.99999H31.6667C32.5833 4.99999 33.3683 5.32666 34.0217 5.97999C34.675 6.63332 35.0011 7.41777 35 8.33332V15C35 15.4722 34.84 15.8683 34.52 16.1883C34.2 16.5083 33.8044 16.6678 33.3333 16.6667C32.8622 16.6655 32.4667 16.5055 32.1467 16.1867C31.8267 15.8678 31.6667 15.4722 31.6667 15V8.33332H28.3333V11.6667C28.3333 12.1389 28.1733 12.535 27.8533 12.855C27.5333 13.175 27.1378 13.3344 26.6667 13.3333H13.3333C12.8611 13.3333 12.4656 13.1733 12.1467 12.8533C11.8278 12.5333 11.6678 12.1378 11.6667 11.6667V8.33332H8.33333V31.6667H16.6667C17.1389 31.6667 17.535 31.8267 17.855 32.1467C18.175 32.4667 18.3344 32.8622 18.3333 33.3333C18.3322 33.8044 18.1722 34.2005 17.8533 34.5217C17.5344 34.8428 17.1389 35.0022 16.6667 35H8.33333ZM20 8.33332C20.4722 8.33332 20.8683 8.17332 21.1883 7.85332C21.5083 7.53332 21.6678 7.13777 21.6667 6.66666C21.6656 6.19555 21.5056 5.79999 21.1867 5.47999C20.8678 5.15999 20.4722 4.99999 20 4.99999C19.5278 4.99999 19.1322 5.15999 18.8133 5.47999C18.4944 5.79999 18.3344 6.19555 18.3333 6.66666C18.3322 7.13777 18.4922 7.53388 18.8133 7.85499C19.1344 8.1761 19.53 8.33555 20 8.33332Z" fill="#6F6F6F"/>
            </svg>
          }
        />
        <StatusCard
          color="#1EC10899"
          label="In Stock"
          value="75"
          icon={
            <svg height={30} width={30} viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M8.33301 36.6673C7.41634 36.6673 6.6319 36.3412 5.97967 35.689C5.32745 35.0368 5.00079 34.2518 4.99967 33.334V14.5423C4.49967 14.2368 4.0969 13.8412 3.79134 13.3556C3.48579 12.8701 3.33301 12.3073 3.33301 11.6673V6.66732C3.33301 5.75065 3.65967 4.96621 4.31301 4.31398C4.96634 3.66176 5.75079 3.3351 6.66634 3.33398H33.333C34.2497 3.33398 35.0347 3.66065 35.688 4.31398C36.3413 4.96732 36.6674 5.75176 36.6663 6.66732V11.6673C36.6663 12.3062 36.5136 12.869 36.208 13.3556C35.9025 13.8423 35.4997 14.2373 34.9997 14.5407V33.334C34.9997 34.2507 34.6736 35.0357 34.0213 35.689C33.3691 36.3423 32.5841 36.6684 31.6663 36.6673H8.33301ZM8.33301 15.0007V33.334H31.6663V15.0007H8.33301ZM6.66634 11.6673H33.333V6.66732H6.66634V11.6673ZM14.9997 23.334H24.9997V20.0007H14.9997V23.334Z" fill="#6F6F6F"/>
            </svg>

          }
        />
        <StatusCard
          color="#FFA42D99"
          label="Call Muster"
          value="500"
          icon={
            <svg height={30} width={30} viewBox="0 0 24 34" fill="none" xmlns="http://www.w3.org/2000/svg">
               <path d="M9.5 7H14.5M19.1433 2H4.85667C3.28 2 2 3.34333 2 5V29C2 30.6567 3.28 32 4.85667 32H19.1433C20.7217 32 22 30.6567 22 29V5C22 3.34333 20.7217 2 19.1433 2Z" stroke="#6F6F6F" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          }
        />
      </div>

      {/* Bottom Row: Scan Instruction Card */}
       <div className="md:w-[40%] flex flex-col lg:flex-row rounded-xl overflow-hidden shadow-md bg-white mb-4 sm:ml-2 lg:ml-0">
          <div className="flex flex-col items-center justify-center bg-blue-100 px-4 py-4 lg:py-2 text-sm roboto-text text-gray-700 w-full lg:w-1/2">
            <p>Scan Student ID to Assign Mobile</p>
            <p>Scan Mobile QR to Return Mobile</p>
          </div>
          <div className="flex items-center justify-center px-4 py-2 text-gray-400 text-sm w-full lg:w-1/2">
            Scan ID/ Mobile Devices
          </div>
        </div>
    </div>
  );
};

export default CustomHeader;
