import { useState } from "react";
import { FaEye, FaEdit, FaCheck, FaTimes } from "react-icons/fa";
import { dynamicData } from "../../../../../model/dynamicData";
import AccordionItem from "@/components/accordion/AccordionItem";

interface ContactListMobProps {
  dataProp: dynamicData[];
  handleView: (row: dynamicData) => void;
  handleEdit: (row: dynamicData) => void;
}

export default function LocationListMob({
  dataProp,
  handleView,
  handleEdit,
}: ContactListMobProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  return (
    <div className="flex-1 overflow-y-auto px-2">
      {dataProp && dataProp.length > 0 ? (
        dataProp.map((contact, index) => (
          <AccordionItem
            key={contact.id}
            title={`address1: ${contact.address1 ?? "--"} (id: ${contact.id})`}
            isOpen={openIndex === index}
            onToggle={() => {
              const willOpen = openIndex !== index;
              setOpenIndex(willOpen ? index : null);

              if (willOpen) {
                handleView(contact); // 👈 FIXED
              }
            }}
          >
            {/* Accordion Content */}
            <div className="flex flex-col min-h-[220px]">
              {/* Content */}
              <div className="space-y-1 text-sm border-t">
                <p>
                  <strong>city:</strong> {contact.city || "--"}
                </p>
                <p>
                  <strong>country:</strong> {contact.country || "--"}
                </p>
                <p>
                  <strong>address_type:</strong> {contact.address_type || "--"}
                </p>
              </div>

              {/* Footer Actions */}
              <div className="mt-auto pt-3 border-t flex justify-end gap-1 bg-white sticky bottom-0">
                <button
                  onClick={() => handleView(contact)}
                  title="View"
                  className="h-[25px] w-[25px] flex items-center justify-center
                         border rounded-md hover:text-green-600"
                >
                  <FaEye className="text-green-600 hover:scale-110" />
                </button>

                <button
                  onClick={() => handleEdit(contact)}
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
        <p className="text-center text-gray-500">No email found.</p>
      )}
    </div>
  );
}
