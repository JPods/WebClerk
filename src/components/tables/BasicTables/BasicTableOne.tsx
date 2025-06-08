import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "../../ui/table";

import Badge from "../../ui/badge/Badge";
import { useEffect, useState } from "react";
import { getExamList } from "../../../api/exam";
import { useAppDispatch } from "../../../store/hooks";
import { showToast } from "../../../store/slices/toastSlice";
import Switch from "../../form/switch/Switch";


interface examList {
  test_name: string;
  date: string; // or Date if you'll parse it
  subject_id: string;
  class_id: number | null;
  division_id: number | null;
  test_no: string;
  max_marks: string;
  status: "Active" | "Inactive" | string; // more specific if you know all possible statuses
  id: number;
  subject_name: string;
  created_on: string; // or Date
  updated_on: string; // or Date
}

export default function BasicTableOne() {
     const dispatch = useAppDispatch();
     const [tableData, setTableData] = useState<examList[]>([]) 
     useEffect(() => {
          ExamList()
     },[])

     const ExamList = async() => {
          try {
               const res = await getExamList(1)
               if(res.return_status === 1)
                   setTableData(res.return_data)
          } catch (error:any) {               
               dispatch(showToast({ message: error.message, type: "error" }));
          }
     }

     const handleSwitchChange = (checked: boolean) => {
      console.log("Switch is now:", checked ? "ON" : "OFF");
    };

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-white/[0.05] dark:bg-white/[0.03]">
      <div className="max-w-full overflow-x-auto">
        <Table>
          {/* Table Header */}
          <TableHeader className="border-b border-gray-100 dark:border-white/[0.05]">
            <TableRow>
              <TableCell
                isHeader
                className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
              >
                Sl No.
              </TableCell>
              <TableCell
                isHeader
                className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
              >
                Test No.
              </TableCell>
              <TableCell
                isHeader
                className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
              >
                Test Name
              </TableCell>
              <TableCell
                isHeader
                className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
              >
                Date
              </TableCell>
              <TableCell
                isHeader
                className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
              >
                Subject
              </TableCell>
              <TableCell
                isHeader
                className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
              >
                Max Mark
              </TableCell>
              <TableCell
                isHeader
                className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
              >
                Class & Divisions
              </TableCell>
              <TableCell
                isHeader
                className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
              >
                Status
              </TableCell>
              <TableCell
                isHeader
                className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
              >
                Action
              </TableCell>
            </TableRow>
          </TableHeader>

          {/* Table Body */}
          <TableBody className="divide-y divide-gray-100 dark:divide-white/[0.05]">
            {tableData.map((order,index) => (
              <TableRow key={order.id}>
                <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                  {index + 1}
                </TableCell>
                <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                  {order.test_no}
                </TableCell>
                <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                  {order.test_name}
                </TableCell>                
                <TableCell className="px-4 py-3 text-gray-500 text-theme-sm dark:text-gray-400">
                  {order.date}
                </TableCell>
                <TableCell className="px-4 py-3 text-gray-500 text-theme-sm dark:text-gray-400">
                  {order.subject_name}
                </TableCell>
                <TableCell className="px-4 py-3 text-gray-500 text-theme-sm dark:text-gray-400">
                  {order.max_marks}
                </TableCell>
                <TableCell className="px-4 py-3 text-gray-500 text-theme-sm dark:text-gray-400">
                  {order.class_id}
                </TableCell>
                <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                  {/* <Badge
                    size="sm"
                    color={
                      order.status === "Active"
                        ? "success"
                        : order.status === "Inactive"
                        ? "warning"
                        : "error"
                    }
                  >
                    {order.status}
                  </Badge> */}
                  <Switch
                    label=""
                    defaultChecked={order.status === "Active" ? true : false}
                    onChange={handleSwitchChange}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
