import { useState, useEffect } from "react";
import { dynamicData } from "../../../../../model/dynamicData";
import AccordionItem from "@/components/accordion/AccordionItem";

interface AddressListMobProps {
  dataProp: dynamicData[];
  selectedAddress?: dynamicData | null;
  handleView: (row: dynamicData) => void;
  handleEdit: (row: dynamicData) => void;
}

export default function AddressListMob({
  dataProp,
  selectedAddress,
  handleView,
}: AddressListMobProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  useEffect(() => {
    if (selectedAddress?.id && dataProp?.length) {
      const idx = dataProp.findIndex(
        (item) => String(item.id) === String(selectedAddress.id),
      );
      setOpenIndex(idx >= 0 ? idx : null);
    } else {
      setOpenIndex(null);
    }
  }, [selectedAddress, dataProp]);
  return (
    <div className="flex-1 overflow-y-auto px-2">
      {dataProp && dataProp.length > 0 ? (
        dataProp.map((address, index) => (
          <AccordionItem
            key={address.id}
            title={`[id: ${address.id}] ${address.address1 ?? "--"} `}
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
                  <strong>contact:</strong> {address.contact || "--"}
                </p>
                <p>
                  <strong>city:</strong> {address.city || "--"}
                </p>
                <p>
                  <strong>country:</strong> {address.country || "--"}
                </p>
                <p>
                  <strong>latitude:</strong> {address.latitude || "--"}
                </p>
                <p>
                  <strong>longitude:</strong> {address.longitude || "--"}
                </p>
                <p>
                  <strong>address_type:</strong> {address.address_type || "--"}
                </p>
                <p>
                  <strong>full:</strong> {address.full || "--"}
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
