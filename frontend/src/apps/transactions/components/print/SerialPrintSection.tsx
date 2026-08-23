/**
 * SerialPrintSection — Renders serial numbers for a line item on printed documents.
 *
 * Used by Invoice, Purchase Order, Receipt, and Packing Slip print documents.
 * Shows serial numbers in a compact grid under the line item.
 * Context-aware: shows warranty on invoices, cost on purchases.
 */
import type { PrintSerial } from './printTypes';

interface SerialPrintSectionProps {
  serials: PrintSerial[];
  context: 'invoice' | 'purchase' | 'receipt' | 'packing_slip';
  /** Compact mode: just serial numbers in a comma list */
  compact?: boolean;
}

export default function SerialPrintSection({
  serials,
  context,
  compact = false,
}: SerialPrintSectionProps) {
  if (!serials || serials.length === 0) return null;

  // Compact mode — comma-separated list
  if (compact) {
    return (
      <div className="text-xs text-slate-600 mt-0.5 pl-4 print:text-[7pt]">
        <span className="font-medium">S/N: </span>
        {serials.map((s) => s.serialIda).join(', ')}
      </div>
    );
  }

  // Full mode — table under the line item
  const showModel = serials.some((s) => s.modelIda);
  const showWarranty = context === 'invoice' && serials.some((s) => s.warranty);
  const showCost = context === 'purchase' && serials.some((s) => s.cost);

  return (
    <div className="ml-4 mt-1 mb-2 print:ml-2">
      <table className="w-full text-xs print:text-[7pt] border-collapse">
        <thead>
          <tr className="text-left text-slate-500 border-b border-slate-200">
            <th className="py-0.5 pr-3 font-medium">Serial Number</th>
            {showModel && (
              <th className="py-0.5 pr-3 font-medium">Model</th>
            )}
            {showWarranty && (
              <th className="py-0.5 pr-3 font-medium">Warranty</th>
            )}
            {showCost && (
              <th className="py-0.5 pr-3 font-medium text-right">Cost</th>
            )}
          </tr>
        </thead>
        <tbody>
          {serials.map((serial, idx) => (
            <tr
              key={idx}
              className="border-b border-slate-100 last:border-b-0"
            >
              <td className="py-0.5 pr-3 font-mono text-slate-800">
                {serial.serialIda}
              </td>
              {showModel && (
                <td className="py-0.5 pr-3 text-slate-600">
                  {serial.modelIda || ''}
                </td>
              )}
              {showWarranty && (
                <td className="py-0.5 pr-3 text-slate-600">
                  {serial.warranty || ''}
                </td>
              )}
              {showCost && (
                <td className="py-0.5 pr-3 text-right text-slate-600">
                  {serial.cost != null
                    ? `$${serial.cost.toFixed(2)}`
                    : ''}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="text-[6pt] text-slate-400 mt-0.5">
        {serials.length} serial{serials.length !== 1 ? 's' : ''}
      </div>
    </div>
  );
}
