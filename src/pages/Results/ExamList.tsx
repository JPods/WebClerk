import { useEffect, useState } from "react";
import { TableBody } from "../../components/tables/TableBody";
import TableContainer from "../../components/tables/TableContainer";
import TableFooter from "../../components/tables/TableFooter";
import TableHeader from "../../components/tables/TableHeader";

type StudentRow = {
  sn: number;
  class: string;
  division: string;
  rollNo: number;
  name: string;
  device: number;
  assignedOn: string;
  returnedOn: string;
};

export default function ExamList() {

  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [totalItems, setTotalItems] = useState(0);
  const itemsPerPageOptions = [10, 25, 50];
  const [data, setData] = useState<StudentRow[]>([]);

  useEffect(() => {
    // Simulate fetching data based on currentPage and itemsPerPage
    const fetchData = async () => {
      console.log("show data", currentPage);
      // Replace this with your actual API call or data fetching logic
      const startIndex = (currentPage - 1) * itemsPerPage;
      const endIndex = startIndex + itemsPerPage;
      const allData = Array.from({ length: 500 }, (_, i) => (
        { 
          sn: i + 1,
          class: "2023-25",
          division: "NEET A1 Boys",
          rollNo: 1000 + i + 1,
          name: `Item ${i + 1}`,
          device: 234567 + i + 1,
          assignedOn: "2024-10-01 10:43:30",
          returnedOn: "2024-10-01 10:50:01",
        })); // Example data

      const paginatedData = allData.slice(startIndex, endIndex);
      setData(paginatedData);
      setTotalItems(allData.length);
    };

    fetchData();
  }, [currentPage, itemsPerPage]);

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
  };

  const handleItemsPerPageChange = (newItemsPerPage: number) => {
    setItemsPerPage(newItemsPerPage);
    setCurrentPage(1); // Reset to the first page when items per page changes
  };

  return (
    <>
      <TableContainer>
        <TableHeader />
        <TableBody rows={data} />
        <TableFooter 
            totalItems={totalItems}
            itemsPerPageOptions={itemsPerPageOptions}
            initialItemsPerPage={itemsPerPage}
            onPageChange={handlePageChange}
            onItemsPerPageChange={handleItemsPerPageChange} 
        />
      </TableContainer>
     </>
  );
}
