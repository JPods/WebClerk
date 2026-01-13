import { useState } from "react";
import { FaEye, FaEdit, FaCheck, FaTimes } from "react-icons/fa";
import AccordionItem from "@/components/accordion/AccordionItem";

interface ActionData {
  id: string | number;
  email?: string;
  name_first?: string;
  name_last?: string;
  company?: string;
  role?: string;
  is_active?: boolean;
  is_staff?: boolean;
  [key: string]: any;
}

interface ContactListMobProps {
  dataProp: ActionData[];
  handleView: (row: ActionData) => void;
  handleEdit: (row: ActionData) => void;
  emptyMessage?: string;
}

export default function ContactListMob({
  dataProp,
  handleView,
  handleEdit,
  emptyMessage,
}: ContactListMobProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  return (
    <div className="flex-1 overflow-y-auto px-2">
      {dataProp && dataProp.length > 0 ? (
        dataProp.map((contact, index) => (
          <AccordionItem
            key={contact.id}
            title={`email: ${contact.email ?? "--"} (id: ${contact.id})`}
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
                  <strong>name_first:</strong> {contact.name_first || "--"}
                </p>
                <p>
                  <strong>name_last:</strong> {contact.name_last || "--"}
                </p>
                <p>
                  <strong>attention:</strong> {contact.attention || "--"}
                </p>

                <p>
                  <strong>company:</strong> {contact.company || "--"}
                </p>
                <p>
                  <strong>role:</strong> {contact.role || "--"}
                </p>
                <div className="flex items-center gap-2">
                  <strong>is_active:</strong>
                  {contact.is_active ? (
                    <p className="text-green-600">Yes</p>
                  ) : (
                    <p className="text-red-500">No</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <strong>is_staff:</strong>
                  {contact.is_staff ? (
                    <p className="text-green-600">Yes</p>
                  ) : (
                    <p className="text-red-500">No</p>
                  )}
                </div>
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
        <p className="text-center text-gray-500">
          {emptyMessage ?? "No contacts found."}
        </p>
      )}
    </div>
  );
}
