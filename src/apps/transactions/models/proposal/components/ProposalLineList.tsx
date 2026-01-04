import { FaPlus, FaEdit, FaTrash } from "react-icons/fa";
import { formatNumberValue, formatQuantityValue } from "../../common/numberFormat";
import ProposalLineForm from "./ProposalLineForm";

interface ProposalLine {
  id?: number;
  item_id?: number;
  item_name?: string;
  description: string;
  quantity: number;
  price: {
    sell: number;
    cost: number;
  };
  discount_amount: number;
  extended_price?: number;
  line_margin?: number;
}

interface ProposalLineListProps {
  lines: ProposalLine[];
  editingId: number | null;
  newLine: ProposalLine;
  onAdd: () => void;
  onEdit: (line: ProposalLine) => void;
  onDelete: (id: number) => void;
  onSave: (line: ProposalLine) => void;
  onCancel: () => void;
  onNewLineChange: (line: ProposalLine) => void;
}

export default function ProposalLineList({
  lines,
  editingId,
  newLine,
  onAdd,
  onEdit,
  onDelete,
  onSave,
  onCancel,
  onNewLineChange
}: ProposalLineListProps) {
  const handleNewLineSave = (line: ProposalLine) => {
    onSave(line);
  };

  const handleEditSave = (line: ProposalLine) => {
    onSave(line);
  };

  const extendedTotal = lines.reduce((sum, item) => sum + (item.extended_price || 0), 0);
  const marginTotal = lines.reduce((sum, item) => sum + (item.line_margin || 0), 0);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold dark:text-white">Line Items</h3>
        <button
          type="button"
          onClick={onAdd}
          className="flex items-center gap-2 px-3 py-1 text-white bg-green-500 rounded-md hover:bg-green-600 text-sm"
        >
          <FaPlus className="text-xs" />
          Add Item
        </button>
      </div>

      {lines.length === 0 && editingId !== -1 ? (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          No line items added yet. Click "Add Item" to get started.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse border border-gray-300 dark:border-gray-600 text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-left" colSpan={2}>Product & Description</th>
                <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">Qty</th>
                <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">Sell Price</th>
                <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">Cost Price</th>
                <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">Discount</th>
                <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">Total</th>
                <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-center">Actions</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((item, index) => (
                <tr key={item.id || index} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">
                    <div className="font-medium dark:text-white">{item.item_name || 'Manual Entry'}</div>
                  </td>
                  <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">{item.description || ''}</td>
                  <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">{formatQuantityValue(item.quantity ?? 0)}</td>
                  <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">${formatNumberValue(item.price?.sell ?? 0)}</td>
                  <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">${formatNumberValue(item.price?.cost ?? 0)}</td>
                  <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">${formatNumberValue(item.discount_amount ?? 0)}</td>
                  <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right font-medium">${formatNumberValue(item.extended_price ?? 0)}</td>
                  <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-center">
                    <div className="flex gap-1 justify-center">
                      <button type="button" onClick={() => onEdit(item)} className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded">
                        <FaEdit className="text-blue-600 text-xs" />
                      </button>
                      <button type="button" onClick={() => onDelete(item.id!)} className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded">
                        <FaTrash className="text-red-600 text-xs" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {editingId === -1 && (
                <ProposalLineForm
                  line={newLine}
                  onSave={handleNewLineSave}
                  onCancel={onCancel}
                  onChange={onNewLineChange}
                />
              )}
              {editingId && editingId > 0 && (
                <ProposalLineForm
                  line={newLine}
                  onSave={handleEditSave}
                  onCancel={onCancel}
                  onChange={onNewLineChange}
                />
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Totals Summary */}
      {lines.length > 0 && (
        <div className="flex justify-end">
          <div className="w-64 space-y-2">
            <div className="flex justify-between">
              <span>Subtotal:</span>
              <span>${formatNumberValue(extendedTotal)}</span>
            </div>
            <div className="flex justify-between text-green-600 dark:text-green-400">
              <span>Margin:</span>
              <span>${formatNumberValue(marginTotal)}</span>
            </div>
            <div className="flex justify-between font-semibold text-lg border-t pt-2">
              <span>Total:</span>
              <span>${formatNumberValue(extendedTotal)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}