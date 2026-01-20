import { useState } from "react";
import { FaSave, FaTimes } from "react-icons/fa";

interface SalesOrderLine {
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
}

interface SalesOrderLineFormProps {
  line?: SalesOrderLine;
  onSave: (line: SalesOrderLine) => void;
  onCancel: () => void;
  onChange?: (line: SalesOrderLine) => void;
}

export default function SalesOrderLineForm({ line, onSave, onCancel, onChange }: SalesOrderLineFormProps) {
  const [formData, setFormData] = useState<SalesOrderLine>({
    description: '',
    quantity: 1,
    price: { sell: 0, cost: 0 },
    discount_amount: 0,
    ...line
  });

  const updateFormData = (updates: Partial<SalesOrderLine>) => {
    const newData = { ...formData, ...updates };
    setFormData(newData);
    if (onChange) {
      onChange(newData);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  const calculateTotal = () => {
    return (formData.quantity * formData.price.sell) - formData.discount_amount;
  };

  return (
    <tr className="bg-blue-50 dark:bg-blue-900">
      <td className="border border-gray-300 dark:border-gray-600 px-3 py-2" colSpan={2}>
        <div className="space-y-2">
          <input
            type="text"
            value={formData.item_name || ''}
            onChange={(e) => updateFormData({ item_name: e.target.value })}
            className="w-full px-2 py-1 border rounded dark:bg-gray-700 dark:text-white"
            placeholder="Item Name (optional)"
          />
          <input
            type="text"
            value={formData.description}
            onChange={(e) => updateFormData({ description: e.target.value })}
            className="w-full px-2 py-1 border rounded dark:bg-gray-700 dark:text-white"
            placeholder="Description"
            required
          />
        </div>
      </td>
      <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">
        <input
          type="number"
          value={formData.quantity}
          onChange={(e) => updateFormData({ quantity: Number(e.target.value) })}
          className="w-full px-2 py-1 border rounded text-right dark:bg-gray-700 dark:text-white"
          min="0"
          step="0.01"
          required
        />
      </td>
      <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">
        <input
          type="number"
          value={formData.price.sell}
          onChange={(e) => updateFormData({ price: { ...formData.price, sell: Number(e.target.value) } })}
          className="w-full px-2 py-1 border rounded text-right dark:bg-gray-700 dark:text-white"
          min="0"
          step="0.01"
          required
        />
      </td>
      <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">
        <input
          type="number"
          value={formData.price.cost}
          onChange={(e) => updateFormData({ price: { ...formData.price, cost: Number(e.target.value) } })}
          className="w-full px-2 py-1 border rounded text-right dark:bg-gray-700 dark:text-white"
          min="0"
          step="0.01"
        />
      </td>
      <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">
        <input
          type="number"
          value={formData.discount_amount}
          onChange={(e) => updateFormData({ discount_amount: Number(e.target.value) })}
          className="w-full px-2 py-1 border rounded text-right dark:bg-gray-700 dark:text-white"
          min="0"
          step="0.01"
        />
      </td>
      <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-right font-medium">
        ${calculateTotal().toFixed(2)}
      </td>
      <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-center">
        <div className="flex gap-1 justify-center">
          <button type="button" onClick={handleSubmit} className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded">
            <FaSave className="text-green-600 text-xs" />
          </button>
          <button type="button" onClick={onCancel} className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded">
            <FaTimes className="text-red-600 text-xs" />
          </button>
        </div>
      </td>
    </tr>
  );
}
