import React, { useState, useEffect } from 'react';

interface PaginationProps {
  totalItems: number;
  itemsPerPageOptions: number[];
  initialItemsPerPage?: number;
  onPageChange: (pageNumber: number) => void;
  onItemsPerPageChange: (itemsPerPage: number) => void;
}

const TableFooter: React.FC<PaginationProps> = ({
  totalItems,
  itemsPerPageOptions,
  initialItemsPerPage = itemsPerPageOptions[0] || 10,
  onPageChange,
  onItemsPerPageChange,
}) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(initialItemsPerPage);
  const totalPages = Math.ceil(totalItems / itemsPerPage);

  useEffect(() => {
    //setCurrentPage(1); // Reset to the first page when itemsPerPage changes
    onItemsPerPageChange(itemsPerPage);
  }, [itemsPerPage, onItemsPerPageChange]);

  useEffect(() => {
    onPageChange(currentPage);
  }, [currentPage, onPageChange]);

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  const handlePrevious = () => {
    handlePageChange(currentPage - 1);
  };

  const handleNext = () => {
    handlePageChange(currentPage + 1);
  };

  const handleItemsPerPageChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const newItemsPerPage = parseInt(event.target.value, 10);
    setCurrentPage(1)
    setItemsPerPage(newItemsPerPage);
  };

  const renderPageNumbers = () => {
    const pageNumbers = [];
    const maxVisiblePages = 7; // Adjust as needed

    if (totalPages <= maxVisiblePages) {
      for (let i = 1; i <= totalPages; i++) {
        pageNumbers.push(i);
      }
    } else {
      pageNumbers.push(1);
      if (currentPage > 3) {
        pageNumbers.push('...');
      }
      const middlePages = [];
      for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) {
        middlePages.push(i);
      }
      pageNumbers.push(...middlePages);
      if (currentPage < totalPages - 2) {
        pageNumbers.push('...');
      }
      pageNumbers.push(totalPages);
    }

    return pageNumbers.map((page, index) => (

      <button
        key={index}
        onClick={() => typeof page === 'number' && handlePageChange(page)}
        className={`page-number ${currentPage === page ? 'active bg-[#1D458B] text-white' : 'bg-white text-[#333]'}  py-2 px-[6px] sm:px-4 border-l-1 border-[#DBDBDB] cursor-pointer`}
        disabled={typeof page === 'string'}
      >
        {page}
      </button>
    ));
  };

  return (
    <div className='w-full flex flex-col sm:flex-row justify-between items-center p-4'>
      <div className=''>
        <label className='inter-text-500 text-[#0B131C] text-base mr-2' htmlFor="itemsPerPage">
          Showing {currentPage} to 
        </label>
        <select
          id="itemsPerPage"
          value={itemsPerPage}
          onChange={handleItemsPerPageChange}
          style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
        >
          {itemsPerPageOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <span className='inter-text-500 text-[#0B131C] text-base ml-2'>of {totalItems} entries</span>
      </div>
      <div className=' border border-[#DBDBDB] rounded-[5px] mt-2 sm:mt-0'>
        <button
          onClick={handlePrevious}
          disabled={currentPage === 1}
          className='inter-text-400 py-2 px-1 sm:px-3 my-0 mx-1 sm:mx-0 cursor-pointer'
        >
          Previous
        </button>
        {renderPageNumbers()}
        <button
          className='inter-text-400 py-2 px-1 sm:px-3 border-l-1 border-[#DBDBDB] cursor-pointer'
          onClick={handleNext}
          disabled={currentPage === totalPages || totalPages === 0}
        >
          Next
        </button>
      </div>
    </div>
  );
};

export default TableFooter;
