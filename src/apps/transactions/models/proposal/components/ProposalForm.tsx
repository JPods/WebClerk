import React, { useState, useEffect } from 'react';
import { useWCAPI } from '../hooks/useWCAPI';
import { useRealTimeCalculations } from '../hooks/useRealTimeCalculations';
import { useAuditTrail } from '../hooks/useAuditTrail';
import { TransactionHeader } from '../common/TransactionHeader';
import { TransactionTotals } from '../common/TransactionTotals';
import { AuditTrail } from '../common/AuditTrail';
import { TransactionLine } from '../hooks/useRealTimeCalculations';

export interface ProposalFormProps {
  proposalId?: number;
  onSave?: (proposal: any) => void;
  onCancel?: () => void;
}

export const ProposalForm: React.FC<ProposalFormProps> = ({
  proposalId,
  onSave,
  onCancel,
}) => {
  const { get, create, update } = useWCAPI();
  const [loading, setLoading] = useState(false);
  const [proposal, setProposal] = useState({
    id: proposalId || 0,
    uuid: '',
    ida: '',
    proposal_no: '',
    status: 'planned',
    customer_id: 0,
    vendor_id: 0,
    manufacturer_id: 0,
    priority: '',
    price_level: '',
    dt_created: '',
    dt_modified: '',
    cost: {},
    sell: {},
    finance: {},
    flow: {},
    source: {},
    action: {},
  });

  const [lines, setLines] = useState<TransactionLine[]>([]);
  const totals = useRealTimeCalculations(lines, 0.08, 0, 0); // 8% tax rate
  const { addEntry } = useAuditTrail(proposalId || 0, 'proposal');

  useEffect(() => {
    if (proposalId) {
      loadProposal();
    } else {
      // Initialize new proposal
      setProposal(prev => ({
        ...prev,
        dt_created: new Date().toISOString(),
        dt_modified: new Date().toISOString(),
      }));
    }
  }, [proposalId]);

  const loadProposal = async () => {
    setLoading(true);
    try {
      const [proposalRes, linesRes] = await Promise.all([
        get('proposal', { id: proposalId }),
        get('proposal_line', { parent: proposalId }),
      ]);

      if (proposalRes?.record) {
        setProposal(proposalRes.record);
      }

      if (linesRes?.results) {
        setLines(linesRes.results);
      }
    } catch (error) {
      console.error('Failed to load proposal:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleHeaderChange = (field: string, value: any) => {
    setProposal(prev => ({
      ...prev,
      [field]: value,
      dt_modified: new Date().toISOString(),
    }));
  };

  const handleLineChange = (index: number, field: string, value: any) => {
    setLines(prev => prev.map((line, i) =>
      i === index ? { ...line, [field]: value } : line
    ));
  };

  const addLine = () => {
    setLines(prev => [...prev, {
      quantity: 1,
      price: 0,
      discount_amount: 0,
      extended_price: 0,
      item_name: '',
      unit_cost: 0,
      line_margin: 0,
    }]);
  };

  const removeLine = (index: number) => {
    setLines(prev => prev.filter((_, i) => i !== index));
  };

  const prepareLinePayload = (line: TransactionLine): Record<string, unknown> => {
    const rawPrice = (line as unknown as { price?: unknown }).price;
    const resolveNumeric = (value: unknown) => (typeof value === "number" && Number.isFinite(value) ? value : 0);

    let numericPrice = resolveNumeric(rawPrice);
    if (typeof rawPrice !== "number") {
      if (rawPrice && typeof rawPrice === "object" && !Array.isArray(rawPrice) && "base" in rawPrice) {
        numericPrice = resolveNumeric((rawPrice as Record<string, unknown>).base);
      } else {
        numericPrice = resolveNumeric((line as unknown as Record<string, unknown>).unit_price);
      }
    }

    const pricePayload =
      rawPrice && typeof rawPrice === "object" && rawPrice !== null && !Array.isArray(rawPrice)
        ? { ...(rawPrice as Record<string, unknown>), base: numericPrice }
        : { base: numericPrice };

    return {
      ...line,
      price: pricePayload,
      unit_price: numericPrice,
    };
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      let savedProposal;
      if (proposalId) {
        const response = await update('proposal', proposalId, proposal);
        savedProposal = response?.record;
        await addEntry('updated', { status: proposal.status });
      } else {
        const response = await create('proposal', proposal);
        savedProposal = response?.record;
        await addEntry('created', { status: proposal.status });
      }

      if (savedProposal) {
        // Save lines
        for (const line of lines) {
          const linePayload = { ...prepareLinePayload(line), parent: savedProposal.id };
          if (line.id) {
            await update('proposal_line', line.id, linePayload);
          } else {
            await create('proposal_line', linePayload);
          }
        }

        onSave?.(savedProposal);
      }
    } catch (error) {
      console.error('Failed to save proposal:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleConvertToOrder = async () => {
    if (!proposalId) return;

    try {
      const response = await fetch(`/api/transactions/proposals/${proposalId}/convert_to_order/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (response.ok) {
        const data = await response.json();
        await addEntry('converted', { order_id: data.order_id });
        alert(`Proposal converted to order #${data.order_id}`);
        onSave?.(proposal);
      }
    } catch (error) {
      console.error('Failed to convert proposal:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2">Loading proposal...</span>
      </div>
    );
  }

  return (
    <div className="proposal-form max-w-6xl mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-800">
          {proposalId ? `Edit Proposal #${proposal.proposal_no}` : 'New Proposal'}
        </h1>
        <div className="space-x-2">
          {proposalId && proposal.status === 'accepted' && (
            <button
              onClick={handleConvertToOrder}
              className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
            >
              Convert to Order
            </button>
          )}
          <button
            onClick={handleSave}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Saving...' : 'Save'}
          </button>
          <button
            onClick={onCancel}
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            Cancel
          </button>
        </div>
      </div>

      <TransactionHeader
        model="proposal"
        transactionId={proposalId}
        data={proposal}
        onChange={handleHeaderChange}
      />

      {/* Lines Section */}
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-800">Line Items</h2>
          <button
            onClick={addLine}
            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
          >
            Add Line
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full table-auto">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left">Item</th>
                <th className="px-4 py-2 text-left">Description</th>
                <th className="px-4 py-2 text-right">Quantity</th>
                <th className="px-4 py-2 text-right">Price</th>
                <th className="px-4 py-2 text-right">Discount</th>
                <th className="px-4 py-2 text-right">Extended</th>
                <th className="px-4 py-2 text-center">Actions</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line, index) => (
                <tr key={index} className="border-t">
                  <td className="px-4 py-2">
                    <input
                      type="text"
                      value={line.item_name || ''}
                      onChange={(e) => handleLineChange(index, 'item_name', e.target.value)}
                      className="w-full px-2 py-1 border rounded"
                      placeholder="Item name"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="text"
                      value={line.description || ''}
                      onChange={(e) => handleLineChange(index, 'description', e.target.value)}
                      className="w-full px-2 py-1 border rounded"
                      placeholder="Description"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      value={line.quantity}
                      onChange={(e) => handleLineChange(index, 'quantity', parseFloat(e.target.value) || 0)}
                      className="w-20 px-2 py-1 border rounded text-right"
                      min="0"
                      step="0.01"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      value={line.price}
                      onChange={(e) => handleLineChange(index, 'price', parseFloat(e.target.value) || 0)}
                      className="w-24 px-2 py-1 border rounded text-right"
                      min="0"
                      step="0.01"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      value={line.discount_amount || 0}
                      onChange={(e) => handleLineChange(index, 'discount_amount', parseFloat(e.target.value) || 0)}
                      className="w-24 px-2 py-1 border rounded text-right"
                      min="0"
                      step="0.01"
                    />
                  </td>
                  <td className="px-4 py-2 text-right font-medium">
                    ${(line.quantity * line.price - (line.discount_amount || 0)).toFixed(2)}
                  </td>
                  <td className="px-4 py-2 text-center">
                    <button
                      onClick={() => removeLine(index)}
                      className="px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <TransactionTotals totals={totals} />

      {proposalId && (
        <AuditTrail
          transactionId={proposalId}
          model="proposal"
          className="mt-6"
        />
      )}
    </div>
  );
};