import React from "react";

type Props = {
  children: React.ReactNode;
};

const TableContainer = ({ children }: Props) => (
  <div className="overflow-x-auto rounded-xl shadow bg-white">
    {children}
  </div>
);

export default TableContainer;
