/**
 * FlightSimCard — dd-card component with flight simulator launcher.
 *
 * Shows a select list of available simulations. Selecting one navigates
 * to the flight simulator with that simulation pre-loaded.
 *
 * Add to any form layout via layout.card:
 *   "flight_sim": { "title": "Flight Simulator", "component": "flight_sim", "fields": [] }
 *
 * Registered in cardRegistry as 'flight_sim'.
 */
import React from 'react';
import { useNavigate } from 'react-router';
import { registerCardComponent } from './cardRegistry';
import type { CardComponentProps } from './cardRegistry';
import './FlightSimCard.css';

const SIMULATIONS = [
  // Phase 1: Foundation
  { id: 'first-customer', label: '1. Your First Customer', description: 'Contact → Customer Org → Credit limit' },
  { id: 'first-item', label: '2. Your First Item', description: 'Item → Price/Cost → GL accounts → Opening inventory' },
  { id: 'first-sale', label: '3. Your First Sale', description: 'Proposal → Convert to Order — watch on_p and on_so change' },
  // Phase 2+
  { id: 'inventory', label: '4. Transaction Lifecycle', description: 'Proposal → Order → Invoice → Payment — watch inventory and GL change' },
  { id: 'gl-audit', label: 'GL Audit Trail', description: 'How every event creates balanced journal entries' },
  { id: 'cash', label: 'Cash Flow', description: 'Cash vs profit — from payment through bank reconciliation' },
  { id: 'payment', label: 'Payment Lifecycle', description: 'Order → Invoice → Payment → Apply → Journal — watch available, ledger, and GL' },
  { id: 'bom', label: 'Bill of Materials', description: 'BOM explosion, component availability, cost rollup' },
  { id: 'p2p', label: 'Purchase-to-Pay', description: 'Requisition through three-way match and payment' },
  { id: 'commissions', label: 'Commissions', description: 'Accrual, splits, overrides, adjustments' },
  { id: 'currency', label: 'Currency Variations', description: 'Multi-currency, FX gains/losses, revaluation' },
  { id: 'costing', label: 'Costing Methods', description: 'FIFO vs LIFO vs weighted average — same transactions, different numbers' },
];

const FlightSimCard: React.FC<CardComponentProps> = ({ data }) => {
  const navigate = useNavigate();

  const handleSelect = (simId: string) => {
    const itemId = data?.id || data?.item_id;
    const path = itemId
      ? `/flight-sim/${simId}?item=${itemId}`
      : `/flight-sim/${simId}`;
    navigate(path);
  };

  return (
    <div className="dd-card-flight-sim">
      {SIMULATIONS.map((sim) => (
        <button
          key={sim.id}
          className="fs-sim-btn"
          onClick={() => handleSelect(sim.id)}
        >
          <span className="fs-sim-label">{sim.label}</span>
          <span className="fs-sim-desc">{sim.description}</span>
        </button>
      ))}
    </div>
  );
};

registerCardComponent('flight_sim', FlightSimCard);
export default FlightSimCard;
