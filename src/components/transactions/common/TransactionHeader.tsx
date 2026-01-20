import React, { useState, useEffect } from 'react';
import { useWCAPI } from '../../../hooks/useWCAPI';

export interface TransactionHeaderProps {
  model: string;
  transactionId?: number;
  onChange: (field: string, value: any) => void;
  data: {
    id?: number;
    uuid?: string;
    ida?: string;
    proposal_no?: string;
    order_no?: string;
    invoice_no?: string;
    payment_no?: string;
    status: string;
    customer_id: number;
    vendor_id: number;
    manufacturer_id: number;
    priority?: string;
    price_level?: string;
    dt_created?: string;
    dt_modified?: string;
    dt_deadline?: string;
    dt_shipped?: string;
    // JSON fields
    cost?: any;
    sell?: any;
    finance?: any;
    flow?: any;
    source?: any;
    action?: any;
  };
}

const STATUS_CHOICES = {
  planned: 'Planned',
  released: 'Released',
  in_progress: 'In Progress',
  hold: 'Hold',
  complete: 'Complete',
  canceled: 'Canceled',
  sent: 'Sent',
  accepted: 'Accepted',
  rejected: 'Rejected',
  confirmed: 'Confirmed',
  fulfilled: 'Fulfilled',
  paid: 'Paid',
  overdue: 'Overdue',
  pending: 'Pending',
  processing: 'Processing',
  failed: 'Failed',
  refunded: 'Refunded',
  expired: 'Expired',
  active: 'Active',
};

export const TransactionHeader: React.FC<TransactionHeaderProps> = ({
  model,
  transactionId,
  onChange,
  data,
}) => {
  const { get } = useWCAPI();
  const [customers, setCustomers] = useState<any[]>([]);
  const [vendors, setVendors] = useState<any[]>([]);
  const [manufacturers, setManufacturers] = useState<any[]>([]);

  useEffect(() => {
    // Load contacts for dropdowns
    const loadContacts = async () => {
      const [custRes, vendRes, manufRes] = await Promise.all([
        get('contact', { is_customer: true, limit: 100 }),
        get('contact', { is_vendor: true, limit: 100 }),
        get('contact', { is_manufacturer: true, limit: 100 }),
      ]);

      if (custRes?.results) setCustomers(custRes.results);
      if (vendRes?.results) setVendors(vendRes.results);
      if (manufRes?.results) setManufacturers(manufRes.results);
    };

    loadContacts();
  }, [get]);

  const handleFieldChange = (field: string, value: any) => {
    onChange(field, value);
  };

  const getNumberField = () => {
    switch (model) {
      case 'proposal': return 'proposal_no';
      case 'sales_order': return 'order_no';
      case 'invoice': return 'invoice_no';
      case 'payment': return 'payment_no';
      default: return 'ida';
    }
  };

  const numberField = getNumberField();

  return (
    <div className="transaction-header bg-white p-6 rounded-lg shadow-sm border">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* ID and Number */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">ID</label>
          <input
            type="text"
            value={data.id || ''}
            disabled
            className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
          />
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            {numberField.replace('_', ' ').toUpperCase()}
          </label>
          <input
            type="text"
            value={data[numberField] || data.ida || ''}
            onChange={(e) => handleFieldChange(numberField, e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Status */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Status</label>
          <select
            value={data.status}
            onChange={(e) => handleFieldChange('status', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            {Object.entries(STATUS_CHOICES).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        {/* Priority */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Priority</label>
          <select
            value={data.priority || ''}
            onChange={(e) => handleFieldChange('priority', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">Normal</option>
            <option value="low">Low</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
        {/* Customer */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Customer</label>
          <select
            value={data.customer_id}
            onChange={(e) => handleFieldChange('customer_id', parseInt(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value={0}>Select Customer</option>
            {customers.map((customer) => (
              <option key={customer.id} value={customer.id}>
                {customer.name}
              </option>
            ))}
          </select>
        </div>

        {/* Vendor */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Vendor</label>
          <select
            value={data.vendor_id}
            onChange={(e) => handleFieldChange('vendor_id', parseInt(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value={0}>Select Vendor</option>
            {vendors.map((vendor) => (
              <option key={vendor.id} value={vendor.id}>
                {vendor.name}
              </option>
            ))}
          </select>
        </div>

        {/* Manufacturer */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Manufacturer</label>
          <select
            value={data.manufacturer_id}
            onChange={(e) => handleFieldChange('manufacturer_id', parseInt(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value={0}>Select Manufacturer</option>
            {manufacturers.map((manufacturer) => (
              <option key={manufacturer.id} value={manufacturer.id}>
                {manufacturer.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Dates */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-4">
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Created</label>
          <input
            type="datetime-local"
            value={data.dt_created ? new Date(data.dt_created).toISOString().slice(0, 16) : ''}
            disabled
            className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
          />
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Modified</label>
          <input
            type="datetime-local"
            value={data.dt_modified ? new Date(data.dt_modified).toISOString().slice(0, 16) : ''}
            disabled
            className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
          />
        </div>

        {(model === 'invoice' || model === 'payment') && (
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">Due Date</label>
            <input
              type="date"
              value={data.dt_deadline ? data.dt_deadline.split('T')[0] : ''}
              onChange={(e) => handleFieldChange('dt_deadline', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        )}

        {model === 'sales_order' && (
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">Ship Date</label>
            <input
              type="date"
              value={data.dt_shipped ? data.dt_shipped.split('T')[0] : ''}
              onChange={(e) => handleFieldChange('dt_shipped', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        )}
      </div>
    </div>
  );
};