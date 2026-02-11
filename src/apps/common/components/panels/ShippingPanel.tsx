/**
 * ShippingPanel - Shared shipping details panel for sell-side transactions
 */
import React, { useState } from "react";
import { FaTruck, FaChevronDown, FaChevronUp } from "react-icons/fa";
import { usePermissions } from "./usePermissions";
import type { BasePanelProps } from "./types";

type AnyRecord = Record<string, any>;

export interface ShippingPanelData {
  ship_date?: string;
  ship_via?: string;
  fob?: string;
  weight?: number;
  refs?: {
    links?: {
      contact?: AnyRecord[];
      location?: AnyRecord[];
    };
  };
}

interface ShippingPanelProps
  extends Omit<
    BasePanelProps<ShippingPanelData>,
    "data" | "entityType" | "entityId"
  > {
  data?: ShippingPanelData;
}

const formatDate = (value?: string) => {
  if (!value) return "--";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString();
};

const ShippingPanel: React.FC<ShippingPanelProps> = ({
  data,
  readOnly: _readOnly = false,
  viewRoles,
  editRoles,
  className = "",
  compact = false,
  title = "Shipping",
  defaultCollapsed = false,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);

  const { canView } = usePermissions({
    panelType: "shipping",
    viewRoles,
    editRoles,
    forceReadOnly: true,
  });

  if (canView === false) return null;

  const record = (data ?? {}) as AnyRecord;
  const contacts: AnyRecord[] = record.refs?.links?.contact ?? [];
  const locations: AnyRecord[] = record.refs?.links?.location ?? [];

  const shippingContact = contacts.find((c) => c.purpose === "shipto");
  const shippingLocation = locations.find((l) => l.type === "shipto");
  const address = shippingLocation?.address as AnyRecord | undefined;

  return (
    <div
      className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 ${className}`}
    >
      <div
        className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 cursor-pointer"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaTruck className="text-slate-400" size={14} />
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
            {title}
          </h3>
        </div>
        {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
      </div>

      {!isCollapsed && (
        <div className={compact ? "p-2" : "p-4"}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
              <h4 className="font-semibold text-slate-900 dark:text-white mb-3">
                Shipping Details
              </h4>
              <dl className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <dt className="text-slate-500 dark:text-slate-400">Ship Date</dt>
                  <dd className="text-slate-900 dark:text-white">
                    {formatDate(record.ship_date)}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500 dark:text-slate-400">Ship Via</dt>
                  <dd className="text-slate-900 dark:text-white">
                    {record.ship_via ?? "--"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500 dark:text-slate-400">FOB</dt>
                  <dd className="text-slate-900 dark:text-white">
                    {record.fob ?? "--"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500 dark:text-slate-400">Weight</dt>
                  <dd className="text-slate-900 dark:text-white">
                    {record.weight ? `${record.weight} kg` : "--"}
                  </dd>
                </div>
              </dl>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
              <h4 className="font-semibold text-slate-900 dark:text-white mb-3">
                Ship To Address
              </h4>
              {shippingContact ? (
                <div className="text-xs text-slate-700 dark:text-slate-300 space-y-1">
                  <p className="font-medium">
                    {shippingContact.display_name ||
                      shippingContact.name ||
                      `Contact #${shippingContact.contact_id ?? shippingContact.id ?? ""}`}
                  </p>
                  {shippingContact.company && <p>{shippingContact.company}</p>}
                  {address && (
                    <>
                      {address.street && <p>{address.street}</p>}
                      {(address.city || address.state || address.zip) && (
                        <p>
                          {[address.city, address.state, address.zip]
                            .filter(Boolean)
                            .join(", ")}
                        </p>
                      )}
                      {address.country && <p>{address.country}</p>}
                    </>
                  )}
                  {shippingContact.phone && (
                    <p className="mt-2">Tel: {shippingContact.phone}</p>
                  )}
                </div>
              ) : (
                <p className="text-slate-400 text-xs">
                  No shipping address specified
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ShippingPanel;
