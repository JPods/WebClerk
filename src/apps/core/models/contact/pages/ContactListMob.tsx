import { useState } from "react";
import { FaEye, FaEdit, FaCheck, FaTimes } from "react-icons/fa";
import { dynamicData } from "../../../../../model/dynamicData";
import AccordionItem from "@/components/accordion/AccordionItem";

interface ContactListMobProps {
  dataProp: dynamicData[];
  handleView: (row: dynamicData) => void;
  handleEdit: (row: dynamicData) => void;
}

export default function ContactListMob({
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
            title={`Email: ${contact.email ?? "--"} (ID: ${contact.id})`}
            isOpen={openIndex === index}
            onToggle={() => setOpenIndex(openIndex === index ? null : index)}
          >
            {/* Accordion Content */}
            <div className="flex flex-col min-h-[220px]">
              {/* Content */}
              <div className="space-y-1 text-sm">
                <p>
                  <strong>First Name:</strong> {contact.name_first || "--"}
                </p>
                <p>
                  <strong>Last Name:</strong> {contact.name_last || "--"}
                </p>
                <p>
                  <strong>Company:</strong> {contact.company || "--"}
                </p>
                <p>
                  <strong>Role:</strong> {contact.role || "--"}
                </p>

                <div className="flex items-center gap-2">
                  <strong>Active:</strong>
                  {contact.is_active ? (
                    <p className="text-green-600">Yes</p>
                  ) : (
                    <p className="text-red-500">No</p>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <strong>Staff:</strong>
                  {contact.is_staff ? (
                    <p className="text-green-600">Yes</p>
                  ) : (
                    <p className="text-red-500">No</p>
                  )}
                </div>
              </div>

              {/* Footer Actions */}
              <div className="mt-auto pt-3 border-t flex justify-end gap-4 bg-white sticky bottom-0">
                <button
                  onClick={() => handleView(contact)}
                  title="View"
                  className="h-[38px] w-[38px] flex items-center justify-center
                         border rounded-md hover:text-green-600"
                >
                  <FaEye className="text-green-600 hover:scale-110" />
                </button>

                <button
                  onClick={() => handleEdit(contact)}
                  title="Edit"
                  className="h-[38px] w-[38px] flex items-center justify-center
                         border rounded-md hover:text-blue-600"
                >
                  <FaEdit className="text-blue-600 hover:scale-110" />
                </button>
              </div>
            </div>
          </AccordionItem>
        ))
      ) : (
        <p className="text-center text-gray-500">No contacts found.</p>
      )}
    </div>
  );
}
