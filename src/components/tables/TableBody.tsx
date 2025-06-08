import { ChangeEvent, useState } from "react";

type TableBodyProps = {
  rows: any[];
};

export const TableBody = ({ rows }: TableBodyProps) => {

        const [selectedItems, setSelectedItems] = useState<number[]>([]);

        // Determine if all items are selected
        const allSelected = rows.length > 0 && selectedItems.length === rows.length;
        // Handle changes to individual checkboxes
        const handleItemCheckboxChange = (event: ChangeEvent<HTMLInputElement>, itemId: number) => {
            const isChecked = event.target.checked;

            if (isChecked) {
            setSelectedItems([...selectedItems, itemId]);
            } else {
            setSelectedItems(selectedItems.filter((id) => id !== itemId));
            }
        };

        // Handle changes to the "Select All" checkbox
        const handleSelectAllChange = (event: ChangeEvent<HTMLInputElement>) => {
            const isChecked = event.target.checked;

            if (isChecked) {
            // Select all item IDs
            setSelectedItems(rows.map((item) => item.sn));
            } else {
            // Deselect all items
            setSelectedItems([]);
            }
        };

   
    return (
        <div className=" h-[620px] overflow-y-scroll">
        <table className="min-w-full table-auto text-left ml-4">
            <thead className="bg-[#C5DAFF] text-sm md:h-16 sticky top-0 z-10">
            <tr>
                <th className="px-4 py-2 rounded-l-[7px]">
                <input type="checkbox" checked={allSelected} onChange={handleSelectAllChange} style={{ transform: 'scale(1.5)', margin: 0, verticalAlign: 'middle' }} />
                </th>
                <th className="px-4 py-2 ">S.N</th>
                <th className="px-4 py-2 roboto-text">Class</th>
                <th className="px-4 py-2 roboto-text">Division</th>
                <th className="px-4 py-2 roboto-text">Roll No</th>
                <th className="px-4 py-2 roboto-text">Student Name</th>
                <th className="px-4 py-2 roboto-text">Assigned Device</th>
                <th className="px-4 py-2 roboto-text">Assigned On</th>
                <th className="px-4 py-2 roboto-text">Returned On</th>
                <th className="px-4 py-2 roboto-text">Action</th>
            </tr>
            </thead>
            <tbody>
            {rows.map((row) => (
                <tr key={row.sn} className="even:bg-gray-100 text-sm text-gray-700">
                    <td className="px-4 py-2 rounded-l-[7px]">
                    <input type="checkbox" checked={selectedItems.includes(row.sn)} onChange={(event) => handleItemCheckboxChange(event, row.sn)} 
                           style={{ transform: 'scale(1.5)', margin: 0, verticalAlign: 'middle', border: '1px solid', borderColor: '#989898' }} 
                    />
                    </td>
                    <td className="px-4 py-4">{row.sn}</td>
                    <td className="px-4 py-4 inter-text-400">{row.class}</td>
                    <td className="px-4 py-4 inter-text-400">{row.division}</td>
                    <td className="px-4 py-4 inter-text-400">{row.rollNo}</td>
                    <td className="px-4 py-4 inter-text-400">{row.name}</td>
                    <td className="px-4 py-4 inter-text-400">{row.device}</td>
                    <td className="px-4 py-4 inter-text-400">{row.assignedOn}</td>
                    <td className="px-4 py-4 inter-text-400">{row.returnedOn}</td>
                    <td className="px-0 py-4 inter-text-400 flex justify-center">
                    {/* Replace with actual SVG */}
                        <svg width="55" height="25" viewBox="0 0 55 25" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M42.0542 3.89532H35.7898C35.3151 3.89532 34.8599 4.08389 34.5242 4.41955C34.1886 4.75521 34 5.21046 34 5.68515V18.2139C34 18.6886 34.1886 19.1438 34.5242 19.4795C34.8599 19.8151 35.3151 20.0037 35.7898 20.0037H48.3186C48.7933 20.0037 49.2485 19.8151 49.5842 19.4795C49.9198 19.1438 50.1084 18.6886 50.1084 18.2139V11.9495" stroke="black" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M47.7592 3.55969C48.1152 3.20367 48.5981 3.00366 49.1016 3.00366C49.6051 3.00366 50.0879 3.20367 50.4439 3.55969C50.8 3.91571 51 4.39857 51 4.90205C51 5.40554 50.8 5.8884 50.4439 6.24442L42.3781 14.3111C42.1656 14.5235 41.9031 14.6789 41.6148 14.7631L39.0437 15.5148C38.9667 15.5373 38.8851 15.5386 38.8074 15.5187C38.7296 15.4988 38.6587 15.4584 38.602 15.4016C38.5453 15.3449 38.5049 15.274 38.4849 15.1963C38.465 15.1186 38.4664 15.037 38.4888 14.9599L39.2406 12.3889C39.3252 12.1008 39.4809 11.8386 39.6934 11.6264L47.7592 3.55969Z" stroke="black" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M3.275 15.296C2.425 14.192 2 13.639 2 12C2 10.36 2.425 9.809 3.275 8.704C4.972 6.5 7.818 4 12 4C16.182 4 19.028 6.5 20.725 8.704C21.575 9.81 22 10.361 22 12C22 13.64 21.575 14.191 20.725 15.296C19.028 17.5 16.182 20 12 20C7.818 20 4.972 17.5 3.275 15.296Z" stroke="black" stroke-width="1.5"/>
                        <path d="M15 12C15 12.7956 14.6839 13.5587 14.1213 14.1213C13.5587 14.6839 12.7956 15 12 15C11.2044 15 10.4413 14.6839 9.87868 14.1213C9.31607 13.5587 9 12.7956 9 12C9 11.2044 9.31607 10.4413 9.87868 9.87868C10.4413 9.31607 11.2044 9 12 9C12.7956 9 13.5587 9.31607 14.1213 9.87868C14.6839 10.4413 15 11.2044 15 12Z" stroke="black" stroke-width="1.5"/>
                        </svg>

                    </td>
                </tr>
            ))}
            </tbody>
        </table>
        </div>
   )};
