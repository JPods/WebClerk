import { useState, useEffect } from "react";
import { dynamicData } from "../../../../../model/dynamicData";
import AccordionItem from "@/components/accordion/AccordionItem";

interface ContactListMobProps {
  dataProp: dynamicData[];
  selectedPhone?: dynamicData | null;
  handleView: (row: dynamicData) => void;
  handleEdit: (row: dynamicData) => void;
}

export default function PhoneListMob({
  dataProp,
  selectedPhone,
  handleView,
}: ContactListMobProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  useEffect(() => {
    if (selectedPhone?.id && dataProp?.length) {
      const idx = dataProp.findIndex(
        (item) => String(item.id) === String(selectedPhone.id),
      );
      setOpenIndex(idx >= 0 ? idx : null);
    } else {
      setOpenIndex(null);
    }
  }, [selectedPhone, dataProp]);
  return (
    <div className="flex-1 overflow-y-auto px-2">
      {dataProp && dataProp.length > 0 ? (
        dataProp.map((contact, index) => (
          <AccordionItem
            key={contact.id}
            title={`[id: ${contact.id}] ${contact.name ?? "--"} `}
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
            <div className="flex flex-col min-h-auto">
              {/* Content */}
              <div className="space-y-1 text-sm border-t">
                <p>
                  <strong>contact:</strong> {contact.contact || "--"}
                </p>
                <p>
                  <strong>number:</strong> {contact.number || "--"}
                </p>
                <p>
                  <strong>country_code:</strong> {contact.country_code || "--"}
                </p>
                <p>
                  <strong>attention:</strong> {contact.attention || "--"}
                </p>
                <div className="flex items-center gap-2">
                  <strong>opt_out:</strong>
                  {contact.opt_out ? (
                    <p className="text-green-600">Yes</p>
                  ) : (
                    <p className="text-red-500">No</p>
                  )}
                </div>
              </div>
            </div>
          </AccordionItem>
        ))
      ) : (
        <p className="text-center text-gray-500">No phone number found.</p>
      )}
    </div>
  );
}
