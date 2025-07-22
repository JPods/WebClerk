import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import ComponentCard from "../../components/common/ComponentCard";

import DataTable, { TableColumn } from 'react-data-table-component';
import { useEffect, useState } from "react";
import { deleteAction, getAction } from "../../api/userProfile";
import { dynamicData } from "../../model/dynamicData";
import { FaEye, FaEdit, FaTrash } from 'react-icons/fa'; 
import { useNavigate } from "react-router";
import { PageRoutes } from "../../routes/Routes";
import { showToast } from "../../store/slices/toastSlice";
import { useDispatch } from "react-redux";

export default function ContactList() {

const [globalFilter, setGlobalFilter] = useState('');
const [data, setData] = useState<dynamicData[]>([]);

const navigate = useNavigate()
const dispatch = useDispatch()

const handleView = (row: any) => {
    navigate(PageRoutes.actionAdd, {state: {mode:'view', data:row}})
};

  const handleEdit = (row: any) => {
    navigate(PageRoutes.actionAdd, {state: {mode:'edit', data:row}})
  };

  const handleDelete = async(row: any) => {
    if (window.confirm(`Delete task with ID ${row.id}?`)) {
      try {
        deleteAction(row.id)      
        dispatch(showToast({ message: "Action delete Successfully", type: "success" }));
        setData((prev:dynamicData) => 
            prev.filter((list: { id: any; }) => list.id !== row.id))
      } catch (error) {
        
      }
    }
  };

useEffect(() => {
   getActionData()
},[])
 const getActionData = async() => {
      try {
         const res = await getAction()       
         if(res.status === 200)
         {            
            setData(res.data)
         }
         
      } catch (error) {
        
      }
  }

const userColumns: TableColumn<dynamicData>[] = [
  { name: 'ID', selector: row => row.id, sortable: true },
  { name: 'Priority', selector: row => row.priority, sortable: true },
  { name: 'Difficulty', selector: row => row.difficulty, sortable: true },
  { name: 'Status', selector: row => row.status, sortable: true },
  { name: 'Quality', selector: row => row.quality, sortable: true },
  { name: 'Hours', selector: row => row.hours, sortable: true },
  { name: 'Percent', selector: row => `${row.percent}%`, sortable: true },
  { name: 'Due Date', selector: row => new Date(row.dt_due).toLocaleString(), sortable: true },
  { name: 'Completed On', selector: row => new Date(row.dt_completed).toLocaleString(), sortable: true },
  { name: 'Last Updated', selector: row => new Date(row.dt_updated).toLocaleString(), sortable: true },
  {
    name: 'Action',
    cell: (row) => (
      <div className="flex gap-2">
        <button onClick={() => handleView(row)} title="View">
          <FaEye className="text-blue-600 hover:scale-110 transition" />
        </button>
        <button onClick={() => handleEdit(row)} title="Edit">
          <FaEdit className="text-green-600 hover:scale-110 transition" />
        </button>
        <button onClick={() => handleDelete(row)} title="Delete">
          <FaTrash className="text-red-600 hover:scale-110 transition" />
        </button>
      </div>
    ),
    ignoreRowClick: true,
    allowOverflow: true,
    button: true,
  },
];

  return (
    <>
      <PageBreadcrumb pageTitle="Contact List" />
      <div className="space-y-6">
        <ComponentCard>              
                {/* <input
                    type="text"
                    className="border p-2 w-full max-w-md"
                    placeholder="Global search..."
                    value={globalFilter}
                    onChange={e => setGlobalFilter(e.target.value)}
                /> */}
                <div className="overflow-x-auto">
                    <DataTable
                    // title="User List"
                    columns={userColumns}
                    data={data}
                    pagination
                    />  
                </div>        
        </ComponentCard>       
      </div>
    </>
  );
}
