import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import ComponentCard from "../../components/common/ComponentCard";

import { useEffect, useState } from "react";
import { Contacts } from "../../api/userProfile";


interface Item {
  id: number;
  title: string;
  description: string;
  author: string;
}

// Dummy data to populate the list.
const initialItems: Item[] = [
  {
    id: 1,
    title: 'Getting Started with React',
    description: 'An introductory guide to setting up a React development environment and building your first component.',
    author: 'Alice Johnson'
  },
  {
    id: 2,
    title: 'Tailwind CSS for Beginners',
    description: 'Learn the fundamentals of utility-first CSS and how to integrate Tailwind into your projects efficiently.',
    author: 'Bob Williams'
  },
  {
    id: 3,
    title: 'State Management with Redux',
    description: 'A deep dive into managing complex application state using the Redux pattern and modern Redux Toolkit.',
    author: 'Charlie Brown'
  },
  {
    id: 4,
    title: 'Building a Node.js API',
    description: 'Explore how to create a RESTful API from scratch using Express.js and a MongoDB database.',
    author: 'Diana Miller'
  },
  {
    id: 5,
    title: 'Advanced TypeScript Features',
    description: 'Understand and apply advanced TypeScript concepts like generics, utility types, and decorators.',
    author: 'Evan Davis'
  },
];

export default function ContactList() {

      const [selectedItem, setSelectedItem] = useState<Item | null>(initialItems[0]);
  
  // State for the form data, used for editing.
  const [editingItem] = useState<Item | null>(null);


// const [ setData] = useState<dynamicData[]>([]);

// const navigate = useNavigate()
// const dispatch = useDispatch()

//const handleView = (row: any) => {
//     navigate(PageRoutes.actionAdd, {state: {mode:'view', data:row}})
// };

//   const handleEdit = (row: any) => {
//     navigate(PageRoutes.actionAdd, {state: {mode:'edit', data:row}})
//   };

//   const handleDelete = async(row: any) => {
//     if (window.confirm(`Delete task with ID ${row.id}?`)) {
//       try {
//         deleteAction(row.id)      
//         dispatch(showToast({ message: "Action delete Successfully", type: "success" }));
//         // setData((prev:dynamicData) => 
//         //     prev.filter((list: { id: any; }) => list.id !== row.id))
//       } catch (error) {
        
//       }
//     }
//   };

useEffect(() => {
   getActionData()
},[])
 const getActionData = async() => {
      try {
         const res = await Contacts()       
         if(res.status === 200)
         {            
            //setData(res.data)
         }
         
      } catch (error) {
        
      }
  }

// const userColumns: TableColumn<dynamicData>[] = [
//   { name: 'ID', selector: row => row.id, sortable: true },
//   { name: 'Priority', selector: row => row.priority, sortable: true },
//   { name: 'Difficulty', selector: row => row.difficulty, sortable: true },
//   { name: 'Status', selector: row => row.status, sortable: true },
//   { name: 'Quality', selector: row => row.quality, sortable: true },
//   { name: 'Hours', selector: row => row.hours, sortable: true },
//   { name: 'Percent', selector: row => `${row.percent}%`, sortable: true },
//   { name: 'Due Date', selector: row => new Date(row.dt_due).toLocaleString(), sortable: true },
//   { name: 'Completed On', selector: row => new Date(row.dt_completed).toLocaleString(), sortable: true },
//   { name: 'Last Updated', selector: row => new Date(row.dt_updated).toLocaleString(), sortable: true },
//   {
//     name: 'Action',
//     cell: (row) => (
//       <div className="flex gap-2">
//         <button onClick={() => handleView(row)} title="View">
//           <FaEye className="text-blue-600 hover:scale-110 transition" />
//         </button>
//         <button onClick={() => handleEdit(row)} title="Edit">
//           <FaEdit className="text-green-600 hover:scale-110 transition" />
//         </button>
//         <button onClick={() => handleDelete(row)} title="Delete">
//           <FaTrash className="text-red-600 hover:scale-110 transition" />
//         </button>
//       </div>
//     ),
//     ignoreRowClick: true,
//     allowOverflow: true,
//     button: true,
//   },
// ];

  return (
    <>
      <PageBreadcrumb pageTitle="Contact List" />
      <div className="space-y-6">
        <ComponentCard>              
                <div className={`flex flex-col md:flex-row h-screen font-sans antialiased transition-colors duration-300`}>
      
  
                <div className="w-full md:w-2/3 p-6 overflow-y-auto border-b md:border-b-0 md:border-r border-gray-300 dark:border-gray-700">
                   
                    <div className="overflow-x-auto">
                    <table className="min-w-full table-auto">
                        <thead className="text-left border-b border-gray-300 dark:border-gray-700">
                        <tr>
                            <th className="px-4 py-2 font-medium">Title</th>
                            <th className="px-4 py-2 font-medium hidden sm:table-cell">Author</th>
                        </tr>
                        </thead>
                        <tbody>
                        {initialItems.map((item) => (
                            <tr
                            key={item.id}
                            onClick={() => setSelectedItem(item)}
                            // Conditional styling based on selection.
                            className={`cursor-pointer transition-all duration-200 border-b border-gray-200 dark:border-gray-700
                                ${selectedItem?.id === item.id
                                ? 'bg-blue-600 text-white'
                                : 'bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700'
                                }`}
                            >
                            <td className="px-4 py-3">
                                <div className="font-semibold text-base">{item.title}</div>
                                <div className="text-sm sm:hidden opacity-80">{item.author}</div>
                            </td>
                            <td className="px-4 py-3 hidden sm:table-cell text-sm opacity-80">{item.author}</td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                    </div>
                </div>  

                <div className="w-full md:w-2/3 p-6 flex items-center justify-center">
                    {editingItem ? (
                    <form className="w-full max-w-2xl bg-white dark:bg-gray-800 p-8 rounded-xl shadow-lg transform transition-transform duration-300 scale-100">
                        <h2 className="text-4xl font-bold mb-6 text-blue-600 dark:text-blue-400">Edit Article</h2>
                        
                        <div className="mb-4">
                        <label htmlFor="title" className="block text-sm font-medium mb-1">title</label>
                        <input
                            type="text"
                            id="title"
                            name="title"
                            value={editingItem.title}
                            
                            className="w-full px-4 py-2 rounded-lg border-2 border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors duration-200 dark:bg-gray-700"
                        />
                        </div>
                        
                        <div className="mb-4">
                        <label htmlFor="author" className="block text-sm font-medium mb-1">author</label>
                        <input
                            type="text"
                            id="author"
                            name="author"
                            value={editingItem.author}
                    
                            className="w-full px-4 py-2 rounded-lg border-2 border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors duration-200 dark:bg-gray-700"
                        />
                        </div>
                        
                        <div className="mb-6">
                        <label htmlFor="description" className="block text-sm font-medium mb-1">description</label>
                        <textarea
                            id="description"
                            name="description"
                            value={editingItem.description}
                            
                            rows={5}
                            className="w-full px-4 py-2 rounded-lg border-2 border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors duration-200 dark:bg-gray-700"
                        />
                        </div>
                        
                        <div className="flex justify-end space-x-4">
                        <button
                            type="button"
                            onClick={() => setSelectedItem(selectedItem)} // Cancel button resets the form
                            className="px-6 py-3 rounded-lg font-medium text-gray-700 dark:text-gray-300 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors duration-200"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="px-6 py-3 rounded-lg font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors duration-200"
                        >
                            Save Changes
                        </button>
                        </div>
                    </form>
                    ) : (
                    <div className="text-center text-lg text-gray-500 dark:text-gray-400">
                        <p>Select an article from the list to view and edit its details.</p>
                    </div>
                    )}
                </div>
                </div>
        </ComponentCard>       
      </div>
    </>
  );
}
