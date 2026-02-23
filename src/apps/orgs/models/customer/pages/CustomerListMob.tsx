import { useState, useEffect } from "react";
import { FaEye, FaEdit, FaCheck, FaTimes } from "react-icons/fa";
import { dynamicData } from "../../../../../model/dynamicData";
import AccordionItem from "@/components/accordion/AccordionItem";
import { CustomerApiTask } from "../types/customerType";
interface CustomerListMobProps {
  dataProp: dynamicData[];
  selectedCustomer?: CustomerApiTask | null;
  handleView: (row: dynamicData) => void;
  handleEdit: (row: dynamicData) => void;
  emptyMessage?: string;
}

export default function CustomerListMob({
  dataProp,
  selectedCustomer,
  handleView,
  handleEdit,
  emptyMessage,
}: CustomerListMobProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  useEffect(() => {
    if (selectedCustomer?.id && dataProp?.length) {
      const idx = dataProp.findIndex(
        (item) => String(item.id) === String(selectedCustomer.id),
      );
      setOpenIndex(idx >= 0 ? idx : null);
    } else {
      setOpenIndex(null);
    }
  }, [selectedCustomer, dataProp]);

  return (
    <div className="flex-1 overflow-y-auto px-2">
      {dataProp && dataProp.length > 0 ? (
        dataProp.map((customer, index) => (
          <AccordionItem
            key={customer.id}
            title={`display_name: ${customer.display_name ?? "--"} (id: ${
              customer.id
            })`}
            isOpen={openIndex === index}
            onToggle={() => {
              const willOpen = openIndex !== index;
              setOpenIndex(willOpen ? index : null);
              if (willOpen) {
                handleView(customer);
              }
            }}
          >
            {/* Accordion Content */}
            <div className="flex flex-col min-h-auto">
              {/* Content */}
              <div className="space-y-1 text-sm border-t">
                <p>
                  <strong>org_type:</strong> {customer.org_type || "--"}
                </p>
                <p>
                  <strong>status:</strong> {customer.status || "--"}
                </p>
                <p>
                  <strong>version:</strong> {customer.version || "--"}
                </p>
                <p>
                  <strong>display_name:</strong> {customer.display_name || "--"}
                </p>
                <p>
                  <strong>company:</strong> {customer.company || "--"}
                </p>
                <div className="flex items-center gap-2">
                  <strong>is_active:</strong>
                  {customer.is_active ? (
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
        <p className="text-center text-gray-500">
          {emptyMessage ?? "No customer found."}
        </p>
      )}
    </div>
  );
}
