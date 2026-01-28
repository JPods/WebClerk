/**
 * PartySelector - Unified customer/vendor/manufacturer selector for transactions
 *
 * Provides a searchable dropdown/modal for selecting parties (customers, vendors, manufacturers)
 * Reusable across all transaction types with appropriate party type based on transaction.
 *
 * Usage:
 *   - Sales transactions (proposal, order, invoice): select customer
 *   - Purchase transactions (purchase_order, work_order): select vendor
 *   - Any transaction: optionally select manufacturer
 */
import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  FaSearch,
  FaUser,
  FaBuilding,
  FaTruck,
  FaIndustry,
  FaTimes,
  FaPlus,
  FaSpinner,
  FaChevronDown,
  FaHistory,
} from "react-icons/fa";
import {
  customerApi,
  vendorApi,
  manufacturerApi,
} from "@/apps/orgs/services/orgApi";
import type { Organization } from "@/apps/orgs/types/orgTypes";

// Party type determines which entity we're selecting
export type PartyType = "customer" | "vendor" | "manufacturer";

// Selected party summary (minimal data needed for display)
export interface SelectedParty {
  id: number;
  name: string;
  ida?: string;
  type: PartyType;
}

// Props for the PartySelector
export interface PartySelectorProps {
  /** Type of party to select */
  partyType: PartyType;

  /** Currently selected party ID */
  value?: number | null;

  /** Callback when party is selected */
  onChange: (party: SelectedParty | null) => void;

  /** Label to display */
  label?: string;

  /** Placeholder text */
  placeholder?: string;

  /** Whether the field is required */
  required?: boolean;

  /** Whether the selector is disabled */
  disabled?: boolean;

  /** Error message to display */
  error?: string;

  /** Size variant */
  size?: "sm" | "md" | "lg";

  /** Additional CSS classes */
  className?: string;

  /** Show recent selections */
  showRecent?: boolean;

  /** Maximum recent items to show */
  maxRecent?: number;
}

// Configuration per party type
const partyConfig: Record<
  PartyType,
  {
    icon: React.ComponentType<{ className?: string }>;
    label: string;
    searchPlaceholder: string;
    emptyMessage: string;
    api: typeof customerApi;
  }
> = {
  customer: {
    icon: FaUser,
    label: "Customer",
    searchPlaceholder: "Search customers by name or ID...",
    emptyMessage: "No customers found",
    api: customerApi,
  },
  vendor: {
    icon: FaTruck,
    label: "Vendor",
    searchPlaceholder: "Search vendors by name or ID...",
    emptyMessage: "No vendors found",
    api: vendorApi,
  },
  manufacturer: {
    icon: FaIndustry,
    label: "Manufacturer",
    searchPlaceholder: "Search manufacturers by name or ID...",
    emptyMessage: "No manufacturers found",
    api: manufacturerApi,
  },
};

// Local storage key for recent selections
const getRecentKey = (partyType: PartyType) =>
  `partySelector_recent_${partyType}`;

// Size classes
const sizeClasses = {
  sm: "h-8 text-sm px-2",
  md: "h-10 text-base px-3",
  lg: "h-12 text-lg px-4",
};

export const PartySelector: React.FC<PartySelectorProps> = ({
  partyType,
  value,
  onChange,
  label,
  placeholder,
  required = false,
  disabled = false,
  error,
  size = "sm",
  className = "",
  showRecent = true,
  maxRecent = 5,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Organization[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedParty, setSelectedParty] = useState<SelectedParty | null>(
    null,
  );
  const [recentParties, setRecentParties] = useState<SelectedParty[]>([]);

  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const config = partyConfig[partyType];
  const Icon = config.icon;

  // Load recent parties from localStorage
  useEffect(() => {
    if (showRecent) {
      try {
        const stored = localStorage.getItem(getRecentKey(partyType));
        if (stored) {
          setRecentParties(JSON.parse(stored).slice(0, maxRecent));
        }
      } catch {
        // Ignore localStorage errors
      }
    }
  }, [partyType, showRecent, maxRecent]);

  // Load selected party details if value changes
  useEffect(() => {
    if (value && value > 0) {
      // Check if we already have this party in recent selections
      const recentMatch = recentParties.find((p) => p.id === value);

      if (recentMatch) {
        setSelectedParty(recentMatch);
      } else {
        // Check search results (Organization type)
        const searchMatch = searchResults.find((r) => r.id === value);
        if (searchMatch) {
          setSelectedParty({
            id: value,
            name: searchMatch.display_name || "",
            ida: searchMatch.display_id,
            type: partyType,
          });
        } else {
          // Fetch the party details
          config.api
            .get(value)
            .then((party) => {
              if (party && party.id) {
                setSelectedParty({
                  id: party.id,
                  name: party.display_name || "",
                  ida: party.display_id,
                  type: partyType,
                });
              }
            })
            .catch(() => {
              // Party not found, clear selection
              setSelectedParty(null);
            });
        }
      }
    } else {
      setSelectedParty(null);
    }
  }, [value, partyType, config.api, recentParties, searchResults]);

  // Search for parties
  const handleSearch = useCallback(
    async (query: string) => {
      if (!query.trim()) {
        setSearchResults([]);
        return;
      }

      setIsLoading(true);
      try {
        const response = await config.api.list({
          search: query,
          is_active: true,
          limit: 20,
        });
        setSearchResults(response.results || []);
      } catch (err) {
        console.error(`Error searching ${partyType}:`, err);
        setSearchResults([]);
      } finally {
        setIsLoading(false);
      }
    },
    [config.api, partyType],
  );

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
  const saveToRecent = (party: SelectedParty) => {
    try {
      const key = getRecentKey(partyType);
      const current = localStorage.getItem(key);
      let recent: SelectedParty[] = current ? JSON.parse(current) : [];

      // Remove if already exists
      recent = recent.filter((p) => p.id !== party.id);

      // Add to front
      recent.unshift(party);

      // Limit size
      recent = recent.slice(0, maxRecent);

      localStorage.setItem(key, JSON.stringify(recent));
      setRecentParties(recent);
    } catch {
      // Ignore localStorage errors
    }
  };

  // Handle party selection
  // Handle party selection - accepts either Organization or SelectedParty
  const handleSelectOrg = (org: Organization) => {
    const party: SelectedParty = {
      id: org.id,
      name: org.display_name || "",
      ida: org.display_id,
      type: partyType,
    };

    setSelectedParty(party);
    saveToRecent(party);
    onChange(party);
    setIsOpen(false);
    setSearchQuery("");
    setSearchResults([]);
  };

  const handleSelectRecent = (party: SelectedParty) => {
    setSelectedParty(party);
    saveToRecent(party);
    onChange(party);
    setIsOpen(false);
    setSearchQuery("");
    setSearchResults([]);
  };

  // Handle clear selection
  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedParty(null);
    onChange(null);
  };

  // Toggle dropdown
  const handleToggle = () => {
    if (!disabled) {
      setIsOpen(!isOpen);
      if (!isOpen) {
        setTimeout(() => inputRef.current?.focus(), 100);
      }
    }
  };

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      {/* Label */}
      {label && (
        <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}

      {/* Main Input/Display */}
      <div
        onClick={handleToggle}
        className={`
          flex items-center justify-between w-full
          bg-white dark:bg-slate-800
          border rounded-lg cursor-pointer
          transition-colors duration-150
          ${sizeClasses[size]}
          ${
            error
              ? "border-red-500 dark:border-red-500"
              : "border-slate-300 dark:border-slate-600 hover:border-slate-400 dark:hover:border-slate-500"
          }
          ${
            disabled
              ? "opacity-50 cursor-not-allowed bg-slate-100 dark:bg-slate-900"
              : ""
          }
          ${isOpen ? "ring-2 ring-blue-500 border-blue-500" : ""}
        `}
      >
        <div className="flex items-center flex-1 min-w-0">
          <Icon className="w-2 h-2 text-slate-400 dark:text-slate-500 mr-2 flex-shrink-0" />
          {selectedParty ? (
            <div className="flex items-center min-w-0">
              <span className="truncate  text-slate-900 dark:text-white text-xs">
                {selectedParty.name}
              </span>
              {selectedParty.ida && (
                <span className="ml-2 text-slate-500 dark:text-slate-400 text-sm">
                  ({selectedParty.ida})
                </span>
              )}
            </div>
          ) : (
            <span className="text-slate-400 dark:text-slate-500 text-xs">
              {placeholder || `Select ${config.label}...`}
            </span>
          )}
        </div>

        <div className="flex items-center ml-2">
          {selectedParty && !disabled && (
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
      </div>

      {/* Error message */}
      {error && <p className="mt-1 text-sm text-red-500">{error}</p>}

      {/* Dropdown */}
      {isOpen && (
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
                placeholder={config.searchPlaceholder}
                className="w-full pl-9 pr-4 py-2 text-sm bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                autoFocus
              />
              {isLoading && (
                <FaSpinner className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 animate-spin" />
              )}
            </div>
          </div>

          {/* Results/Recent */}
          <div className="max-h-60 overflow-y-auto">
            {/* Search Results */}
            {searchQuery.trim() && searchResults.length > 0 && (
              <div>
                <div className="px-3 py-1 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase bg-slate-50 dark:bg-slate-900/50">
                  Search Results
                </div>
                {searchResults.map((org) => (
                  <button
                    key={org.id}
                    type="button"
                    onClick={() => handleSelectOrg(org)}
                    className="w-full px-3 py-2 text-left hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center"
                  >
                    <Icon className="w-4 h-4 text-slate-400 mr-2 flex-shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="font-medium text-slate-900 dark:text-white truncate">
                        {org.display_name}
                      </div>
                      {org.display_id && (
                        <div className="text-sm text-slate-500 dark:text-slate-400">
                          {org.display_id}
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
                <FaBuilding className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>{config.emptyMessage}</p>
                <p className="text-sm mt-1">Try a different search term</p>
              </div>
            )}

            {/* Recent Selections */}
            {!searchQuery.trim() && showRecent && recentParties.length > 0 && (
              <div>
                <div className="px-3 py-1 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase bg-slate-50 dark:bg-slate-900/50 flex items-center">
                  <FaHistory className="w-3 h-3 mr-1" />
                  Recent
                </div>
                {recentParties.map((party) => (
                  <button
                    key={party.id}
                    type="button"
                    onClick={() => handleSelectRecent(party)}
                    className="w-full px-3 py-2 text-left hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center"
                  >
                    <Icon className="w-4 h-4 text-slate-400 mr-2 flex-shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="font-medium text-slate-900 dark:text-white truncate">
                        {party.name}
                      </div>
                      {party.ida && (
                        <div className="text-sm text-slate-500 dark:text-slate-400">
                          {party.ida}
                        </div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}

            {/* Empty State - No Recent */}
            {!searchQuery.trim() &&
              (!showRecent || recentParties.length === 0) && (
                <div className="px-3 py-8 text-center text-slate-400 dark:text-slate-500">
                  <FaSearch className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>Start typing to search for {partyType}s</p>
                </div>
              )}
          </div>

          {/* Create New Option */}
          <div className="border-t border-slate-200 dark:border-slate-700 p-2">
            <button
              type="button"
              className="w-full px-3 py-2 text-left text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-md flex items-center"
              onClick={() => {
                // TODO: Open create modal or navigate to create page
                console.log(`Create new ${partyType}`);
              }}
            >
              <FaPlus className="w-3 h-3 mr-2" />
              Create new {config.label}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// --- Convenience components for specific party types ---

export interface CustomerSelectorProps
  extends Omit<PartySelectorProps, "partyType"> {}

export const CustomerSelector: React.FC<CustomerSelectorProps> = (props) => (
  <PartySelector {...props} partyType="customer" />
);

export interface VendorSelectorProps
  extends Omit<PartySelectorProps, "partyType"> {}

export const VendorSelector: React.FC<VendorSelectorProps> = (props) => (
  <PartySelector {...props} partyType="vendor" />
);

export interface ManufacturerSelectorProps
  extends Omit<PartySelectorProps, "partyType"> {}

export const ManufacturerSelector: React.FC<ManufacturerSelectorProps> = (
  props,
) => <PartySelector {...props} partyType="manufacturer" />;

// --- Transaction-aware party selector ---

export type TransactionPartyType = "sales" | "purchase";

export interface TransactionPartySelectorProps
  extends Omit<PartySelectorProps, "partyType"> {
  /** Transaction type determines which party (customer for sales, vendor for purchase) */
  transactionType: TransactionPartyType;
}

/**
 * TransactionPartySelector - Automatically selects the correct party type based on transaction
 *
 * - Sales transactions (proposal, order, invoice): selects customer
 * - Purchase transactions (purchase_order, work_order): selects vendor
 */
export const TransactionPartySelector: React.FC<
  TransactionPartySelectorProps
> = ({ transactionType, ...props }) => {
  const partyType = transactionType === "sales" ? "customer" : "vendor";
  return <PartySelector {...props} partyType={partyType} />;
};

export default PartySelector;
