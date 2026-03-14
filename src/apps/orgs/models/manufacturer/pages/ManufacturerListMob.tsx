/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useState } from "react";
import { FaEye, FaEdit, FaCheck, FaTimes } from "react-icons/fa";
import { dynamicData } from "../../../../../model/dynamicData";
import AccordionItem from "@/components/accordion/AccordionItem";

interface ManufacturerAddProps {
  dataProp: dynamicData[];
  handleView: (row: dynamicData) => void;
  handleEdit: (row: dynamicData) => void;
}

export default function ManufacturerListMob({
  dataProp,
  handleView,
  handleEdit,
}: ManufacturerAddProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  return (
    <div className="flex-1 overflow-y-auto px-2">
      {dataProp && dataProp.length > 0 ? (
        dataProp.map((employee, index) => (
          <AccordionItem
            key={employee.id}
            title={`display_name: ${employee.display_name ?? "--"} (id: ${
              employee.id
            })`}
            isOpen={openIndex === index}
            onToggle={() => {
              const willOpen = openIndex !== index;
              setOpenIndex(willOpen ? index : null);

              if (willOpen) {
                handleView(employee);
              }
            }}
          >
            {/* Accordion Content */}
            <div className="flex flex-col min-h-[220px]">
              {/* Content */}
              <div className="space-y-1 text-sm">
                <p>
                  <strong>org_type:</strong> {employee.org_type || "--"}
                </p>
                <p>
                  <strong>status:</strong> {employee.status || "--"}
                </p>
                <p>
                  <strong>version:</strong> {employee.version || "--"}
                </p>

                <div className="flex items-center gap-2">
                  <strong>is_active:</strong>
                  {employee.is_active ? (
                    <p className="text-green-600">Yes</p>
                  ) : (
                    <p className="text-red-500">No</p>
                  )}
                </div>
              </div>

              {/* Footer Actions */}
              <div className="mt-auto pt-3 border-t flex justify-end gap-1 bg-white sticky bottom-0">
                <button
                  onClick={() => handleView(employee)}
                  title="View"
                  className="h-[25px] w-[25px] flex items-center justify-center
                         border rounded-md hover:text-green-600"
                >
                  <FaEye className="text-green-600 hover:scale-110" />
                </button>

                <button
                  onClick={() => handleEdit(employee)}
                  title="Edit"
                  className="h-[25px] w-[25px] flex items-center justify-center
                         border rounded-md hover:text-blue-600"
                >
                  <FaEdit className="text-blue-600 hover:scale-110" />
                </button>
              </div>
            </div>
          </AccordionItem>
        ))
      ) : (
        <p className="text-center text-gray-500">No employee found.</p>
      )}
    </div>
  );
}
