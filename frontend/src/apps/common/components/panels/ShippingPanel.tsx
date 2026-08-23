/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * ShippingPanel - Shared shipping details panel for sell-side transactions
 */
import React, { useState } from "react";
import { FaTruck, FaChevronDown, FaChevronUp } from "react-icons/fa";
import { usePermissions } from "./usePermissions";
import type { BasePanelProps } from "./types";
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { formatDt } from '@/utils/fieldFormatters';

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
  return formatDt(value, 'date');
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
  const locations: AnyRecord[] = record.refs?.links?.address ?? [];

  const shippingContact = contacts.find((c) => c.purpose === "shipto");
  const shippingLocation = locations.find((l) => l.type === "shipto");
  const address = shippingLocation?.address as AnyRecord | undefined;

  return (
    <div
      className={`rounded-lg border ${className}`}
      style={{ background: 'var(--db-surface)', borderColor: 'var(--db-border)' }}
    >
      <div
        className="flex items-center justify-between px-4 py-3 border-b cursor-pointer"
        style={{ borderColor: 'var(--db-border)' }}
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaTruck style={{ color: 'var(--db-text-dim)' }} size={14} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--db-text)' }}>
            {title}
          </h3>
        </div>
        {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
      </div>

      {!isCollapsed && (
        <div className={compact ? "p-2" : "p-4"}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="rounded-lg border p-4" style={{ background: 'var(--db-surface)', borderColor: 'var(--db-border)' }}>
              <h4 className="font-semibold mb-3" style={{ color: 'var(--db-text)' }}>
                Shipping Details
              </h4>
              <dl className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <dt style={{ color: 'var(--db-text-muted)' }}>Ship Date</dt>
                  <dd style={{ color: 'var(--db-text)' }}>
                    {formatDate(record.ship_date)}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt style={{ color: 'var(--db-text-muted)' }}>Ship Via</dt>
                  <dd style={{ color: 'var(--db-text)' }}>
                    {record.ship_via ?? "--"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt style={{ color: 'var(--db-text-muted)' }}>FOB</dt>
                  <dd style={{ color: 'var(--db-text)' }}>
                    {record.fob ?? "--"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt style={{ color: 'var(--db-text-muted)' }}>Weight</dt>
                  <dd style={{ color: 'var(--db-text)' }}>
                    {record.weight ? `${record.weight} kg` : "--"}
                  </dd>
                </div>
              </dl>
            </div>

            <div className="rounded-lg border p-4" style={{ background: 'var(--db-surface)', borderColor: 'var(--db-border)' }}>
              <h4 className="font-semibold mb-3" style={{ color: 'var(--db-text)' }}>
                Ship To Address
              </h4>
              {shippingContact ? (
                <div className="text-xs space-y-1" style={{ color: 'var(--db-text)' }}>
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
                <p className="text-xs" style={{ color: 'var(--db-text-dim)' }}>
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

export default withDevIdentifier(ShippingPanel, 'ShippingPanel', 'teal', 'apps/common/components/panels/ShippingPanel.tsx');