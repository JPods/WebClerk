import React from 'react';
import { useParams } from 'react-router-dom';

const InvoiceDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  return (
    <div className="p-4 space-y-4">
      <nav className="text-sm text-gray-500">Home / Transactions / Invoices / {id}</nav>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-4">
          <div className="card p-4 border rounded">Customer Search (placeholder)</div>
          <div className="card p-4 border rounded">Invoice Form (placeholder)</div>
          <div className="card p-4 border rounded">Invoice Totals (placeholder)</div>
        </div>
        <div className="space-y-4">
          <div className="card p-4 border rounded">Product Tree (placeholder)</div>
          <div className="card p-4 border rounded">Items List (placeholder)</div>
          <div className="card p-4 border rounded">Invoice Lines (placeholder)</div>
          <div className="card p-4 border rounded">QA List & Form (placeholder)</div>
        </div>
      </div>
    </div>
  );
};

export default InvoiceDetailPage;
