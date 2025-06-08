import React from 'react';

interface RangeInputFieldProps {
  label: string;
  startId: string;
  endId: string;
  startValue: string | number;
  endValue: string | number;
  onStartChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onEndChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  type?: 'text' | 'number'; // Allow specifying input type
  className?: string; // Optional classes for the outer container
}

const RangeInputField: React.FC<RangeInputFieldProps> = ({
  label,
  startId,
  endId,
  startValue,
  endValue,
  onStartChange,
  onEndChange,
  type = 'text', // Default to number as per the Figma
  className = '',
}) => {
  return (
    <div className={`flex flex-col ${className}`}>
      {/* Label for the section (e.g., Physics) */}
      <label htmlFor={startId} className="block text-sm font-semibold text-gray-700 mb-2">
        {label}
      </label>

      {/* The combined input container */}
      <div className="flex items-center justify-between w-full border border-gray-300 rounded-md shadow-sm px-3 py-2 bg-white overflow-hidden">
        {/* Start No. Input */}
        <input
          type={type}
          id={startId}
          name={startId}
          placeholder="Start no."
          value={startValue}
          onChange={onStartChange}
          className="flex-1 min-w-0 text-sm text-gray-700 placeholder-gray-400 focus:outline-none bg-transparent border-none pl-[5%] lg:pl-[10%] focus:ring-0 appearance-none"
          // bg-transparent and no border to make it look like part of the parent container
        />

        {/* Dash Separator */}
        <span className=" text-gray-500 font-medium select-none mx-[15%]">—</span>
        {/* <span className="text-gray-500 font-medium select-none px-2">-</span> */}
        {/* End No. Input */}
        <input
          type={type}
          id={endId}
          name={endId}
          placeholder="End no."
          value={endValue}
          onChange={onEndChange}
          className="flex-1 min-w-0 text-sm text-gray-700 placeholder-gray-400 focus:outline-none bg-transparent border-none focus:ring-0 appearance-none"
          // text-right to align placeholder and value to the right as in Figma
        />
      </div>
    </div>
  );
};

export default RangeInputField;