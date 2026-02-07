/**
 * SearchableSelect - A searchable dropdown select component
 *
 * Features:
 * - Search/filter through options
 * - Keyboard navigation (arrow keys, enter, escape)
 * - Customizable option labels
 * - Loading state support
 * - Dark mode compatible
 */
import React, { useState, useRef, useEffect, useCallback } from "react";
import { FaSearch, FaChevronDown, FaSpinner, FaTimes } from "react-icons/fa";

export interface SearchableSelectOption {
  value: string | number;
  label: string;
  description?: string;
}

export interface SearchableSelectProps {
  /** Available options */
  options: SearchableSelectOption[];
  /** Currently selected value */
  value: string | number | null;
  /** Callback when value changes */
  onChange: (value: string | number | null) => void;
  /** Placeholder text when no value selected */
  placeholder?: string;
  /** Search input placeholder */
  searchPlaceholder?: string;
  /** Label for the field */
  label?: string;
  /** Whether the field is disabled */
  disabled?: boolean;
  /** Whether options are loading */
  loading?: boolean;
  /** Allow clearing the selection */
  clearable?: boolean;
  /** Additional CSS classes for the container */
  className?: string;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** No results message */
  noResultsMessage?: string;
}

const sizeClasses = {
  sm: "px-2 py-1 text-xs",
  md: "px-3 py-2 text-sm",
  lg: "px-4 py-3 text-base",
};

export const SearchableSelect: React.FC<SearchableSelectProps> = ({
  options,
  value,
  onChange,
  placeholder = "Select...",
  searchPlaceholder = "Search...",
  label,
  disabled = false,
  loading = false,
  clearable = true,
  className = "",
  size = "sm",
  noResultsMessage = "No results found",
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Filter options based on search query
  const filteredOptions = options.filter((option) => {
    const query = searchQuery.toLowerCase();
    return (
      option.label.toLowerCase().includes(query) ||
      option.description?.toLowerCase().includes(query) ||
      String(option.value).toLowerCase().includes(query)
    );
  });

  // Get selected option
  const selectedOption = options.find((opt) => opt.value === value);

  // Handle click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setSearchQuery("");
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Focus input when dropdown opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Reset highlighted index when filtering
  useEffect(() => {
    setHighlightedIndex(-1);
  }, [searchQuery]);

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlightedIndex >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll("[data-option]");
      const item = items[highlightedIndex] as HTMLElement;
      if (item) {
        item.scrollIntoView({ block: "nearest" });
      }
    }
  }, [highlightedIndex]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!isOpen) {
        if (e.key === "Enter" || e.key === " " || e.key === "ArrowDown") {
          e.preventDefault();
          setIsOpen(true);
        }
        return;
      }

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setHighlightedIndex((prev) =>
            prev < filteredOptions.length - 1 ? prev + 1 : prev,
          );
          break;
        case "ArrowUp":
          e.preventDefault();
          setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : prev));
          break;
        case "Enter":
          e.preventDefault();
          if (highlightedIndex >= 0 && filteredOptions[highlightedIndex]) {
            onChange(filteredOptions[highlightedIndex].value);
            setIsOpen(false);
            setSearchQuery("");
          }
          break;
        case "Escape":
          e.preventDefault();
          setIsOpen(false);
          setSearchQuery("");
          break;
      }
    },
    [isOpen, highlightedIndex, filteredOptions, onChange],
  );

  const handleSelect = (optionValue: string | number) => {
    onChange(optionValue);
    setIsOpen(false);
    setSearchQuery("");
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange(null);
  };

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {label && (
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
          {label}
        </label>
      )}

      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        className={`
          w-full px-3 py-2 flex items-center justify-between
          border border-slate-300 dark:border-slate-600 rounded-lg
          bg-white dark:bg-slate-700 text-slate-900 dark:text-white
          transition-colors
          ${sizeClasses[size]}
          ${
            disabled
              ? "opacity-50 cursor-not-allowed"
              : "hover:border-slate-400 dark:hover:border-slate-500 cursor-pointer"
          }
          ${isOpen ? "ring-2 ring-blue-500 border-blue-500" : ""}
        `}
      >
        <span
          className={selectedOption ? "" : "text-slate-400 dark:text-slate-500"}
        >
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <div className="flex items-center gap-1">
          {loading && (
            <FaSpinner className="w-3 h-3 animate-spin text-slate-400" />
          )}
          {clearable && selectedOption && !disabled && (
            <button
              type="button"
              onClick={handleClear}
              className="p-0.5 hover:bg-slate-200 dark:hover:bg-slate-600 rounded"
            >
              <FaTimes className="w-3 h-3 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300" />
            </button>
          )}
          <FaChevronDown
            className={`w-3 h-3 text-slate-400 transition-transform ${
              isOpen ? "rotate-180" : ""
            }`}
          />
        </div>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg max-h-72 overflow-hidden">
          {/* Search Input */}
          <div className="p-2 border-b border-slate-200 dark:border-slate-700">
            <div className="relative">
              <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400" />
              <input
                ref={inputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={searchPlaceholder}
                className={`
                  w-full pl-8 pr-3 px-3 py-2 text-xs
                  bg-slate-50 dark:bg-slate-900
                  border border-slate-200 dark:border-slate-700 rounded-md
                  focus:outline-none focus:ring-2 focus:ring-blue-500
                  text-slate-900 dark:text-white
                  placeholder-slate-400 dark:placeholder-slate-500
                `}
              />
            </div>
          </div>

          {/* Options List */}
          <div ref={listRef} className="max-h-52 overflow-y-auto">
            {filteredOptions.length === 0 ? (
              <div className="px-3 py-4 text-center text-slate-400 dark:text-slate-500 text-xs">
                {noResultsMessage}
              </div>
            ) : (
              filteredOptions.map((option, index) => (
                <button
                  key={option.value}
                  type="button"
                  data-option
                  onClick={() => handleSelect(option.value)}
                  onMouseEnter={() => setHighlightedIndex(index)}
                  className={`
                    w-full px-3 py-2 text-left text-xs
                    ${
                      value === option.value
                        ? "bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                        : highlightedIndex === index
                        ? "bg-slate-100 dark:bg-slate-700"
                        : "hover:bg-slate-50 dark:hover:bg-slate-700/50"
                    }
                  `}
                >
                  <div className="font-medium text-slate-900 dark:text-white">
                    {option.label}
                  </div>
                  {option.description && (
                    <div className="text-slate-500 dark:text-slate-400 text-xs mt-0.5">
                      {option.description}
                    </div>
                  )}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchableSelect;
