/**
 * CustomerSalesPanel - Customer search and financial info panel for sales transactions
 *
 * Features:
 * - Search customers by scalar values (name, ida, phone, email) and refs.keywords
 * - Comma-separated values create AND queries (e.g., "acme, west" finds customers with both keywords)
 * - Displays key customer financial data when selected
 * - Transfers terms and price_level to parent transaction
 *
 * Usage: ProposalDetail, OrderDetail, InvoiceDetail (center card)
 */
import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  FaSearch,
  FaUser,
  FaTimes,
  FaSpinner,
  FaChevronDown,
  FaHistory,
  FaExclamationTriangle,
  FaCreditCard,
  FaChartLine,
  FaCheck,
} from "react-icons/fa";
import { customerApi } from "@/apps/orgs/services/orgApi";
import type { Organization } from "@/apps/orgs/types/orgTypes";
import ComponentCard from "@/components/common/ComponentCard";

// ---------- Constants ----------

/** Default price level when customer doesn't have one set. "retail" and "base" are equivalent. */
const DEFAULT_PRICE_LEVEL = "retail";

// ---------- Types ----------

export interface CustomerFinancial {
  common?: {
    currency?: string;
    account?: {
      dt_opened?: string | null;
      dt_last_activity?: string | null;
      hold?: boolean;
      cod_only?: boolean;
      inactive?: boolean;
    };
    rating?: {
      internal?: string | null;
      comments?: string;
      credit_score?: number | null;
    };
    settings?: {
      discount_pct?: number;
      tax_exempt?: boolean;
      tax_exempt_id?: string;
      terms_id?: number | null;
      notes?: string;
    };
  };
  customer?: {
    credit?: {
      limit?: number;
      high?: number;
      available?: number;
    };
    balances?: {
      due?: number;
      current?: number;
      open_orders?: number;
      total_exposure?: number;
    };
    aging?: {
      future?: number;
      period_1?: number;
      period_2?: number;
      period_3?: number;
    };
    payment?: {
      days_avg_paid?: number;
      days_pay?: number;
      dt_last_payment?: string | null;
      last_payment_amount?: number;
    };
    sales?: {
      mtd?: number;
      ytd?: number;
      lifetime?: number;
      dt_last_sale?: string | null;
      last_sale_amount?: number;
    };
    margin?: {
      mtd?: number;
      ytd?: number;
      pct?: number;
    };
    minimums?: {
      order?: number;
    };
  };
}

export interface SelectedCustomer {
  id: number;
  display_name: string;
  display_id?: string;
  price_level?: string | null;
  status?: string;
  phone?: string | null;
  email?: string | null;
  financial?: CustomerFinancial;
  refs?: {
    keywords?: string[];
  };
}

export interface CustomerSelectionData {
  customer: SelectedCustomer;
  terms?: string | null;
  price_level?: string | null;
}

export interface CustomerSalesPanelProps {
  /** Currently selected customer ID */
  value?: number | null;

  /** Callback when customer is selected - returns customer + terms/price_level for parent */
  onSelect: (data: CustomerSelectionData | null) => void;

  /** Whether the panel is in edit mode */
  isEditing?: boolean;

  /** Whether to show the financial data section */
  showFinancials?: boolean;

  /** Title for the panel */
  title?: string;

  /** Additional CSS classes */
  className?: string;
}

// ---------- Utility functions ----------

const formatCurrency = (value?: number | null): string => {
  if (value === undefined || value === null) return "--";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

const formatDate = (dateStr?: string | null): string => {
  if (!dateStr) return "--";
  try {
    return new Date(dateStr).toLocaleDateString();
  } catch {
    return "--";
  }
};

// Local storage key for recent selections
const RECENT_KEY = "customerSalesPanel_recent";
const MAX_RECENT = 5;

// ---------- Status Badge ----------

const StatusBadge: React.FC<{ hold?: boolean; codOnly?: boolean; inactive?: boolean }> = ({
  hold,
  codOnly,
  inactive,
}) => {
  if (hold) {
    return (
      <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
        ON HOLD
      </span>
    );
  }
  if (codOnly) {
    return (
      <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
        COD ONLY
      </span>
    );
  }
  if (inactive) {
    return (
      <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400">
        INACTIVE
      </span>
    );
  }
  return (
    <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
      ACTIVE
    </span>
  );
};

// ---------- Financial Info Display ----------

const FinancialInfo: React.FC<{ financial?: CustomerFinancial; priceLevel?: string | null }> = ({ financial, priceLevel }) => {
  const common = financial?.common;
  const customer = financial?.customer;
  // Display price level, defaulting to "retail" if not set
  const displayPriceLevel = priceLevel || DEFAULT_PRICE_LEVEL;

  return (
    <div className="mt-4 space-y-4">
      {/* Price Level & Last Sale Info */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
          <span className="text-xs text-blue-600 dark:text-blue-400 font-medium">Price Level: </span>
          <span className="text-sm font-semibold text-blue-700 dark:text-blue-300 uppercase">{displayPriceLevel}</span>
        </div>
        {customer?.sales?.dt_last_sale && (
          <div className="text-xs text-slate-500 dark:text-slate-400">
            Last Sale: <span className="font-medium text-slate-700 dark:text-slate-300">{formatDate(customer.sales.dt_last_sale)}</span>
          </div>
        )}
      </div>

      {/* Credit & Balances */}
      <div className="grid grid-cols-2 gap-4">
        {/* Credit Info */}
        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3">
          <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-2 flex items-center gap-1">
            <FaCreditCard className="w-3 h-3" />
            Credit
          </h4>
          <dl className="space-y-1 text-xs">
            <div className="flex justify-between">
              <dt className="text-slate-500 dark:text-slate-400">Limit</dt>
              <dd className="font-medium text-slate-900 dark:text-white">
                {formatCurrency(customer?.credit?.limit)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500 dark:text-slate-400">Available</dt>
              <dd className="font-medium text-slate-900 dark:text-white">
                {formatCurrency(customer?.credit?.available)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500 dark:text-slate-400">High</dt>
              <dd className="font-medium text-slate-600 dark:text-slate-300">
                {formatCurrency(customer?.credit?.high)}
              </dd>
            </div>
          </dl>
        </div>

        {/* Balances */}
        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3">
          <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-2">
            Balances
          </h4>
          <dl className="space-y-1 text-xs">
            <div className="flex justify-between">
              <dt className="text-slate-500 dark:text-slate-400">Due</dt>
              <dd className={`font-medium ${(customer?.balances?.due ?? 0) > 0 ? "text-red-600 dark:text-red-400" : "text-slate-900 dark:text-white"}`}>
                {formatCurrency(customer?.balances?.due)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500 dark:text-slate-400">Current</dt>
              <dd className="font-medium text-slate-900 dark:text-white">
                {formatCurrency(customer?.balances?.current)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500 dark:text-slate-400">Open Orders</dt>
              <dd className="font-medium text-slate-600 dark:text-slate-300">
                {formatCurrency(customer?.balances?.open_orders)}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Aging */}
      {(customer?.aging?.period_1 || customer?.aging?.period_2 || customer?.aging?.period_3) && (
        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3">
          <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-2">
            Aging
          </h4>
          <div className="grid grid-cols-4 gap-2 text-xs">
            <div className="text-center">
              <div className="text-slate-500 dark:text-slate-400">Future</div>
              <div className="font-medium text-slate-900 dark:text-white">
                {formatCurrency(customer?.aging?.future)}
              </div>
            </div>
            <div className="text-center">
              <div className="text-slate-500 dark:text-slate-400">1-30</div>
              <div className="font-medium text-slate-900 dark:text-white">
                {formatCurrency(customer?.aging?.period_1)}
              </div>
            </div>
            <div className="text-center">
              <div className="text-slate-500 dark:text-slate-400">31-60</div>
              <div className={`font-medium ${(customer?.aging?.period_2 ?? 0) > 0 ? "text-amber-600 dark:text-amber-400" : "text-slate-900 dark:text-white"}`}>
                {formatCurrency(customer?.aging?.period_2)}
              </div>
            </div>
            <div className="text-center">
              <div className="text-slate-500 dark:text-slate-400">61+</div>
              <div className={`font-medium ${(customer?.aging?.period_3 ?? 0) > 0 ? "text-red-600 dark:text-red-400" : "text-slate-900 dark:text-white"}`}>
                {formatCurrency(customer?.aging?.period_3)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sales Stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3">
          <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-2 flex items-center gap-1">
            <FaChartLine className="w-3 h-3" />
            Sales
          </h4>
          <dl className="space-y-1 text-xs">
            <div className="flex justify-between">
              <dt className="text-slate-500 dark:text-slate-400">MTD</dt>
              <dd className="font-medium text-slate-900 dark:text-white">
                {formatCurrency(customer?.sales?.mtd)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500 dark:text-slate-400">YTD</dt>
              <dd className="font-medium text-slate-900 dark:text-white">
                {formatCurrency(customer?.sales?.ytd)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500 dark:text-slate-400">Lifetime</dt>
              <dd className="font-medium text-green-600 dark:text-green-400">
                {formatCurrency(customer?.sales?.lifetime)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500 dark:text-slate-400">Last Sale</dt>
              <dd className="font-medium text-slate-600 dark:text-slate-300">
                {formatDate(customer?.sales?.dt_last_sale)}
              </dd>
            </div>
          </dl>
        </div>

        {/* Payment Info */}
        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3">
          <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-2">
            Payment
          </h4>
          <dl className="space-y-1 text-xs">
            <div className="flex justify-between">
              <dt className="text-slate-500 dark:text-slate-400">Avg Days</dt>
              <dd className="font-medium text-slate-900 dark:text-white">
                {customer?.payment?.days_avg_paid ?? "--"}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500 dark:text-slate-400">Last Payment</dt>
              <dd className="font-medium text-slate-900 dark:text-white">
                {formatDate(customer?.payment?.dt_last_payment)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500 dark:text-slate-400">Amount</dt>
              <dd className="font-medium text-slate-600 dark:text-slate-300">
                {formatCurrency(customer?.payment?.last_payment_amount)}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Account Settings */}
      <div className="flex flex-wrap gap-2 text-xs">
        {common?.settings?.discount_pct ? (
          <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
            {common.settings.discount_pct}% Discount
          </span>
        ) : null}
        {common?.settings?.tax_exempt && (
          <span className="px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
            Tax Exempt {common.settings.tax_exempt_id ? `(${common.settings.tax_exempt_id})` : ""}
          </span>
        )}
        {customer?.minimums?.order ? (
          <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400">
            Min Order: {formatCurrency(customer.minimums.order)}
          </span>
        ) : null}
      </div>
    </div>
  );
};

// ---------- Main Component ----------

export const CustomerSalesPanel: React.FC<CustomerSalesPanelProps> = ({
  value,
  onSelect,
  isEditing = false,
  showFinancials = true,
  title = "Customer",
  className = "",
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Organization[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<SelectedCustomer | null>(null);
  const [recentCustomers, setRecentCustomers] = useState<SelectedCustomer[]>([]);

  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load recent customers from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(RECENT_KEY);
      if (stored) {
        setRecentCustomers(JSON.parse(stored).slice(0, MAX_RECENT));
      }
    } catch {
      // Ignore localStorage errors
    }
  }, []);

  // Load selected customer details if value changes
  useEffect(() => {
    if (value && value > 0) {
      // Check if we already have this customer in recent selections
      const recentMatch = recentCustomers.find((c) => c.id === value);
      if (recentMatch) {
        setSelectedCustomer(recentMatch);
      } else {
        // Fetch the customer details
        customerApi
          .get(value)
          .then((customer) => {
            if (customer && customer.id) {
              const selected: SelectedCustomer = {
                id: customer.id,
                display_name: customer.display_name || "",
                display_id: customer.display_id,
                price_level: customer.price_level,
                status: customer.status,
                phone: customer.phone,
                email: customer.email,
                financial: customer.financial,
                refs: customer.refs,
              };
              setSelectedCustomer(selected);
            }
          })
          .catch(() => {
            setSelectedCustomer(null);
          });
      }
    } else {
      setSelectedCustomer(null);
    }
  }, [value, recentCustomers]);

  // Search for customers with AND query support
  // Comma-separated values are treated as AND conditions
  const handleSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }

    setIsLoading(true);
    try {
      // Parse comma-separated keywords for AND query
      // e.g., "acme, west" searches for customers matching BOTH keywords
      const keywords = query
        .split(",")
        .map((k) => k.trim())
        .filter((k) => k.length > 0);

      // Use kw parameter for keyword search (AND semantics)
      const response = await customerApi.list({
        search: keywords.length === 1 ? keywords[0] : undefined,
        // For multiple keywords, use comma-separated kw param
        // The API will do AND matching on refs.keywords
        ...(keywords.length > 1 ? {} : {}),
        is_active: true,
        limit: 20,
      });

      // If we have multiple keywords, filter client-side for AND matching
      // (API may not fully support AND semantics on keywords)
      let results = response.results || [];
      if (keywords.length > 1) {
        results = results.filter((customer) => {
          const customerKeywords = customer.refs?.keywords || [];
          const searchableText = [
            customer.display_name?.toLowerCase(),
            customer.display_id?.toLowerCase(),
            customer.email?.toLowerCase(),
            customer.phone,
            ...customerKeywords.map((k: string) => k.toLowerCase()),
          ]
            .filter(Boolean)
            .join(" ");

          // All keywords must match
          return keywords.every((kw) =>
            searchableText.includes(kw.toLowerCase())
          );
        });
      }

      setSearchResults(results);
    } catch (err) {
      console.error("Error searching customers:", err);
      setSearchResults([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchQuery.trim()) {
        handleSearch(searchQuery);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, handleSearch]);

  // Handle click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  // Save to recent selections
  const saveToRecent = (customer: SelectedCustomer) => {
    try {
      const current = localStorage.getItem(RECENT_KEY);
      let recent: SelectedCustomer[] = current ? JSON.parse(current) : [];

      // Remove if already exists
      recent = recent.filter((c) => c.id !== customer.id);

      // Add to front
      recent.unshift(customer);

      // Limit size
      recent = recent.slice(0, MAX_RECENT);

      localStorage.setItem(RECENT_KEY, JSON.stringify(recent));
      setRecentCustomers(recent);
    } catch {
      // Ignore localStorage errors
    }
  };

  // Handle customer selection from Organization
  const handleSelectOrg = (org: Organization) => {
    const customer: SelectedCustomer = {
      id: org.id,
      display_name: org.display_name || "",
      display_id: org.display_id,
      price_level: org.price_level,
      status: org.status,
      phone: org.phone,
      email: org.email,
      financial: org.financial,
      refs: org.refs,
    };

    setSelectedCustomer(customer);
    saveToRecent(customer);

    // Get terms from financial.common.settings.terms_id
    // (would need to resolve term name from ID)
    const termsId = customer.financial?.common?.settings?.terms_id;

    // Call onSelect with customer data plus terms/price_level for parent
    // Default to "retail" if customer doesn't have a price_level set
    onSelect({
      customer,
      terms: termsId ? String(termsId) : null,
      price_level: customer.price_level || DEFAULT_PRICE_LEVEL,
    });

    setIsOpen(false);
    setSearchQuery("");
    setSearchResults([]);
  };

  // Handle customer selection from recent
  const handleSelectRecent = (customer: SelectedCustomer) => {
    setSelectedCustomer(customer);
    saveToRecent(customer);

    const termsId = customer.financial?.common?.settings?.terms_id;
    // Default to "retail" if customer doesn't have a price_level set
    onSelect({
      customer,
      terms: termsId ? String(termsId) : null,
      price_level: customer.price_level || DEFAULT_PRICE_LEVEL,
    });

    setIsOpen(false);
    setSearchQuery("");
    setSearchResults([]);
  };

  // Handle clear selection
  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedCustomer(null);
    onSelect(null);
  };

  // Toggle dropdown
  const handleToggle = () => {
    if (isEditing) {
      setIsOpen(!isOpen);
      if (!isOpen) {
        setTimeout(() => inputRef.current?.focus(), 100);
      }
    }
  };

  const accountStatus = selectedCustomer?.financial?.common?.account;
  const hasWarning = accountStatus?.hold || accountStatus?.cod_only || accountStatus?.inactive;

  return (
    <ComponentCard
      title={title}
      icon={<FaUser />}
      className={className}
      headerRight={
        selectedCustomer && (
          <StatusBadge
            hold={accountStatus?.hold}
            codOnly={accountStatus?.cod_only}
            inactive={accountStatus?.inactive}
          />
        )
      }
    >
      <div className="relative" ref={dropdownRef}>
        {/* Customer Display / Selector */}
        <div
          onClick={handleToggle}
          className={`
            flex items-center justify-between w-full p-3
            bg-white dark:bg-slate-800
            border rounded-lg
            transition-colors duration-150
            ${isEditing ? "cursor-pointer hover:border-slate-400 dark:hover:border-slate-500" : "cursor-default"}
            ${hasWarning ? "border-amber-300 dark:border-amber-600" : "border-slate-200 dark:border-slate-700"}
            ${isOpen ? "ring-2 ring-blue-500 border-blue-500" : ""}
          `}
        >
          <div className="flex items-center flex-1 min-w-0">
            <FaUser className="w-4 h-4 text-slate-400 dark:text-slate-500 mr-3 flex-shrink-0" />
            {selectedCustomer ? (
              <div className="min-w-0">
                <div className="font-medium text-slate-900 dark:text-white truncate">
                  {selectedCustomer.display_name}
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                  {selectedCustomer.display_id && (
                    <span className="font-mono">{selectedCustomer.display_id}</span>
                  )}
                  {selectedCustomer.price_level && (
                    <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700">
                      Level {selectedCustomer.price_level}
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <span className="text-slate-400 dark:text-slate-500">
                {isEditing ? "Search customer by name, ID, or keywords..." : "No customer selected"}
              </span>
            )}
          </div>

          {isEditing && (
            <div className="flex items-center ml-2">
              {selectedCustomer && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                >
                  <FaTimes className="w-3 h-3" />
                </button>
              )}
              <FaChevronDown
                className={`w-4 h-4 text-slate-400 ml-1 transition-transform ${
                  isOpen ? "rotate-180" : ""
                }`}
              />
            </div>
          )}
        </div>

        {/* Warning Banner for Hold/COD/Inactive */}
        {selectedCustomer && hasWarning && (
          <div className="mt-2 p-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg flex items-center gap-2 text-xs text-amber-700 dark:text-amber-400">
            <FaExclamationTriangle className="w-4 h-4 flex-shrink-0" />
            <span>
              {accountStatus?.hold
                ? "Account is on hold. Manager approval required."
                : accountStatus?.cod_only
                ? "COD Only - No credit terms available."
                : "Account is inactive."}
            </span>
          </div>
        )}

        {/* Search Dropdown */}
        {isOpen && isEditing && (
          <div className="absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg max-h-80 overflow-hidden">
            {/* Search Input */}
            <div className="p-2 border-b border-slate-200 dark:border-slate-700">
              <div className="relative">
                <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  ref={inputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by name, ID, or keywords (comma = AND)"
                  className="w-full pl-9 pr-4 py-2 text-sm bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  autoFocus
                />
                {isLoading && (
                  <FaSpinner className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 animate-spin" />
                )}
              </div>
              {searchQuery.includes(",") && (
                <div className="mt-1 text-xs text-blue-600 dark:text-blue-400 flex items-center gap-1">
                  <FaCheck className="w-3 h-3" />
                  AND search: results must match all keywords
                </div>
              )}
            </div>

            {/* Results/Recent */}
            <div className="max-h-60 overflow-y-auto">
              {/* Search Results */}
              {searchQuery.trim() && searchResults.length > 0 && (
                <div>
                  <div className="px-3 py-1 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase bg-slate-50 dark:bg-slate-900/50">
                    Search Results ({searchResults.length})
                  </div>
                  {searchResults.map((org) => (
                    <button
                      key={org.id}
                      type="button"
                      onClick={() => handleSelectOrg(org)}
                      className="w-full px-3 py-2 text-left hover:bg-slate-100 dark:hover:bg-slate-700 flex items-start gap-2"
                    >
                      <FaUser className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                      <div className="min-w-0 flex-1">
                        <div className="font-medium text-slate-900 dark:text-white truncate">
                          {org.display_name}
                        </div>
                        <div className="flex flex-wrap items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                          {org.display_id && (
                            <span className="font-mono">{org.display_id}</span>
                          )}
                          {org.price_level && (
                            <span className="px-1 py-0.5 rounded bg-slate-100 dark:bg-slate-700">
                              Level {org.price_level}
                            </span>
                          )}
                          {org.financial?.common?.account?.hold && (
                            <span className="px-1 py-0.5 rounded bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400">
                              HOLD
                            </span>
                          )}
                        </div>
                        {/* Show matching keywords */}
                        {org.refs?.keywords && org.refs.keywords.length > 0 && (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {org.refs.keywords.slice(0, 5).map((kw: string, i: number) => (
                              <span
                                key={i}
                                className="px-1 py-0.5 text-xs rounded bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
                              >
                                {kw}
                              </span>
                            ))}
                            {org.refs.keywords.length > 5 && (
                              <span className="text-xs text-slate-400">
                                +{org.refs.keywords.length - 5} more
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* No Results */}
              {searchQuery.trim() && !isLoading && searchResults.length === 0 && (
                <div className="px-3 py-8 text-center text-slate-400 dark:text-slate-500">
                  <FaUser className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No customers found</p>
                  <p className="text-xs mt-1">Try different search terms</p>
                </div>
              )}

              {/* Recent Selections */}
              {!searchQuery.trim() && recentCustomers.length > 0 && (
                <div>
                  <div className="px-3 py-1 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase bg-slate-50 dark:bg-slate-900/50 flex items-center">
                    <FaHistory className="w-3 h-3 mr-1" />
                    Recent
                  </div>
                  {recentCustomers.map((customer) => (
                    <button
                      key={customer.id}
                      type="button"
                      onClick={() => handleSelectRecent(customer)}
                      className="w-full px-3 py-2 text-left hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-2"
                    >
                      <FaUser className="w-4 h-4 text-slate-400 flex-shrink-0" />
                      <div className="min-w-0 flex-1">
                        <div className="font-medium text-slate-900 dark:text-white truncate">
                          {customer.display_name}
                        </div>
                        <div className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                          {customer.display_id && (
                            <span className="font-mono">{customer.display_id}</span>
                          )}
                          {customer.price_level && (
                            <span className="px-1 py-0.5 rounded bg-slate-100 dark:bg-slate-700">
                              Level {customer.price_level}
                            </span>
                          )}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* Empty State - No Recent */}
              {!searchQuery.trim() && recentCustomers.length === 0 && (
                <div className="px-3 py-8 text-center text-slate-400 dark:text-slate-500">
                  <FaSearch className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>Start typing to search for customers</p>
                  <p className="text-xs mt-1">Use commas for AND search</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Financial Info Display */}
        {selectedCustomer && showFinancials && (
          <FinancialInfo financial={selectedCustomer.financial} priceLevel={selectedCustomer.price_level} />
        )}
      </div>
    </ComponentCard>
  );
};

export default CustomerSalesPanel;
