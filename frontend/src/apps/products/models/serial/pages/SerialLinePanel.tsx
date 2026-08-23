/**
 * SerialLinePanel — Display serial numbers associated with a transaction line.
 *
 * Works for purchase lines (receiving), order lines (reserved), and
 * invoice lines (shipped). Shows serials linked to the line via
 * config.purchase_id/purchase_line_ref or config.order_id/sales_line_ref
 * or config.invoice_id.
 *
 * Context-aware: shows different info based on document type.
 * Inline panel — no separate window. Click the line, see the serials.
 */
import { useEffect, useState, useMemo } from "react";
import { getRecords } from "@/api/wcapi";
import {
  Hash,
  Package,
  DollarSign,
  Shield,
  MapPin,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
  FileText,
} from "lucide-react";
import ComponentCard from "@/components/common/ComponentCard";

// -- Types ------------------------------------------------------------------

interface SerialRecord {
  id: number;
  serial_ida: string;
  model_ida: string;
  description: string;
  status: string;
  warranty: Record<string, any>;
  site: Record<string, any>;
  config: Record<string, any>;
}

type DocContext = "purchase" | "order" | "invoice";

interface SerialLinePanelProps {
  /** Which document type this line belongs to */
  context: DocContext;
  /** The item on this line */
  itemId: number;
  itemIda?: string;
  /** Document and line IDs to filter serials */
  documentId?: number;
  lineId?: number;
  /** Expected quantity (from the line) — shown for count validation */
  qtyExpected?: number;
  /** Start collapsed? */
  defaultCollapsed?: boolean;
}

// -- Status badge -----------------------------------------------------------

const STATUS_STYLES: Record<string, { bg: string; icon: any }> = {
  received: { bg: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200", icon: Package },
  available: { bg: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200", icon: CheckCircle },
  reserved: { bg: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200", icon: Clock },
  issued: { bg: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200", icon: Package },
  returned: { bg: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200", icon: AlertTriangle },
  damaged: { bg: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200", icon: XCircle },
  scrapped: { bg: "bg-slate-100 text-slate-800 dark:bg-slate-900 dark:text-slate-200", icon: XCircle },
  warranty: { bg: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200", icon: Shield },
};

function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.received;
  const Icon = style.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${style.bg}`}>
      <Icon size={10} />
      {status}
    </span>
  );
}

// -- Context labels ---------------------------------------------------------

const CONTEXT_LABELS: Record<DocContext, { title: string; verb: string }> = {
  purchase: { title: "Received Serials", verb: "received on" },
  order: { title: "Reserved Serials", verb: "reserved for" },
  invoice: { title: "Shipped Serials", verb: "issued on" },
};

// -- Component --------------------------------------------------------------

export default function SerialLinePanel({
  context,
  itemId,
  itemIda,
  documentId,
  lineId,
  qtyExpected,
  defaultCollapsed = false,
}: SerialLinePanelProps) {
  const [serials, setSerials] = useState<SerialRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  const labels = CONTEXT_LABELS[context];

  // Build query filters based on context
  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);

        // Query serials linked to this document/line via config JSON fields
        const params: Record<string, any> = {
          item_id: itemId,
          page_size: 500,
        };

        // Filter by the appropriate config field based on context
        if (context === "purchase") {
          if (documentId) params["config__purchase_id"] = documentId;
          if (lineId) params["config__purchase_line_ref"] = lineId;
        } else if (context === "order") {
          if (documentId) params["config__order_id"] = documentId;
          if (lineId) params["config__sales_line_ref"] = lineId;
        } else if (context === "invoice") {
          if (documentId) params["config__invoice_id"] = documentId;
          if (lineId) params["config__sales_line_ref"] = lineId;
        }

        const result = await getRecords("serial", params);
        const items = result?.items || result?.data?.items || [];
        setSerials(items);
      } catch (err) {
        console.error("Failed to load serials:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [itemId, documentId, lineId, context]);

  // Count validation
  const serialCount = serials.length;
  const countMatch = qtyExpected != null ? serialCount === qtyExpected : null;

  // Recent action per serial (last entry in config.actions[])
  const lastAction = (serial: SerialRecord): string => {
    const actions = serial.config?.actions || [];
    if (actions.length === 0) return "";
    return actions[actions.length - 1]?.action || "";
  };

  // Warranty info
  const warrantyInfo = (serial: SerialRecord): string | null => {
    const w = serial.warranty || {};
    if (!w.dt_end) return null;
    try {
      const end = new Date(w.dt_end);
      const now = new Date();
      if (end < now) return "Expired";
      const days = Math.ceil((end.getTime() - now.getTime()) / (86400 * 1000));
      return `${days}d remaining`;
    } catch {
      return null;
    }
  };

  if (loading) {
    return (
      <div className="py-3 text-center text-sm text-slate-500">
        Loading serials...
      </div>
    );
  }

  if (serials.length === 0 && !loading) {
    return (
      <div className="py-3 text-center text-sm text-slate-500">
        No serial numbers {labels.verb} this line
      </div>
    );
  }

  return (
    <ComponentCard>
      {/* Header — collapsible */}
      <button
        className="w-full flex items-center justify-between"
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
            {labels.title}
          </h4>
          {itemIda && (
            <span className="text-xs text-slate-500">{itemIda}</span>
          )}

          {/* Count badge */}
          <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
              countMatch === true
                ? "bg-green-100 text-green-800"
                : countMatch === false
                ? "bg-red-100 text-red-800"
                : "bg-slate-100 text-slate-800"
            }`}
          >
            {serialCount}
            {qtyExpected != null && ` / ${qtyExpected}`}
          </span>
        </div>

        {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
      </button>

      {/* Serial list */}
      {!collapsed && (
        <div className="mt-3 divide-y divide-slate-100 dark:divide-slate-800">
          {serials.map((serial) => {
            const warranty = warrantyInfo(serial);
            const recent = lastAction(serial);
            const cost = serial.config?.cost || 0;

            return (
              <div
                key={serial.id}
                className="flex items-center gap-3 py-2.5 first:pt-0"
              >
                {/* Serial number */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Hash size={12} className="text-slate-400 flex-shrink-0" />
                    <span className="text-sm font-medium text-slate-900 dark:text-white">
                      {serial.serial_ida}
                    </span>
                    {serial.model_ida && (
                      <span className="text-xs text-slate-500">
                        {serial.model_ida}
                      </span>
                    )}
                    <StatusBadge status={serial.status} />
                  </div>

                  {/* Detail row */}
                  <div className="flex items-center gap-3 mt-0.5 text-xs text-slate-500">
                    {cost > 0 && (
                      <span>
                        <DollarSign size={10} className="inline" />
                        {cost.toFixed(2)}
                      </span>
                    )}
                    {warranty && (
                      <span>
                        <Shield size={10} className="inline mr-0.5" />
                        {warranty}
                      </span>
                    )}
                    {serial.site?.warehouse_id && (
                      <span>
                        <MapPin size={10} className="inline mr-0.5" />
                        WH {serial.site.warehouse_id}
                      </span>
                    )}
                    {recent && (
                      <span>
                        <FileText size={10} className="inline mr-0.5" />
                        {recent}
                      </span>
                    )}
                  </div>
                </div>

                {/* Action count */}
                <div className="text-xs text-slate-400 flex-shrink-0">
                  {(serial.config?.actions || []).length} actions
                </div>
              </div>
            );
          })}
        </div>
      )}
    </ComponentCard>
  );
}
