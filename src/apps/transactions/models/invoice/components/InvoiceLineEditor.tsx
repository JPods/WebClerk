import { FaPlus, FaEdit, FaTrash } from "react-icons/fa";
import InvoiceLineForm from "./InvoiceLineForm";
import type { InvoiceLine } from "../types/invoiceLineType";

interface InvoiceLineEditorProps {
  lines: InvoiceLine[];
  editingId: number | null;
  newLine: InvoiceLine;
  onAdd: () => void;
  onEdit: (line: InvoiceLine) => void;
  onDelete: (id: number) => void;
  onSave: (line: InvoiceLine) => void;
  onCancel: () => void;
  onNewLineChange: (line: InvoiceLine) => void;
}

export default function InvoiceLineEditor({
  lines,
  editingId,
  newLine,
  onAdd,
  onEdit,
  onDelete,
  onSave,
  onCancel,
  onNewLineChange,
}: InvoiceLineEditorProps) {
  const handleNewLineSave = (line: InvoiceLine) => {
    onSave(line);
  };

  const handleEditSave = (line: InvoiceLine) => {
    onSave(line);
  };

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
                <th
                  className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-left"
                  colSpan={2}
                >
                  Product & Description
                </th>
                <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">
                  Qty
                </th>
                <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">
                  Sell Price
                </th>
                <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">
                  Cost Price
                </th>
                <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">
                  Discount
                </th>
                <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">
                  Total
                </th>
                <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-center">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {lines.map((item, index) => (
                <tr
                  key={item.id || index}
                  className="hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">
                    <div className="font-medium dark:text-white">
                      {item.item_name || "Manual Entry"}
                    </div>
                  </td>
                  <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">
                    {item.description || ""}
                  </td>
                  <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">
                    {item.quantity || 0}
                  </td>
                  <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">
                    $
                    {item.price?.sell
                      ? Number(item.price.sell).toFixed(2)
                      : "0.00"}
                  </td>
                  <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">
                    $
                    {item.price?.cost
                      ? Number(item.price.cost).toFixed(2)
                      : "0.00"}
                  </td>
                  <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right">
                    $
                    {item.discount_amount
                      ? Number(item.discount_amount).toFixed(2)
                      : "0.00"}
                  </td>
                  <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right font-medium">
                    $
                    {item.extended_price
                      ? Number(item.extended_price).toFixed(2)
                      : "0.00"}
                  </td>
                  <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-center">
                    <div className="flex gap-1 justify-center">
                      <button
                        type="button"
                        onClick={() => onEdit(item)}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                      >
                        <FaEdit className="text-blue-600 text-xs" />
                      </button>
                      <button
                        type="button"
                        onClick={() => onDelete(item.id!)}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                      >
                        <FaTrash className="text-red-600 text-xs" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {editingId === -1 && (
                <InvoiceLineForm
                  line={newLine}
                  onSave={handleNewLineSave}
                  onCancel={onCancel}
                  onChange={onNewLineChange}
                />
              )}
              {editingId && editingId > 0 && (
                <InvoiceLineForm
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
              <span>
                $
                {lines
                  .reduce((sum, item) => sum + (item.extended_price || 0), 0)
                  .toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between text-green-600 dark:text-green-400">
              <span>Margin:</span>
              <span>
                $
                {lines
                  .reduce((sum, item) => sum + (item.line_margin || 0), 0)
                  .toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between font-semibold text-lg border-t pt-2">
              <span>Total:</span>
              <span>
                $
                {lines
                  .reduce((sum, item) => sum + (item.extended_price || 0), 0)
                  .toFixed(2)}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
