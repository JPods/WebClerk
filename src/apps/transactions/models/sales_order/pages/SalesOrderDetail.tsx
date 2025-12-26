import { useState, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { 
  Plus, 
  Trash2, 
  Printer, 
  Settings, 
  User, 
  Calendar,
  DollarSign,
  FileText,
  CheckCircle
} from 'lucide-react';

/**
 * @typedef {Object} LineItem
 * @property {string} id
 * @property {string} description
 * @property {number} quantity
 * @property {number} price
 */

const SalesOrderDetail = () => {
  const productCatalog = [
    { label: 'Web Development Services', price: 1200 },
    { label: 'UI/UX Design Consultation', price: 150 },
    { label: 'SEO Optimization Package', price: 300 },
    { label: 'Content Strategy Workshop', price: 450 },
    { label: 'Mobile App Prototype', price: 900 },
    { label: 'API Integration Support', price: 650 }
  ];

  // --- State ---
  const [invoiceNumber, setInvoiceNumber] = useState(`INV-${new Date().getFullYear()}-001`);
  const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().split('T')[0]);
  const [clientName, setClientName] = useState('');
  const [clientEmail, setClientEmail] = useState('');
  const [taxRate, setTaxRate] = useState(10);
  const [items, setItems] = useState([
    { id: crypto.randomUUID(), description: 'Web Development Services', quantity: 1, price: 1200 },
    { id: crypto.randomUUID(), description: 'UI/UX Design Consultation', quantity: 5, price: 150 }
  ]);
  const [descriptionSearch, setDescriptionSearch] = useState<Record<string, string>>({});
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const [dropdownAnchor, setDropdownAnchor] = useState<{ id: string; top: number; left: number; width: number } | null>(null);
  const [isSaved, setIsSaved] = useState(false);

  const normalize = (value: string) => value.toLowerCase().replace(/\s+/g, ' ').trim();
  const selectedLabels = useMemo(() => {
    const labels = items
      .map(i => normalize(i.description))
      .filter(Boolean);
    return new Set(labels);
  }, [items]);

  // --- Calculations ---
  const totals = useMemo(() => {
    const subtotal = items.reduce((acc, item) => acc + (item.quantity * item.price), 0);
    const taxAmount = (subtotal * taxRate) / 100;
    const total = subtotal + taxAmount;
    return { subtotal, taxAmount, total };
  }, [items, taxRate]);

  // --- Handlers ---
  const addItem = () => {
    const newItem = {
      id: crypto.randomUUID(),
      description: '',
      quantity: 1,
      price: 0
    };
    setItems([...items, newItem]);
  };

  const removeItem = (id: string) => {
    if (items.length > 1) {
      setItems(items.filter(item => item.id !== id));
    }
  };

  const updateItem = (id: string, field: string, value: string | number) => {
    setItems(items.map(item => {
      if (item.id === id) {
        return { ...item, [field]: value };
      }
      return item;
    }));
  };

  const handleSave = () => {
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 3000);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4 sm:px-6 lg:px-8 font-sans text-slate-900">
      <div className="max-w-5xl mx-auto">
        
        {/* Header Actions */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8 print:hidden">
          <div>
            <h1 className="text-3xl font-bold text-slate-800">Sales Invoice</h1>
            <p className="text-slate-500 mt-1">Create and manage your professional sales invoices.</p>
          </div>
          <div className="flex items-center gap-3">
            <button 
              onClick={handleSave}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium transition-all ${
                isSaved ? 'bg-green-100 text-green-700' : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 shadow-sm'
              }`}
            >
              {isSaved ? <CheckCircle size={18} /> : <FileText size={18} />}
              {isSaved ? 'Saved!' : 'Save Draft'}
            </button>
            <button 
              onClick={handlePrint}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-lg font-medium shadow-md shadow-indigo-200 transition-all active:scale-95"
            >
              <Printer size={18} />
              Print / PDF
            </button>
          </div>
        </div>

        {/* Main Invoice Card */}
        <div className="bg-white shadow-xl shadow-slate-200/60 rounded-2xl overflow-visible border border-slate-100 print:shadow-none print:border-none">
          
          {/* Invoice Visual Header */}
          <div className="bg-slate-900 p-8 md:p-12 text-white">
            <div className="flex flex-col md:flex-row justify-between gap-8">
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-indigo-500 rounded-xl flex items-center justify-center font-bold text-2xl shadow-lg shadow-indigo-500/20">
                    S
                  </div>
                  <div>
                    <h2 className="text-xl font-bold tracking-tight">SOLUTIONS LTD.</h2>
                    <p className="text-slate-400 text-sm">Fintech & Design Services</p>
                  </div>
                </div>
                <div className="text-slate-400 text-sm leading-relaxed max-w-xs">
                  123 Innovation Drive, Silicon Valley<br />
                  CA 94043, United States<br />
                  contact@solutions.io
                </div>
              </div>
              
              <div className="text-left md:text-right space-y-2">
                <h3 className="text-4xl font-extralight tracking-widest text-slate-300 uppercase">Invoice</h3>
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-slate-800 rounded-md text-slate-300 text-sm border border-slate-700">
                  <span className="font-semibold">{invoiceNumber}</span>
                </div>
                <div className="flex md:justify-end items-center gap-2 text-slate-400 text-sm mt-4">
                  <Calendar size={14} />
                  <span>Issued on {invoiceDate}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="p-8 md:p-12 space-y-12">
            
            {/* Client & Metadata Info */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 pb-8 border-b border-slate-100">
              <div className="space-y-4">
                <label className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
                  <User size={14} /> Bill To
                </label>
                <div className="space-y-3">
                  <input 
                    type="text" 
                    placeholder="Client Name"
                    className="w-full text-lg font-semibold bg-transparent border-b border-transparent hover:border-slate-200 focus:border-indigo-500 outline-none transition-colors"
                    value={clientName}
                    onChange={(e) => setClientName(e.target.value)}
                  />
                  <input 
                    type="email" 
                    placeholder="client@email.com"
                    className="w-full text-slate-500 bg-transparent border-b border-transparent hover:border-slate-200 focus:border-indigo-500 outline-none transition-colors"
                    value={clientEmail}
                    onChange={(e) => setClientEmail(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-4">
                <label className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
                  <Settings size={14} /> Invoice Details
                </label>
                <div className="space-y-2">
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-slate-500">Invoice #</span>
                    <input 
                      type="text" 
                      className="text-right font-medium text-slate-700 w-32 border-b border-transparent hover:border-slate-200 focus:border-indigo-500 outline-none"
                      value={invoiceNumber}
                      onChange={(e) => setInvoiceNumber(e.target.value)}
                    />
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-slate-500">Date</span>
                    <input 
                      type="date" 
                      className="text-right font-medium text-slate-700 border-b border-transparent hover:border-slate-200 focus:border-indigo-500 outline-none"
                      value={invoiceDate}
                      onChange={(e) => setInvoiceDate(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <label className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
                   Currency & Tax
                </label>
                <div className="space-y-2">
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-slate-500">Currency</span>
                    <span className="font-medium text-slate-700">USD ($)</span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-slate-500">Tax Rate (%)</span>
                    <input 
                      type="number" 
                      className="text-right font-medium text-slate-700 w-16 border-b border-transparent hover:border-slate-200 focus:border-indigo-500 outline-none"
                      value={taxRate}
                      onChange={(e) => setTaxRate(Number(e.target.value))}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Line Items Table */}
            <div className="overflow-x-auto overflow-y-visible">
              <table className="w-full text-left border-separate border-spacing-y-2">
                <thead>
                  <tr className="text-slate-400 text-xs font-bold uppercase tracking-widest">
                    <th className="pb-4 pl-2">Description</th>
                    <th className="pb-4 w-24 px-4 text-center">Qty</th>
                    <th className="pb-4 w-32 px-4 text-right">Price</th>
                    <th className="pb-4 w-32 px-4 text-right">Amount</th>
                    <th className="pb-4 w-12 print:hidden"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, index) => (
                    <tr key={item.id} className="group bg-white hover:bg-slate-50/50 transition-colors relative">
                      <td className="py-4 pl-2 border-b border-slate-100">
                        <div className="relative">
                          <input 
                            type="text" 
                            placeholder="Search or select service"
                            className="w-full bg-transparent font-medium text-slate-700 placeholder:text-slate-300 outline-none border-b border-transparent hover:border-slate-200 focus:border-indigo-500"
                            value={descriptionSearch[item.id] ?? item.description}
                            onFocus={(e) => {
                              const rect = e.currentTarget.getBoundingClientRect();
                              setOpenDropdown(item.id);
                              setDropdownAnchor({ id: item.id, top: rect.bottom, left: rect.left, width: rect.width });
                            }}
                            onChange={(e) => {
                              const value = e.target.value;
                              setDescriptionSearch(prev => ({ ...prev, [item.id]: value }));
                              updateItem(item.id, 'description', value);
                            }}
                            onBlur={() => setTimeout(() => {
                              setOpenDropdown(null);
                              setDropdownAnchor(null);
                            }, 100)}
                          />
                          {openDropdown === item.id && dropdownAnchor?.id === item.id && (() => {
                            const availableOptions = productCatalog.filter(option => {
                              const search = normalize(descriptionSearch[item.id] ?? '');
                              const optionKey = normalize(option.label);
                              const currentKey = normalize(item.description);
                              const matchesSearch = optionKey.includes(search);
                              const inUseElsewhere = selectedLabels.has(optionKey) && currentKey !== optionKey;
                              return matchesSearch && !inUseElsewhere;
                            });
                            return createPortal(
                              <div
                                className="fixed z-50 bg-white border border-slate-100 rounded-lg shadow-xl max-h-48 overflow-y-auto"
                                style={{ top: dropdownAnchor.top, left: dropdownAnchor.left, width: dropdownAnchor.width }}
                              >
                                {availableOptions.map(option => (
                                  <button
                                    key={option.label}
                                    type="button"
                                    className="w-full text-left px-3 py-2 hover:bg-indigo-50 text-slate-700"
                                    onMouseDown={() => {
                                      setDescriptionSearch(prev => ({ ...prev, [item.id]: option.label }));
                                      updateItem(item.id, 'description', option.label);
                                      updateItem(item.id, 'price', option.price);
                                      setOpenDropdown(null);
                                      setDropdownAnchor(null);
                                    }}
                                  >
                                    <div className="font-medium">{option.label}</div>
                                    <div className="text-xs text-slate-400">${option.price.toLocaleString()} base</div>
                                  </button>
                                ))}
                                {availableOptions.length === 0 && (
                                  <div className="px-3 py-2 text-sm text-slate-400">No matches</div>
                                )}
                              </div>,
                              document.body
                            );
                          })()}
                        </div>
                      </td>
                      <td className="py-4 px-4 border-b border-slate-100 text-center">
                        <input 
                          type="number" 
                          min="1"
                          className="w-full bg-transparent text-center font-medium text-slate-700 outline-none"
                          value={item.quantity}
                          onChange={(e) => updateItem(item.id, 'quantity', parseInt(e.target.value) || 0)}
                        />
                      </td>
                      <td className="py-4 px-4 border-b border-slate-100 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <span className="text-slate-400 text-sm">$</span>
                          <input 
                            type="number" 
                            className="w-24 bg-transparent text-right font-medium text-slate-700 outline-none"
                            value={item.price}
                            onChange={(e) => updateItem(item.id, 'price', parseFloat(e.target.value) || 0)}
                          />
                        </div>
                      </td>
                      <td className="py-4 px-4 border-b border-slate-100 text-right font-bold text-slate-700">
                        ${(item.quantity * item.price).toLocaleString()}
                      </td>
                      <td className="py-4 border-b border-slate-100 text-center print:hidden">
                        <button 
                          onClick={() => removeItem(item.id)}
                          disabled={items.length <= 1}
                          className="text-slate-300 hover:text-red-500 transition-colors disabled:opacity-0"
                        >
                          <Trash2 size={18} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Footer / Summary Area */}
            <div className="flex flex-col md:flex-row justify-between gap-12 pt-4">
              <div className="flex-1 space-y-6">
                <button 
                  onClick={addItem}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-indigo-600 font-semibold bg-indigo-50 hover:bg-indigo-100 transition-colors print:hidden"
                >
                  <Plus size={18} />
                  Add Line Item
                </button>
                
                <div className="bg-slate-50 rounded-xl p-6 space-y-3">
                  <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Notes & Terms</h4>
                  <textarea 
                    className="w-full bg-transparent text-sm text-slate-600 leading-relaxed min-h-[100px] outline-none border-none resize-none"
                    placeholder="Payment is due within 30 days. Please include the invoice number on your check or wire transfer."
                  />
                </div>
              </div>

              <div className="w-full md:w-80">
                <div className="bg-white border border-slate-100 rounded-xl p-6 shadow-sm space-y-4">
                  <div className="flex justify-between items-center text-slate-500">
                    <span className="text-sm font-medium">Subtotal</span>
                    <span className="font-semibold text-slate-700">${totals.subtotal.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between items-center text-slate-500">
                    <span className="text-sm font-medium">Tax ({taxRate}%)</span>
                    <span className="font-semibold text-slate-700">${totals.taxAmount.toLocaleString()}</span>
                  </div>
                  <div className="pt-4 border-t border-slate-100 flex justify-between items-center">
                    <span className="text-base font-bold text-slate-800">Grand Total</span>
                    <div className="text-right">
                      <span className="text-3xl font-black text-indigo-600">
                        ${totals.total.toLocaleString()}
                      </span>
                      <p className="text-[10px] text-slate-400 font-bold uppercase tracking-tighter mt-1">USD Currency</p>
                    </div>
                  </div>
                </div>
                
                <div className="mt-8 flex items-center gap-3 justify-center text-slate-400 border-2 border-dashed border-slate-100 rounded-xl p-6">
                  <DollarSign size={24} className="opacity-20" />
                  <p className="text-xs font-medium text-center">Please make all payments payable to <br/><span className="text-slate-500 font-bold italic">SOLUTIONS LTD.</span></p>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Help Footer */}
        <div className="mt-12 text-center text-slate-400 text-sm print:hidden">
          <p>Need help? Contact support at <a href="#" className="text-indigo-500 hover:underline">billing@solutions.io</a></p>
        </div>
      </div>

      <style>{`
        @media print {
          body { background: white; }
          .print\\:hidden { display: none !important; }
          @page { margin: 20mm; }
        }
      `}</style>
    </div>
  );
};

export default SalesOrderDetail;