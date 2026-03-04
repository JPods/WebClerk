import { useState, useEffect } from "react";
import { dynamicData } from "../../../../../model/dynamicData";
import AccordionItem from "@/components/accordion/AccordionItem";

interface DomainListMobProps {
  dataProp: dynamicData[];
  selectedDomain?: dynamicData | null;
  handleView: (row: dynamicData) => void;
  handleEdit: (row: dynamicData) => void;
}

export default function DomainListMob({
  dataProp,
  selectedDomain,
  handleView,
}: DomainListMobProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  useEffect(() => {
    if (selectedDomain?.id && dataProp?.length) {
      const idx = dataProp.findIndex(
        (item) => String(item.id) === String(selectedDomain.id),
      );
      setOpenIndex(idx >= 0 ? idx : null);
    } else {
      setOpenIndex(null);
    }
  }, [selectedDomain, dataProp]);
  return (
    <div className="flex-1 overflow-y-auto px-2">
      {dataProp && dataProp.length > 0 ? (
        dataProp.map((contact, index) => (
          <AccordionItem
            key={contact.id}
            title={`[id: ${contact.id}]  ${
              (contact.path ?? "--").length > 40
                ? `${(contact.path ?? "--").slice(0, 40)}...`
                : contact.path ?? "--"
            }`}
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
                  <strong>path:</strong> {contact.path || "--"}
                </p>
                <p>
                  <strong>type:</strong> {contact.type || "--"}
                </p>
              </div>
            </div>
          </AccordionItem>
        ))
      ) : (
        <p className="text-center text-gray-500">No domain found.</p>
      )}
    </div>
  );
}
