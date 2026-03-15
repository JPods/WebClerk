/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect, useState } from "react";
import { getRecords } from "../../../../../api/wcapi";

interface Customer {
  id: number;
  name_first: string;
  name_last: string;
  email?: string;
  phone?: string;
}

interface CustomerSelectProps {
  value?: number;
  onChange: (customerId: number | undefined) => void;
  placeholder?: string;
  disabled?: boolean;
  contactType?: 'customer' | 'vendor' | 'contact';
}

export default function CustomerSelect({ value, onChange, placeholder, disabled = false, contactType = 'customer' }: CustomerSelectProps) {
  const defaultPlaceholder = contactType === 'vendor' ? 'Select vendor' : contactType === 'customer' ? 'Select customer' : 'Select contact';
  const finalPlaceholder = placeholder || defaultPlaceholder;
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const loadCustomers = async () => {
      try {
        setLoading(true);
        const response = await getRecords('contact', { limit: 100 });
        if (cancelled) {
          return;
        }
        const rawList = Array.isArray(response?.results)
          ? response.results
          : Array.isArray(response?.items)
          ? response.items
          : [];
        const customerData = rawList.map((c: any) => ({
          id: c.id,
          name_first: c.name_first || '',
          name_last: c.name_last || '',
          email: c.email,
          phone: c.phone,
        }));
        setCustomers(customerData);
      } catch (error) {
        if (!cancelled) {
          console.error('Failed to load customers:', error);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadCustomers();

    return () => {
      cancelled = true;
    };
  }, []);

  const filteredCustomers = customers.filter(customer =>
    `${customer.name_first} ${customer.name_last}`.toLowerCase().includes(searchTerm.toLowerCase()) ||
    customer.email?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const selectedCustomer = customers.find(c => c.id === value);

  const handleSelect = (customer: Customer) => {
    onChange(customer.id);
    setIsOpen(false);
    setSearchTerm("");
  };

  const handleClear = () => {
    onChange(undefined);
    setSearchTerm("");
  };

  return (
    <div className="relative">
      <div className="relative">
        <input
          type="text"
          value={selectedCustomer ? `${selectedCustomer.name_first} ${selectedCustomer.name_last}`.trim() : searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            if (!isOpen) setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onBlur={() => setTimeout(() => setIsOpen(false), 200)}
          placeholder={finalPlaceholder}
          disabled={disabled}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white dark:border-gray-600"
        />
        {selectedCustomer && !disabled && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-8 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            ×
          </button>
        )}
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          disabled={disabled}
          className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
        >
          ▼
        </button>
      </div>

      {isOpen && (
        <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto dark:bg-gray-800 dark:border-gray-600">
          {loading ? (
            <div className="px-3 py-2 text-gray-500 dark:text-gray-400">Loading customers...</div>
          ) : filteredCustomers.length === 0 ? (
            <div className="px-3 py-2 text-gray-500 dark:text-gray-400">No customers found</div>
          ) : (
            filteredCustomers.map((customer) => (
              <div
                key={customer.id}
                onClick={() => handleSelect(customer)}
                className="px-3 py-2 hover:bg-gray-100 cursor-pointer dark:hover:bg-gray-700"
              >
                <div className="font-medium dark:text-white">
                  {customer.name_first} {customer.name_last}
                </div>
                {customer.email && (
                  <div className="text-sm text-gray-500 dark:text-gray-400">{customer.email}</div>
                )}
                {customer.phone && (
                  <div className="text-sm text-gray-500 dark:text-gray-400">{customer.phone}</div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}