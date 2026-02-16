import { useState } from "react";
import { FaEye, FaEdit } from "react-icons/fa";
import { dynamicData } from "../../../../../model/dynamicData";
import AccordionItem from "@/components/accordion/AccordionItem";

interface AddressListMobProps {
  dataProp: dynamicData[];
  handleView: (row: dynamicData) => void;
  handleEdit: (row: dynamicData) => void;
}

export default function AddressListMob({
  dataProp,
  handleView,
  handleEdit,
}: AddressListMobProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  return (
    <div className="flex-1 overflow-y-auto px-2">
      {dataProp && dataProp.length > 0 ? (
        dataProp.map((address, index) => (
          <AccordionItem
            key={address.id}
            title={`${address.address1 ?? "--"} (id: ${address.id})`}
            isOpen={openIndex === index}
            onToggle={() => {
              const willOpen = openIndex !== index;
              setOpenIndex(willOpen ? index : null);

              if (willOpen) {
                handleView(address);
              }
            }}
          >
            {/* Accordion Content */}
            <div className="flex flex-col min-h-auto">
              {/* Content */}
              <div className="space-y-1 text-sm border-t">
                <p>
                  <strong>City:</strong> {address.city || "--"}
                </p>
                <p>
                  <strong>Country:</strong> {address.country || "--"}
                </p>
                <p>
                  <strong>Type:</strong> {address.address_type || "--"}
                </p>
              </div>
            </div>
          </AccordionItem>
        ))
      ) : (
        <p className="text-center text-gray-500">No addresses found.</p>
      )}
    </div>
  );
}
