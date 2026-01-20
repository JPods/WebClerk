import { useState } from "react";
import { FaEye, FaEdit, FaCheck, FaTimes } from "react-icons/fa";
import { dynamicData } from "../../../../../../model/dynamicData";
import AccordionItem from "@/components/accordion/AccordionItem";

interface VendorMobProps {
  dataProp: dynamicData[];
  handleView: (row: dynamicData) => void;
  handleEdit: (row: dynamicData) => void;
}

export default function VendorListMob({
  dataProp,
  handleView,
  handleEdit,
}: VendorMobProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  return (
    <div className="flex-1 overflow-y-auto px-2">
      {dataProp && dataProp.length > 0 ? (
        dataProp.map((vendor, index) => (
          <AccordionItem
            key={vendor.id}
            title={`display_name: ${vendor.display_name ?? "--"} (id: ${
              vendor.id
            })`}
            isOpen={openIndex === index}
            onToggle={() => {
              const willOpen = openIndex !== index;
              setOpenIndex(willOpen ? index : null);

              if (willOpen) {
                handleView(vendor);
              }
            }}
          >
            {/* Accordion Content */}
            <div className="flex flex-col min-h-[220px]">
              {/* Content */}
              <div className="space-y-1 text-sm">
                <p>
                  <strong>org_type:</strong> {vendor.org_type || "--"}
                </p>
                <p>
                  <strong>status:</strong> {vendor.status || "--"}
                </p>
                <p>
                  <strong>version:</strong> {vendor.version || "--"}
                </p>

                <div className="flex items-center gap-2">
                  <strong>is_active:</strong>
                  {vendor.is_active ? (
                    <p className="text-green-600">Yes</p>
                  ) : (
                    <p className="text-red-500">No</p>
                  )}
                </div>
              </div>

              {/* Footer Actions */}
              <div className="mt-auto pt-3 border-t flex justify-end gap-1 bg-white sticky bottom-0">
                <button
                  onClick={() => handleView(vendor)}
                  title="View"
                  className="h-[25px] w-[25px] flex items-center justify-center
                         border rounded-md hover:text-green-600"
                >
                  <FaEye className="text-green-600 hover:scale-110" />
                </button>

                <button
                  onClick={() => handleEdit(vendor)}
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
        <p className="text-center text-gray-500">No vendor found.</p>
      )}
    </div>
  );
}
