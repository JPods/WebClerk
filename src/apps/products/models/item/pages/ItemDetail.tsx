/**
 * ItemDetail.tsx
 * 
 * Standard Item Detail page using Enterprise Best Practices Layout following UX research:
 * - Two-column layout with labels on the left (scannable)
 * - Logical field groupings in collapsible sections
 * - Consistent label widths for vertical alignment
 * - Compact but readable spacing
 * - Visual hierarchy with section headers
 * - Keyboard navigation support
 * 
 * References:
 * - Nielsen Norman Group enterprise form guidelines
 * - Luke Wroblewski's label placement research
 * - Baymard Institute density studies
 */

import { useEffect, useMemo, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import ComponentCard from "@/components/common/ComponentCard";
import { DevBadge } from "@/components/common/DevBadge";
import Label from "@/components/form/Label";
import { SimpleDetailHeader } from "@/components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "@/components/common/SimpleDetailToolbar";
import Input from "@/components/form/input/InputField";
import Select from "@/components/form/Select";
import Checkbox from "@/components/form/input/Checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableRow,
} from "@/components/ui/table";
import Badge from "@/components/ui/badge/Badge";

import { createItem, updateItem } from "../services/itemApi";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useParams, useSearchParams } from "react-router";
import { getRecord, saveRecord } from "@/api/wcapi";
import { itemSchema, type ItemFormValues } from "../utils/itemSchema";
import { ItemAddProps } from "../types/itemType";
import BOMSection from "../components/BOMSection";
import { 
  FaChevronDown,
  FaChevronRight,
  FaBox,
  FaDollarSign,
  FaWarehouse,
  FaCog,
  FaListAlt,
  FaCalculator,
  FaFileInvoice,
  FaImage,
  FaPlus,
  FaTrash,
} from "react-icons/fa";
import { useDetailFieldAccess } from "@/hooks/useDetailFieldAccess";

import { CheckSquare, MessageSquare, FileIcon, Code } from "lucide-react";

// Tab navigation
import { DetailTabs, useDetailTabs, TabConfig } from "@/components/common/DetailTabs";

// Panel Components
import {
  CommentsPanel,
  DocumentsPanel,
  ActionsPanel,
} from "@/apps/common/components/panels";
import JsonFieldEditor from "@/apps/common/components/JsonFieldEditor";
import { ScalarCard, JsonCard, BaseModelCards } from "@/apps/common/components/detail";

// ============================================================================
// Types (matching Django Item model)
// ============================================================================

interface QuantityData {
  on_hand?: number;
  allocated?: number;
  available?: number;
  on_so?: number;
  on_po?: number;
  on_p?: number;
  on_reciept?: number;  // Note: typo from legacy
  on_in?: number;
  on_wo?: number;
}

interface PriceTier {
  level: string;
  price: number;
}

interface QtyBreak {
  min_qty: number;
  unit_price?: number;
  variant_item_id?: number;
}

interface PriceData {
  base?: number;
  msrp?: number;
  retail?: number;
  wholesale?: number;
  distributor?: number;
  sample?: number;
  tiers?: PriceTier[];
  qty_breaks?: QtyBreak[];
  currency?: string;
  history?: Array<{ dt_utc: string; field: string; old: any; new: any }>;
}

interface CostBreak {
  min_qty: number;
  unit_cost?: number;
  variant_item_id?: number;
}

interface CostData {
  standard?: number;
  last?: number;
  avg?: number;
  landed?: number;
  currency?: string;
  components?: Record<string, number>;
  qty_breaks?: CostBreak[];
  history?: Array<{ dt_utc: string; field: string; old: any; new: any }>;
}

interface GlsData {
  inventory?: string;
  cogs?: string;
  revenue?: string;
  variance?: string;
  [key: string]: string | undefined;
}

interface TaxCodeData {
  code?: string;
  jurisdiction?: string;
  category?: string;
  rate?: number;
  exemptions?: string[];
  jurisdiction_params?: Array<{
    jurisdiction: string;
    kind?: string;
    params?: Record<string, any>;
    effective_from?: string;
    effective_to?: string;
  }>;
}

interface FlagsData {
  back_order_allowed?: boolean;
  discountable?: boolean;
  linked?: boolean;
  not_tracked?: boolean;
  pacing?: boolean;
  print_suppressed?: boolean;
  serialized?: boolean;
  tally_by_type?: boolean;
}

interface CatalogWebData {
  slug?: string;
  title?: string;
  short?: string;
  seo?: Record<string, any>;
}

interface CatalogData {
  categories?: string[];
  attributes?: Record<string, any>;
  web?: CatalogWebData;
  flags?: Record<string, boolean>;
}

interface ItemData {
  id?: number;
  name?: string;
  sku?: string;
  qr_code?: string;
  kind?: string;
  uom?: string;
  base_uom?: string;
  description?: string;
  category?: string;
  specification_id?: number;
  row_version?: number;
  price?: PriceData | number;
  cost?: CostData;
  quantity?: QuantityData;
  flags?: FlagsData;
  gls?: GlsData;
  tax_code?: TaxCodeData;
  catalog?: CatalogData;
  is_active?: boolean;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  comments?: any;
  metadata?: any;
  refs?: any;
  prefs?: any;
  actions?: any;
  [key: string]: any;
}

// ============================================================================
// Enterprise Field Row Component
// Label on left (fixed width), input on right
// Optimized for daily use and scannability
// ============================================================================

interface FieldRowProps {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
  error?: string;
  required?: boolean;
  hint?: string;
}

function FieldRow({ label, htmlFor, children, error, required, hint }: FieldRowProps) {
  return (
    <div className="flex items-start gap-3 py-2">
      <Label 
        htmlFor={htmlFor} 
        className="w-32 shrink-0 pt-2 text-right text-sm font-medium text-slate-600 dark:text-slate-400"
      >
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </Label>
      <div className="flex-1 min-w-0">
        {children}
        {hint && !error && <p className="mt-0.5 text-xs text-slate-400">{hint}</p>}
        {error && <p className="mt-0.5 text-xs text-red-500">{error}</p>}
      </div>
    </div>
  );
}

// ============================================================================
// Collapsible Section Component
// Groups related fields together
// ============================================================================

interface SectionProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultExpanded?: boolean;
}

function Section({ title, icon, children, defaultExpanded = true }: SectionProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className="mb-4 border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
      <button
        type="button"
        className="w-full flex items-center justify-between px-4 py-2.5 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <FaChevronDown className="text-slate-400 w-3 h-3" />
          ) : (
            <FaChevronRight className="text-slate-400 w-3 h-3" />
          )}
          <span className="text-slate-500">{icon}</span>
          <span className="font-semibold text-sm text-slate-700 dark:text-slate-200">{title}</span>
        </div>
      </button>
      {isExpanded && (
        <div className="px-4 py-3 bg-white dark:bg-slate-900">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-6">
            {children}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Data Display Row Component (for view mode - single column table layout)
// ============================================================================

interface DataRowProps {
  label: string;
  value: any;
  highlight?: boolean;
}

function DataRow({ label, value, highlight = false }: DataRowProps) {
  const formatValue = (val: any): string => {
    if (val === null || val === undefined) return "—";
    if (typeof val === "boolean") return val ? "Yes" : "No";
    if (typeof val === "number") {
      if (label.toLowerCase().includes("price") || label.toLowerCase().includes("cost")) {
        return `$${val.toFixed(2)}`;
      }
      return val.toLocaleString();
    }
    if (typeof val === "object") return JSON.stringify(val);
    return String(val);
  };

  return (
    <TableRow className="border-b border-gray-100 dark:border-white/[0.05]">
      <TableCell className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400 w-1/3">
        {label}
      </TableCell>
      <TableCell
        className={`px-4 py-3 ${
          highlight
            ? "font-semibold text-blue-600 dark:text-blue-400"
            : "text-gray-800 dark:text-white"
        }`}
      >
        {formatValue(value)}
      </TableCell>
    </TableRow>
  );
}

// ============================================================================
// Data Field Component (for view mode - multi-column grid layout)
// Label and value on same line, label is exact field name (lowercase)
// ============================================================================

interface DataFieldProps {
  label: string;
  value: any;
  highlight?: boolean;
  isCurrency?: boolean;
}

function DataField({ label, value, highlight = false, isCurrency = false }: DataFieldProps) {
  const formatValue = (val: any): string => {
    if (val === null || val === undefined) return "—";
    if (typeof val === "boolean") return val ? "Yes" : "No";
    if (typeof val === "number") {
      if (isCurrency) {
        return `$${val.toFixed(2)}`;
      }
      return val.toLocaleString();
    }
    if (typeof val === "object") return JSON.stringify(val);
    return String(val);
  };

  return (
    <div className="flex items-baseline gap-2 py-1">
      <dt className="text-xs font-mono text-gray-500 dark:text-gray-400 shrink-0">
        {label}
      </dt>
      <dd
        className={`text-sm ${
          highlight
            ? "font-semibold text-blue-600 dark:text-blue-400"
            : "text-gray-900 dark:text-white"
        }`}
      >
        {formatValue(value)}
      </dd>
    </div>
  );
}

// ============================================================================
// Data Field Grid Component (for view mode - multi-column layout wrapper)
// ============================================================================

interface DataFieldGridProps {
  children: React.ReactNode;
  columns?: 2 | 3 | 4;
}

function DataFieldGrid({ children, columns = 2 }: DataFieldGridProps) {
  const gridClass = {
    2: "grid-cols-1 sm:grid-cols-2",
    3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-2 sm:grid-cols-4",
  }[columns];
  
  return (
    <dl className={`grid gap-x-6 gap-y-1 ${gridClass}`}>
      {children}
    </dl>
  );
}

// ============================================================================
// Data Section Component (for view mode collapsible tables)
// ============================================================================

interface DataSectionProps {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  collapsible?: boolean;
  defaultOpen?: boolean;
  noTable?: boolean;
}

function DataSection({
  title,
  icon,
  children,
  collapsible = true,
  defaultOpen = true,
  noTable = false,
}: DataSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="mb-4 border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
      <button
        type="button"
        className={`w-full flex items-center justify-between px-4 py-2.5 bg-slate-50 dark:bg-slate-800 ${
          collapsible ? "hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer" : ""
        } transition-colors`}
        onClick={() => collapsible && setIsOpen(!isOpen)}
        disabled={!collapsible}
      >
        <div className="flex items-center gap-2">
          {collapsible && (
            isOpen ? (
              <FaChevronDown className="text-slate-400 w-3 h-3" />
            ) : (
              <FaChevronRight className="text-slate-400 w-3 h-3" />
            )
          )}
          {icon && <span className="text-slate-500">{icon}</span>}
          <span className="font-semibold text-sm text-slate-700 dark:text-slate-200">{title}</span>
        </div>
      </button>
      {isOpen && (
        <div className="bg-white dark:bg-slate-900">
          {noTable ? (
            <div className="p-4">{children}</div>
          ) : (
            <Table>{children}</Table>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Quantity Status Badge
// ============================================================================

function QuantityStatusBadge({ quantity }: { quantity?: QuantityData }) {
  if (!quantity) return null;

  const available = quantity.available ?? 0;
  const onHand = quantity.on_hand ?? 0;

  let color: "success" | "warning" | "error" | "primary" = "primary";
  let label = "Unknown";

  if (available > 10) {
    color = "success";
    label = "In Stock";
  } else if (available > 0) {
    color = "warning";
    label = "Low Stock";
  } else if (onHand > 0) {
    color = "warning";
    label = "Allocated";
  } else {
    color = "error";
    label = "Out of Stock";
  }

  return <Badge color={color}>{label}</Badge>;
}

// ============================================================================
// Inventory Grid (Horizontal Layout - Labels on Top)
// ============================================================================

interface InventoryGridProps {
  quantity: QuantityData;
}

function InventoryGrid({ quantity }: InventoryGridProps) {
  const inventoryItems = [
    { label: "On Hand", value: quantity.on_hand, highlight: true },
    { label: "Allocated", value: quantity.allocated, highlight: false },
    { label: "Available", value: quantity.available, highlight: true },
    { label: "On SO", value: quantity.on_so, highlight: false },
    { label: "On PO", value: quantity.on_po, highlight: false },
    { label: "On Proposal", value: quantity.on_p, highlight: false },
    { label: "On Receipt", value: quantity.on_reciept, highlight: false },
    { label: "On Inbound", value: quantity.on_in, highlight: false },
    { label: "On WO", value: quantity.on_wo, highlight: false },
  ];

  const formatValue = (val: number | undefined): string => {
    if (val === null || val === undefined) return "—";
    return val.toLocaleString();
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-700">
            {inventoryItems.map((item) => (
              <th
                key={item.label}
                className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 text-center"
              >
                {item.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            {inventoryItems.map((item) => (
              <td
                key={item.label}
                className={`px-3 py-3 text-center text-lg ${
                  item.highlight
                    ? "font-bold text-blue-600 dark:text-blue-400"
                    : "font-medium text-gray-800 dark:text-white"
                }`}
              >
                {formatValue(item.value)}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}

// ============================================================================
// Image Panel Component
// Displays and manages item images from metadata.images
// ============================================================================

interface ImageData {
  primary?: string;
  gallery?: string[];
  thumbnail?: string;
}

interface ImagePanelProps {
  images?: ImageData;
  itemId?: number;
  onImagesChange?: (images: ImageData) => void;
  editable?: boolean;
}

function ImagePanel({ images, itemId, onImagesChange, editable = false }: ImagePanelProps) {
  const dispatch = useDispatch();
  const [primaryUrl, setPrimaryUrl] = useState(images?.primary || "");
  const [galleryUrls, setGalleryUrls] = useState<string[]>(images?.gallery || []);
  const [showUrlInput, setShowUrlInput] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  
  // Sync state with props
  useEffect(() => {
    setPrimaryUrl(images?.primary || "");
    setGalleryUrls(images?.gallery || []);
  }, [images]);

  const getImageUrl = (path: string): string => {
    if (!path) return "";
    // If already absolute URL, return as-is
    if (path.startsWith("http://") || path.startsWith("https://")) {
      return path;
    }
    // Prefix with Django static images base URL
    const apiBase = import.meta.env.VITE_API_URL || "http://localhost:8000";
    return `${apiBase}/static/images/${path}`;
  };

  const saveImages = async (newImages: ImageData) => {
    if (!itemId) return;
    try {
      await saveRecord("item", {
        id: itemId,
        metadata: {
          images: newImages,
        },
      });
      if (onImagesChange) {
        onImagesChange(newImages);
      }
      return true;
    } catch (err) {
      console.error("Failed to save images:", err);
      dispatch(showToast({ message: "Failed to save image", type: "error" }));
      return false;
    }
  };

  const handleSetPrimary = async (url: string) => {
    const newImages: ImageData = {
      ...images,
      primary: url,
      thumbnail: images?.thumbnail || url, // Auto-set thumbnail if not set
    };
    
    if (await saveImages(newImages)) {
      dispatch(showToast({ message: "Primary image updated", type: "success" }));
    }
  };

  const handleAddToGallery = async () => {
    if (!newUrl.trim()) return;
    
    const updatedGallery = [...galleryUrls, newUrl.trim()];
    const newImages: ImageData = {
      ...images,
      gallery: updatedGallery,
      // If no primary, set the first gallery image as primary
      primary: images?.primary || newUrl.trim(),
    };
    
    if (await saveImages(newImages)) {
      setGalleryUrls(updatedGallery);
      setNewUrl("");
      setShowUrlInput(false);
      dispatch(showToast({ message: "Image added to gallery", type: "success" }));
    }
  };

  const handleRemoveFromGallery = async (index: number) => {
    const updatedGallery = galleryUrls.filter((_, i) => i !== index);
    const removedUrl = galleryUrls[index];
    
    const newImages: ImageData = {
      ...images,
      gallery: updatedGallery,
      // If removing the primary image, set next gallery image or clear
      primary: images?.primary === removedUrl 
        ? (updatedGallery[0] || "") 
        : images?.primary,
    };
    
    if (await saveImages(newImages)) {
      setGalleryUrls(updatedGallery);
      dispatch(showToast({ message: "Image removed", type: "success" }));
    }
  };

  const displayPrimary = primaryUrl || (galleryUrls.length > 0 ? galleryUrls[0] : "");

  return (
    <div className="h-full flex flex-col">
      {/* Primary Image Display */}
      <div className="flex-1 min-h-[280px] bg-gray-100 dark:bg-slate-800 rounded-lg overflow-hidden relative group">
        {displayPrimary ? (
          <img
            src={getImageUrl(displayPrimary)}
            alt="Primary product image"
            className="w-full h-full object-contain"
            onError={(e) => {
              (e.target as HTMLImageElement).src = "/images/placeholder-product.png";
            }}
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center text-gray-400 dark:text-gray-500">
            <FaImage className="w-16 h-16 mb-2" />
            <span className="text-sm">No image</span>
          </div>
        )}
        
        {/* Overlay actions on hover */}
        {editable && displayPrimary && (
          <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
            <button
              type="button"
              onClick={() => handleSetPrimary("")}
              className="p-2 bg-red-500 text-white rounded-full hover:bg-red-600"
              title="Remove primary image"
            >
              <FaTrash className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Gallery Thumbnails */}
      {(galleryUrls.length > 0 || editable) && (
        <div className="mt-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Gallery</span>
            {editable && (
              <button
                type="button"
                onClick={() => setShowUrlInput(!showUrlInput)}
                className="p-1 text-blue-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
                title="Add image"
              >
                <FaPlus className="w-3 h-3" />
              </button>
            )}
          </div>
          
          {/* URL Input */}
          {showUrlInput && (
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={newUrl}
                onChange={(e) => setNewUrl(e.target.value)}
                placeholder="Enter image URL or path..."
                className="flex-1 text-sm px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-slate-800 text-gray-900 dark:text-white"
                onKeyDown={(e) => e.key === "Enter" && handleAddToGallery()}
              />
              <button
                type="button"
                onClick={handleAddToGallery}
                className="px-2 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
              >
                Add
              </button>
            </div>
          )}
          
          {/* Thumbnail Grid */}
          <div className="flex gap-2 flex-wrap">
            {galleryUrls.map((url, index) => (
              <div
                key={index}
                className={`relative w-14 h-14 rounded overflow-hidden cursor-pointer border-2 transition-colors ${
                  url === primaryUrl 
                    ? "border-blue-500" 
                    : "border-transparent hover:border-gray-300 dark:hover:border-gray-600"
                }`}
                onClick={() => editable && handleSetPrimary(url)}
              >
                <img
                  src={getImageUrl(url)}
                  alt={`Gallery image ${index + 1}`}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = "/images/placeholder-product.png";
                  }}
                />
                {editable && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemoveFromGallery(index);
                    }}
                    className="absolute top-0 right-0 p-0.5 bg-red-500 text-white rounded-bl opacity-0 hover:opacity-100 transition-opacity"
                    title="Remove"
                  >
                    <FaTrash className="w-2 h-2" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Image paths display */}
      <div className="mt-3 space-y-1 text-xs font-mono bg-slate-50 dark:bg-slate-800/50 rounded p-2">
        <div className="flex items-center gap-2">
          <span className="text-slate-400 dark:text-slate-500 w-16">primary:</span>
          <span className="text-slate-600 dark:text-slate-300 truncate flex-1" title={primaryUrl || '(none)'}>
            {primaryUrl || <span className="italic text-slate-400">(none)</span>}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-slate-400 dark:text-slate-500 w-16">gallery:</span>
          <span className="text-slate-600 dark:text-slate-300 truncate flex-1" title={galleryUrls.join(', ') || '(empty)'}>
            {galleryUrls.length > 0 
              ? `[${galleryUrls.length}] ${galleryUrls[0]}${galleryUrls.length > 1 ? '...' : ''}`
              : <span className="italic text-slate-400">(empty)</span>
            }
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-slate-400 dark:text-slate-500 w-16">thumb:</span>
          <span className="text-slate-600 dark:text-slate-300 truncate flex-1" title={images?.thumbnail || '(none)'}>
            {images?.thumbnail || <span className="italic text-slate-400">(none)</span>}
          </span>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// View Mode: Item Data Display
// ============================================================================

interface ItemDataViewProps {
  data: ItemData;
  isAdmin: boolean;
  onDataChange?: (data: ItemData) => void;
}

function ItemDataView({ data, isAdmin, onDataChange }: ItemDataViewProps) {
  const formatDate = (timestamp?: number): string => {
    if (!timestamp) return "—";
    return new Date(timestamp).toLocaleString();
  };

  const getPrice = (price: PriceData | number | undefined): number | undefined => {
    if (typeof price === "number") return price;
    if (typeof price === "object" && price) return price.base ?? price.msrp;
    return undefined;
  };

  const handleImagesChange = (images: ImageData) => {
    if (onDataChange) {
      onDataChange({
        ...data,
        metadata: {
          ...data.metadata,
          images,
        },
      });
    }
  };

  return (
    <div className="space-y-4">
      {/* Header with status */}
      <div className="flex items-center justify-between pb-4 border-b border-gray-200 dark:border-gray-700">
        <div>
          <h2 className="text-2xl font-bold text-gray-800 dark:text-white">
            <DevBadge label="ItemDetail" className="mr-2" />
            {data.name || "Unnamed Item"}
          </h2>
          <p className="text-gray-500 dark:text-gray-400">
            SKU: {data.sku || "N/A"} | ID: {data.id || "—"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <QuantityStatusBadge quantity={data.quantity} />
          {data.is_active !== undefined && (
            <Badge color={data.is_active ? "success" : "error"}>
              {data.is_active ? "Active" : "Inactive"}
            </Badge>
          )}
        </div>
      </div>

      {/* 1. Basic Information - expanded */}
      <DataSection title="Basic Information" icon={<FaBox className="w-4 h-4" />} defaultOpen={true} noTable>
        {/* Row 1: name, sku, qr_code, id */}
        <DataFieldGrid columns={4}>
          <DataField label="name" value={data.name} highlight />
          <DataField label="sku" value={data.sku} />
          <DataField label="qr_code" value={data.qr_code} />
          <DataField label="id" value={data.id} />
        </DataFieldGrid>
        {/* Row 2: kind, uom, base_uom, specification_id */}
        <DataFieldGrid columns={4}>
          <DataField label="kind" value={data.kind} />
          <DataField label="uom" value={data.uom} />
          <DataField label="base_uom" value={data.base_uom} />
          <DataField label="specification_id" value={data.specification_id} />
        </DataFieldGrid>
        {/* Row 3: description (full width) */}
        <DataFieldGrid columns={2}>
          <div className="col-span-2">
            <DataField label="description" value={data.description} />
          </div>
        </DataFieldGrid>
      </DataSection>

      {/* 2. Pricing & Cost with Image - side by side layout */}
      <div className="flex gap-4 mb-4">
        {/* Pricing & Cost Column (60%) */}
        <div className="w-[60%] space-y-4">
          {/* Pricing - expanded */}
          <DataSection title="Pricing" icon={<FaDollarSign className="w-4 h-4" />} defaultOpen={true} noTable>
            {typeof data.price === "object" && data.price ? (
              <>
                <DataFieldGrid columns={4}>
                  <DataField label=".base" value={(data.price as PriceData).base} highlight isCurrency />
                  <DataField label=".msrp" value={(data.price as PriceData).msrp} isCurrency />
                  <DataField label=".retail" value={(data.price as PriceData).retail} isCurrency />
                  <DataField label=".wholesale" value={(data.price as PriceData).wholesale} isCurrency />
                </DataFieldGrid>
                <DataFieldGrid columns={4}>
                  <DataField label=".distributor" value={(data.price as PriceData).distributor} isCurrency />
                  <DataField label=".sample" value={(data.price as PriceData).sample} isCurrency />
                  <DataField label=".currency" value={(data.price as PriceData).currency || "USD"} />
                  <DataField label=".history" value={(data.price as PriceData).history?.length ?? 0} />
                </DataFieldGrid>
                {/* Tiers */}
                {(data.price as PriceData).tiers && (data.price as PriceData).tiers!.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Tiers</p>
                    <div className="bg-gray-50 dark:bg-slate-800 rounded p-2 text-sm">
                      {(data.price as PriceData).tiers!.map((t, i) => (
                        <span key={i} className="mr-3">{t.level}: ${t.price?.toFixed(2)}</span>
                      ))}
                    </div>
                  </div>
                )}
                {/* Qty Breaks */}
                {(data.price as PriceData).qty_breaks && (data.price as PriceData).qty_breaks!.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Qty Breaks</p>
                    <div className="overflow-x-auto">
                      <table className="min-w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-200 dark:border-gray-700">
                            <th className="px-2 py-1 text-left text-xs font-semibold text-gray-500">Min Qty</th>
                            <th className="px-2 py-1 text-left text-xs font-semibold text-gray-500">Unit Price</th>
                            <th className="px-2 py-1 text-left text-xs font-semibold text-gray-500">Variant ID</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(data.price as PriceData).qty_breaks!.map((b, i) => (
                            <tr key={i} className="border-b border-gray-100 dark:border-gray-800">
                              <td className="px-2 py-1">{b.min_qty}</td>
                              <td className="px-2 py-1">{b.unit_price != null ? `$${b.unit_price.toFixed(2)}` : "—"}</td>
                              <td className="px-2 py-1">{b.variant_item_id ?? "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <DataFieldGrid columns={2}>
                <DataField label="price" value={getPrice(data.price)} highlight isCurrency />
              </DataFieldGrid>
            )}
          </DataSection>

          {/* Cost - expanded */}
          {data.cost && typeof data.cost === "object" && (
            <DataSection title="Cost" icon={<FaCalculator className="w-4 h-4" />} defaultOpen={true} noTable>
              <DataFieldGrid columns={3}>
                <DataField label=".standard" value={(data.cost as CostData).standard} isCurrency />
                <DataField label=".last" value={(data.cost as CostData).last} isCurrency />
                <DataField label=".avg" value={(data.cost as CostData).avg} isCurrency />
              </DataFieldGrid>
              <DataFieldGrid columns={2}>
                <DataField label=".landed" value={(data.cost as CostData).landed} isCurrency />
                <DataField label=".currency" value={(data.cost as CostData).currency || "USD"} />
              </DataFieldGrid>
              {/* Components */}
              {(data.cost as CostData).components && Object.keys((data.cost as CostData).components!).length > 0 && (
                <div className="mt-2">
                  <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Components</p>
                  <div className="bg-gray-50 dark:bg-slate-800 rounded p-2 text-sm">
                    {Object.entries((data.cost as CostData).components!).map(([k, v]) => (
                      <span key={k} className="mr-3">{k}: ${v?.toFixed(2)}</span>
                    ))}
                  </div>
                </div>
              )}
              {/* Qty Breaks */}
              {(data.cost as CostData).qty_breaks && (data.cost as CostData).qty_breaks!.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Cost Breaks</p>
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-200 dark:border-gray-700">
                          <th className="px-2 py-1 text-left text-xs font-semibold text-gray-500">Min Qty</th>
                          <th className="px-2 py-1 text-left text-xs font-semibold text-gray-500">Unit Cost</th>
                          <th className="px-2 py-1 text-left text-xs font-semibold text-gray-500">Variant ID</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(data.cost as CostData).qty_breaks!.map((b, i) => (
                          <tr key={i} className="border-b border-gray-100 dark:border-gray-800">
                            <td className="px-2 py-1">{b.min_qty}</td>
                            <td className="px-2 py-1">{b.unit_cost != null ? `$${b.unit_cost.toFixed(2)}` : "—"}</td>
                            <td className="px-2 py-1">{b.variant_item_id ?? "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </DataSection>
          )}
        </div>

        {/* Image Column (40%) */}
        <div className="w-[40%]">
          <div className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden h-full">
            <div className="p-4 bg-white dark:bg-slate-900">
              <ImagePanel
                images={data.metadata?.images}
                itemId={data.id}
                onImagesChange={handleImagesChange}
                editable={isAdmin}
              />
            </div>
          </div>
        </div>
      </div>

      {/* 4. Inventory Status - expanded (horizontal layout) */}
      {data.quantity && (
        <DataSection title="Inventory Status" icon={<FaWarehouse className="w-4 h-4" />} defaultOpen={true} noTable>
          <InventoryGrid quantity={data.quantity} />
        </DataSection>
      )}

      {/* 5. Bill of Materials - collapsed */}
      {data.id && (
        <BOMSection itemId={data.id} defaultOpen={false} />
      )}

      {/* Panels 6-8 (Linkages, Actions, Comments) moved to tab navigation */}

      {/* 9. Flags & Settings - collapsed */}
      {data.flags && Object.keys(data.flags).length > 0 && (
        <DataSection title="Flags & Settings" icon={<FaCog className="w-4 h-4" />} defaultOpen={false}>
          <TableBody>
            {Object.entries(data.flags).map(([key, value]) => (
              <DataRow
                key={key}
                label={key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                value={value}
              />
            ))}
          </TableBody>
        </DataSection>
      )}

      {/* 10. GL Accounts - collapsed */}
      {data.gls && (
        <DataSection title="GL Accounts" icon={<FaListAlt className="w-4 h-4" />} defaultOpen={false} noTable>
          <DataFieldGrid columns={4}>
            <DataField label="inventory" value={(data.gls as GlsData).inventory} />
            <DataField label="cogs" value={(data.gls as GlsData).cogs} />
            <DataField label="revenue" value={(data.gls as GlsData).revenue} />
            <DataField label="variance" value={(data.gls as GlsData).variance} />
          </DataFieldGrid>
        </DataSection>
      )}

      {/* 11. Tax Information - collapsed */}
      {data.tax_code && (
        <DataSection title="Tax Information" icon={<FaFileInvoice className="w-4 h-4" />} defaultOpen={false} noTable>
          <DataFieldGrid columns={3}>
            <DataField label="code" value={(data.tax_code as TaxCodeData).code} />
            <DataField label="jurisdiction" value={(data.tax_code as TaxCodeData).jurisdiction} />
            <DataField label="category" value={(data.tax_code as TaxCodeData).category} />
          </DataFieldGrid>
          <DataFieldGrid columns={2}>
            <DataField label="rate" value={(data.tax_code as TaxCodeData).rate} />
            <DataField label="exemptions" value={(data.tax_code as TaxCodeData).exemptions?.join(", ")} />
          </DataFieldGrid>
          {/* Jurisdiction Params */}
          {(data.tax_code as TaxCodeData).jurisdiction_params && (data.tax_code as TaxCodeData).jurisdiction_params!.length > 0 && (
            <div className="mt-2">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Jurisdiction Params</p>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-700">
                      <th className="px-2 py-1 text-left text-xs font-semibold text-gray-500">Jurisdiction</th>
                      <th className="px-2 py-1 text-left text-xs font-semibold text-gray-500">Kind</th>
                      <th className="px-2 py-1 text-left text-xs font-semibold text-gray-500">Effective From</th>
                      <th className="px-2 py-1 text-left text-xs font-semibold text-gray-500">Effective To</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.tax_code as TaxCodeData).jurisdiction_params!.map((jp, i) => (
                      <tr key={i} className="border-b border-gray-100 dark:border-gray-800">
                        <td className="px-2 py-1">{jp.jurisdiction}</td>
                        <td className="px-2 py-1">{jp.kind ?? "—"}</td>
                        <td className="px-2 py-1">{jp.effective_from ?? "—"}</td>
                        <td className="px-2 py-1">{jp.effective_to ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </DataSection>
      )}

      {/* 11b. Catalog - collapsed */}
      {data.catalog && (
        <DataSection title="Catalog" icon={<FaListAlt className="w-4 h-4" />} defaultOpen={false} noTable>
          {/* Categories */}
          {(data.catalog as CatalogData).categories && (data.catalog as CatalogData).categories!.length > 0 && (
            <DataFieldGrid columns={2}>
              <div className="sm:col-span-2">
                <DataField label="categories" value={(data.catalog as CatalogData).categories!.join(" > ")} />
              </div>
            </DataFieldGrid>
          )}
          {/* Web */}
          {(data.catalog as CatalogData).web && (
            <DataFieldGrid columns={4}>
              <DataField label="web.slug" value={(data.catalog as CatalogData).web?.slug} />
              <DataField label="web.title" value={(data.catalog as CatalogData).web?.title} />
              <DataField label="web.short" value={(data.catalog as CatalogData).web?.short} />
              <DataField label="web.seo" value={(data.catalog as CatalogData).web?.seo ? JSON.stringify((data.catalog as CatalogData).web!.seo) : null} />
            </DataFieldGrid>
          )}
          {/* Attributes */}
          {(data.catalog as CatalogData).attributes && Object.keys((data.catalog as CatalogData).attributes!).length > 0 && (
            <div className="mt-2">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Attributes</p>
              <dl className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1 text-sm">
                {Object.entries((data.catalog as CatalogData).attributes!).map(([k, v]) => (
                  <div key={k} className="flex items-baseline gap-1">
                    <dt className="text-xs font-mono text-gray-500 dark:text-gray-400">{k}:</dt>
                    <dd className="text-gray-900 dark:text-white">{String(v)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
          {/* Catalog Flags */}
          {(data.catalog as CatalogData).flags && Object.keys((data.catalog as CatalogData).flags!).length > 0 && (
            <div className="mt-2">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Flags</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries((data.catalog as CatalogData).flags!).map(([k, v]) => (
                  <Badge key={k} color={v ? "success" : "light"}>{k}</Badge>
                ))}
              </div>
            </div>
          )}
        </DataSection>
      )}

      {/* Panels 12-14 (Metadata, Prefs, Refs) moved to tab navigation */}

      {/* 15. Record Information - collapsed */}
      <DataSection title="Record Information" icon={<FaCog className="w-4 h-4" />} defaultOpen={false}>
        <TableBody>
          <DataRow label="Record ID" value={data.id} />
          <DataRow label="Row Version" value={data.row_version} />
          <DataRow label="Created" value={formatDate(data.dt_created)} />
          <DataRow label="Last Modified" value={formatDate(data.dt_modified)} />
          <DataRow label="Active" value={data.is_active} />
        </TableBody>
      </DataSection>

      {/* Panel 16 (Raw Data) moved to tab navigation */}
    </div>
  );
}

// ============================================================================
// Field Configuration
// ============================================================================

const ITEM_DETAIL_FIELDS = [
  "name",
  "sku",
  "qr_code",
  "kind",
  "uom",
  "base_uom",
  "description",
  "specification_id",
  "price",
  "cost",
  "quantity",
  "flags",
  "gls",
  "tax_code",
  "catalog",
  "is_active",
] as const;

// ============================================================================
// Form ↔ Data helpers
// ============================================================================

/** Map server data → flat form values */
function dataToFormValues(d: ItemData | null): ItemFormValues {
  if (!d) {
    return {
      name: "", sku: "", qr_code: "", kind: "physical",
      uom: "", base_uom: "", description: "",
      specification_id: undefined, is_active: true,
      price_base: undefined, price_msrp: undefined, price_currency: "USD",
      cost_standard: undefined, cost_last: undefined, cost_avg: undefined,
      cost_landed: undefined, cost_currency: "USD",
      qty_on_hand: undefined, qty_allocated: undefined, qty_available: undefined,
      qty_on_so: undefined, qty_on_po: undefined, qty_on_p: undefined,
      qty_on_reciept: undefined, qty_on_in: undefined, qty_on_wo: undefined,
      flag_back_order_allowed: false, flag_discountable: false, flag_linked: false,
      flag_not_tracked: false, flag_pacing: false, flag_print_suppressed: false,
      flag_serialized: false, flag_tally_by_type: false,
      gls_inventory: "", gls_cogs: "", gls_revenue: "", gls_variance: "",
      tax_code_code: "", tax_code_jurisdiction: "", tax_code_category: "",
      tax_code_rate: undefined,
      catalog_categories: "", catalog_web_slug: "", catalog_web_title: "",
      catalog_web_short: "",
    };
  }
  const p = typeof d.price === "object" ? (d.price as PriceData) : null;
  const c = (d.cost as CostData) || {};
  const q = (d.quantity as QuantityData) || {};
  const f = (d.flags as FlagsData) || {};
  const g = (d.gls as GlsData) || {};
  const t = (d.tax_code as TaxCodeData) || {};
  const cat = (d.catalog as CatalogData) || {};
  return {
    name: d.name || "", sku: d.sku || "", qr_code: d.qr_code || "",
    kind: d.kind || "physical", uom: d.uom || "", base_uom: d.base_uom || "",
    description: d.description || "",
    specification_id: d.specification_id,
    is_active: d.is_active ?? true,
    price_base: p?.base ?? (typeof d.price === "number" ? d.price : undefined),
    price_msrp: p?.msrp, price_currency: p?.currency || "USD",
    cost_standard: c.standard, cost_last: c.last, cost_avg: c.avg,
    cost_landed: c.landed, cost_currency: c.currency || "USD",
    qty_on_hand: q.on_hand, qty_allocated: q.allocated, qty_available: q.available,
    qty_on_so: q.on_so, qty_on_po: q.on_po, qty_on_p: q.on_p,
    qty_on_reciept: q.on_reciept, qty_on_in: q.on_in, qty_on_wo: q.on_wo,
    flag_back_order_allowed: f.back_order_allowed ?? false,
    flag_discountable: f.discountable ?? false,
    flag_linked: f.linked ?? false,
    flag_not_tracked: f.not_tracked ?? false,
    flag_pacing: f.pacing ?? false,
    flag_print_suppressed: f.print_suppressed ?? false,
    flag_serialized: f.serialized ?? false,
    flag_tally_by_type: f.tally_by_type ?? false,
    gls_inventory: g.inventory || "", gls_cogs: g.cogs || "",
    gls_revenue: g.revenue || "", gls_variance: g.variance || "",
    tax_code_code: t.code || "", tax_code_jurisdiction: t.jurisdiction || "",
    tax_code_category: t.category || "", tax_code_rate: t.rate,
    catalog_categories: (cat.categories || []).join(", "),
    catalog_web_slug: cat.web?.slug || "",
    catalog_web_title: cat.web?.title || "",
    catalog_web_short: cat.web?.short || "",
  };
}

/** Reconstruct nested API payload from flat form values */
function formValuesToPayload(fd: ItemFormValues, orig: ItemData | null): Record<string, any> {
  return {
    name: fd.name, sku: fd.sku, qr_code: fd.qr_code, kind: fd.kind,
    uom: fd.uom, base_uom: fd.base_uom, description: fd.description,
    specification_id: fd.specification_id, is_active: fd.is_active,
    price: {
      ...(typeof orig?.price === "object" ? orig.price : {}),
      base: fd.price_base, msrp: fd.price_msrp, currency: fd.price_currency,
    },
    cost: {
      ...(orig?.cost || {}),
      standard: fd.cost_standard, last: fd.cost_last, avg: fd.cost_avg,
      landed: fd.cost_landed, currency: fd.cost_currency,
    },
    quantity: {
      ...(orig?.quantity || {}),
      on_hand: fd.qty_on_hand, allocated: fd.qty_allocated, available: fd.qty_available,
      on_so: fd.qty_on_so, on_po: fd.qty_on_po, on_p: fd.qty_on_p,
      on_reciept: fd.qty_on_reciept, on_in: fd.qty_on_in, on_wo: fd.qty_on_wo,
    },
    flags: {
      ...(orig?.flags || {}),
      back_order_allowed: fd.flag_back_order_allowed, discountable: fd.flag_discountable,
      linked: fd.flag_linked, not_tracked: fd.flag_not_tracked,
      pacing: fd.flag_pacing, print_suppressed: fd.flag_print_suppressed,
      serialized: fd.flag_serialized, tally_by_type: fd.flag_tally_by_type,
    },
    gls: {
      ...(orig?.gls || {}),
      inventory: fd.gls_inventory, cogs: fd.gls_cogs,
      revenue: fd.gls_revenue, variance: fd.gls_variance,
    },
    tax_code: {
      ...(orig?.tax_code || {}),
      code: fd.tax_code_code, jurisdiction: fd.tax_code_jurisdiction,
      category: fd.tax_code_category, rate: fd.tax_code_rate,
    },
    catalog: {
      ...(orig?.catalog || {}),
      categories: fd.catalog_categories
        ? fd.catalog_categories.split(",").map((s: string) => s.trim()).filter(Boolean)
        : (orig?.catalog as CatalogData)?.categories || [],
      web: {
        ...((orig?.catalog as CatalogData)?.web || {}),
        slug: fd.catalog_web_slug, title: fd.catalog_web_title, short: fd.catalog_web_short,
      },
    },
  };
}

// ============================================================================
// Main Component
// ============================================================================

export default function ItemDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
  id: idProp,
  recordId,
}: ItemAddProps & { id?: string | number; recordId?: string | number }) {
  const dispatch = useDispatch();
  const location = useLocation();
  const params = useParams<{ id?: string }>();
  const [searchParams] = useSearchParams();
  const routeState = (location.state as any) || {};

  // Get ID from multiple sources (in priority order):
  // 1. Direct id/recordId prop (from WcapiRouteHandler)
  // 2. Path params (e.g., /item/22)
  // 3. Search params (e.g., /wcapi/get/?model_name=item&id=22)
  // 4. Route state (e.g., navigate with state)
  // 5. dataProp?.id (passed directly)
  const urlId = idProp || recordId || params.id || searchParams.get("id") || routeState.data?.id || dataProp?.id;
  const itemIdFromUrl = urlId ? (typeof urlId === 'number' ? urlId : parseInt(String(urlId), 10)) : null;
  
  console.log('[ItemDetail] ID resolution:', { 
    idProp,
    recordId,
    'params.id': params.id, 
    'searchParams.id': searchParams.get("id"), 
    'routeState.data?.id': routeState.data?.id,
    'dataProp?.id': dataProp?.id,
    itemIdFromUrl 
  });
  
  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const initialData = dataProp || routeState.data || null;
  
  // State for fetched data (when navigating via URL with id param)
  const [fetchedData, setFetchedData] = useState<ItemData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  // Use fetched data if available and matches URL id, otherwise use prop/state data
  const data: ItemData | null = fetchedData || initialData;
  
  // The actual item ID - USE THE LOADED DATA'S ID as the source of truth
  const activeItemId = data?.id || itemIdFromUrl || null;
  
  console.log('[ItemDetail] Data check:', {
    itemIdFromUrl,
    'data?.id': data?.id,
    'initialData?.id': initialData?.id,
    'fetchedData?.id': fetchedData?.id,
    activeItemId,
  });
  
  // Fetch item data when URL id doesn't match current data
  useEffect(() => {
    if (itemIdFromUrl && itemIdFromUrl !== fetchedData?.id) {
      if (initialData?.id === itemIdFromUrl) {
        console.log('[ItemDetail] initialData matches URL id, no fetch needed');
        return;
      }
      
      setIsLoading(true);
      console.log('[ItemDetail] Fetching item:', itemIdFromUrl);
      getRecord("item", itemIdFromUrl)
        .then((result) => {
          console.log('[ItemDetail] Fetched item:', result);
          setFetchedData(result?.record || result);
        })
        .catch((err) => {
          console.error('[ItemDetail] Failed to fetch item:', err);
          dispatch(showToast({ message: "Failed to load item", type: "error" }));
        })
        .finally(() => setIsLoading(false));
    }
  }, [itemIdFromUrl, initialData?.id, fetchedData?.id, dispatch]);
  
  // Detail pages always open in edit mode
  const [effectiveMode, setEffectiveMode] = useState<"add" | "edit" | "view">(mode === "add" ? "add" : "edit");
  const [isSaving, setIsSaving] = useState(false);
  
  // Tab navigation
  const { activeTab, setActiveTab } = useDetailTabs("item_detail", "actions", [
    "actions", "comments", "documents", "raw",
  ]);

  const tabs: TabConfig[] = useMemo(
    () => [
      { id: "actions", label: "Actions", icon: <CheckSquare size={14} /> },
      { id: "comments", label: "Comments", icon: <MessageSquare size={14} />, badge: data?.comments?.length },
      { id: "documents", label: "Documents", icon: <FileIcon size={14} />, badge: data?.refs?.links?.document?.length },
      { id: "raw", label: "Raw", icon: <Code size={14} /> },
    ],
    [data],
  );

  // Sync effectiveMode when mode prop changes
  useEffect(() => {
    setEffectiveMode(mode === "add" ? "add" : "edit");
  }, [mode]);
  
  // Field access control
  const itemFieldNames = useMemo(() => ITEM_DETAIL_FIELDS.slice(), []);
  const {
    isAdmin,
    isFieldVisible,
    isFieldReadOnly,
  } = useDetailFieldAccess("item", itemFieldNames);

  const isFieldDisabled = (fieldName: string) => {
    if (effectiveMode === "view") return true;
    if (!isAdmin && isFieldReadOnly(fieldName)) return true;
    return false;
  };

  const shouldRenderField = (fieldName: string) => {
    if (isAdmin) return true;
    return isFieldVisible(fieldName);
  };

  // React Hook Form
  const {
    register,
    handleSubmit,
    reset,
    control,
    formState: { errors },
  } = useForm<any>({
    resolver: zodResolver(itemSchema),
    defaultValues: {
      name: "",
      description: "",
      price: undefined,
      category: "",
      price_base: undefined,
      price_msrp: undefined,
      price_retail: undefined,
      price_wholesale: undefined,
      price_distributor: undefined,
      price_sample: undefined,
      price_currency: undefined,
      price_qty_breaks_json: JSON.stringify([]),
        // Cost fields (mirror Pricing inputs)
        cost_standard: undefined,
        cost_last: undefined,
        cost_avg: undefined,
        cost_landed: undefined,
        cost_currency: undefined,
        cost_qty_breaks_json: JSON.stringify([]),
        cost_components_json: JSON.stringify({}),
        // Catalog fields
        catalog_categories: "",
        catalog_web_slug: "",
        catalog_web_title: "",
        catalog_web_short: "",
        catalog_attributes_json: JSON.stringify({}),
        catalog_flags_json: JSON.stringify({}),
        // Tax fields
        tax_code_code: "",
        tax_code_jurisdiction: "",
        tax_code_category: "",
        tax_code_rate: undefined,
        tax_code_exemptions: "",
        tax_code_jurisdiction_params_json: JSON.stringify([]),
      price_history_json: JSON.stringify([]),
    },
  });

  // Load Edit Data
  useEffect(() => {
    if (!data) {
      reset({});
      return;
    }

    const priceObj = typeof data.price === "number" ? { base: data.price } : (data.price as PriceData) || {};
    const costObj = (data.cost as CostData) || {};

    const taxObj = (data.tax_code as TaxCodeData) || {};

    const normalizedItem = {
      name: data.name || "",
      description: data.description || "",
      price: typeof data.price === "number" ? data.price : priceObj.base,
      category: data.category || "",
      price_base: priceObj.base,
      price_msrp: priceObj.msrp,
      price_retail: priceObj.retail,
      price_wholesale: priceObj.wholesale,
      price_distributor: priceObj.distributor,
      price_sample: priceObj.sample,
      price_currency: priceObj.currency,
      price_qty_breaks_json: JSON.stringify(priceObj.qty_breaks || []),
      price_history_json: JSON.stringify(priceObj.history || []),
      // Cost fields
      cost_standard: costObj.standard,
      cost_last: costObj.last,
      cost_avg: costObj.avg,
      cost_landed: costObj.landed,
      cost_currency: costObj.currency,
      cost_qty_breaks_json: JSON.stringify(costObj.qty_breaks || []),
      cost_components_json: JSON.stringify(costObj.components || {}),
      // Catalog fields
      catalog_categories: (data.catalog as CatalogData)?.categories ? (data.catalog as CatalogData).categories!.join(", ") : "",
      catalog_web_slug: (data.catalog as CatalogData)?.web?.slug || "",
      catalog_web_title: (data.catalog as CatalogData)?.web?.title || "",
      catalog_web_short: (data.catalog as CatalogData)?.web?.short || "",
      catalog_attributes_json: JSON.stringify((data.catalog as CatalogData)?.attributes || {}),
      catalog_flags_json: JSON.stringify((data.catalog as CatalogData)?.flags || {}),
      // Tax fields
      tax_code_code: taxObj.code || "",
      tax_code_jurisdiction: taxObj.jurisdiction || "",
      tax_code_category: taxObj.category || "",
      tax_code_rate: taxObj.rate,
      tax_code_exemptions: taxObj.exemptions ? taxObj.exemptions.join(", ") : "",
      tax_code_jurisdiction_params_json: JSON.stringify(taxObj.jurisdiction_params || []),
    };

    reset(normalizedItem);
  }, [data, reset]);

  // Form submission
  const onSubmit = async (formData: any) => {
    try {
      setIsSaving(true);
      // Build price object from individual form fields (all optional)
      const priceObj: any = {};
      if (formData.price_base !== undefined && formData.price_base !== null && formData.price_base !== "") priceObj.base = Number(formData.price_base);
      if (formData.price_msrp !== undefined && formData.price_msrp !== null && formData.price_msrp !== "") priceObj.msrp = Number(formData.price_msrp);
      if (formData.price_retail !== undefined && formData.price_retail !== null && formData.price_retail !== "") priceObj.retail = Number(formData.price_retail);
      if (formData.price_wholesale !== undefined && formData.price_wholesale !== null && formData.price_wholesale !== "") priceObj.wholesale = Number(formData.price_wholesale);
      if (formData.price_distributor !== undefined && formData.price_distributor !== null && formData.price_distributor !== "") priceObj.distributor = Number(formData.price_distributor);
      if (formData.price_sample !== undefined && formData.price_sample !== null && formData.price_sample !== "") priceObj.sample = Number(formData.price_sample);
      if (formData.price_currency) priceObj.currency = formData.price_currency;
      try {
        if (formData.price_qty_breaks_json) {
          const parsed = JSON.parse(formData.price_qty_breaks_json);
          if (Array.isArray(parsed)) priceObj.qty_breaks = parsed;
        }
      } catch (e) {
        // ignore parse errors
      }

      // Build cost object from individual form fields (all optional)
      const costObj: any = {};
      if (formData.cost_standard !== undefined && formData.cost_standard !== null && formData.cost_standard !== "") costObj.standard = Number(formData.cost_standard);
      if (formData.cost_last !== undefined && formData.cost_last !== null && formData.cost_last !== "") costObj.last = Number(formData.cost_last);
      if (formData.cost_avg !== undefined && formData.cost_avg !== null && formData.cost_avg !== "") costObj.avg = Number(formData.cost_avg);
      if (formData.cost_landed !== undefined && formData.cost_landed !== null && formData.cost_landed !== "") costObj.landed = Number(formData.cost_landed);
      if (formData.cost_currency) costObj.currency = formData.cost_currency;
      try {
        if (formData.cost_qty_breaks_json) {
          const parsed = JSON.parse(formData.cost_qty_breaks_json);
          if (Array.isArray(parsed)) costObj.qty_breaks = parsed;
        }
      } catch (e) {
        // ignore parse errors
      }
      try {
        if (formData.cost_components_json) {
          const parsed = JSON.parse(formData.cost_components_json);
          if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) costObj.components = parsed;
        }
      } catch (e) {
        // ignore parse errors
      }
      // Build catalog object from form fields
      const catalogObj: any = {};
      if (formData.catalog_categories) {
        catalogObj.categories = String(formData.catalog_categories)
          .split(",")
          .map((s: string) => s.trim())
          .filter(Boolean);
      }
      const webObj: any = {};
      if (formData.catalog_web_slug) webObj.slug = formData.catalog_web_slug;
      if (formData.catalog_web_title) webObj.title = formData.catalog_web_title;
      if (formData.catalog_web_short) webObj.short = formData.catalog_web_short;
      if (Object.keys(webObj).length > 0) catalogObj.web = webObj;
      try {
        if (formData.catalog_attributes_json) {
          const parsed = JSON.parse(formData.catalog_attributes_json);
          if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) catalogObj.attributes = parsed;
        }
      } catch (e) {
        // ignore parse errors
      }
      try {
        if (formData.catalog_flags_json) {
          const parsed = JSON.parse(formData.catalog_flags_json);
          if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) catalogObj.flags = parsed;
        }
      } catch (e) {
        // ignore parse errors
      }
      // Build tax_code object from form fields
      const taxCodeObj: any = {};
      if (formData.tax_code_code) taxCodeObj.code = formData.tax_code_code;
      if (formData.tax_code_jurisdiction) taxCodeObj.jurisdiction = formData.tax_code_jurisdiction;
      if (formData.tax_code_category) taxCodeObj.category = formData.tax_code_category;
      if (formData.tax_code_rate !== undefined && formData.tax_code_rate !== null && formData.tax_code_rate !== "") taxCodeObj.rate = Number(formData.tax_code_rate);
      if (formData.tax_code_exemptions) {
        taxCodeObj.exemptions = String(formData.tax_code_exemptions).split(',').map((s: string) => s.trim()).filter(Boolean);
      }
      try {
        if (formData.tax_code_jurisdiction_params_json) {
          const parsed = JSON.parse(formData.tax_code_jurisdiction_params_json);
          if (Array.isArray(parsed)) taxCodeObj.jurisdiction_params = parsed;
        }
      } catch (e) {
        // ignore parse errors
      }
      try {
        if (formData.price_history_json) {
          const parsed = JSON.parse(formData.price_history_json);
          if (Array.isArray(parsed)) priceObj.history = parsed;
        }
      } catch (e) {
        // ignore parse errors
      }

      const payload: any = {
        ...formData,
        ...(mode === "edit" && data?.id ? { id: data.id } : {}),
      };

      // Remove transient form-only fields
      delete payload.price_base;
      delete payload.price_msrp;
      delete payload.price_retail;
      delete payload.price_wholesale;
      delete payload.price_distributor;
      delete payload.price_sample;
      delete payload.price_currency;
      delete payload.price_qty_breaks_json;
      delete payload.price_history_json;

      // Remove transient cost form-only fields
      delete payload.cost_standard;
      delete payload.cost_last;
      delete payload.cost_avg;
      delete payload.cost_landed;
      delete payload.cost_currency;
      delete payload.cost_qty_breaks_json;
      delete payload.cost_components_json;
      // Remove transient catalog form-only fields
      delete payload.catalog_categories;
      delete payload.catalog_attributes_json;
      delete payload.catalog_flags_json;
      delete payload.catalog_web_slug;
      delete payload.catalog_web_title;
      delete payload.catalog_web_short;
      // Remove transient tax fields
      delete payload.tax_code_code;
      delete payload.tax_code_jurisdiction;
      delete payload.tax_code_category;
      delete payload.tax_code_rate;
      delete payload.tax_code_exemptions;
      delete payload.tax_code_jurisdiction_params_json;

      if (Object.keys(priceObj).length > 0) {
        payload.price = priceObj;
      }

      if (Object.keys(costObj).length > 0) {
        payload.cost = costObj;
      }

      if (Object.keys(catalogObj).length > 0) {
        payload.catalog = {
          ...(data?.catalog || {}),
          ...catalogObj,
          web: {
            ...((data?.catalog as CatalogData)?.web || {}),
            ...(catalogObj.web || {}),
          },
        };
      }

      if (Object.keys(taxCodeObj).length > 0) {
        payload.tax_code = {
          ...(data?.tax_code || {}),
          ...taxCodeObj,
        };
      }

      const res = mode === "add"
        ? await createItem(payload as any)
        : await updateItem({ ...payload, id: data!.id! } as any);

      if (res) {
        dispatch(showToast({ 
          message: `Item ${mode === "add" ? "created" : "updated"} successfully`, 
          type: "success" 
        }));
        if (onSaved) onSaved();
        if (effectiveMode === "add" && onCancelInline) {
          onCancelInline();
        }
      }
    } catch (error: unknown) {
      if (error instanceof Error) {
        dispatch(showToast({ message: error.message, type: "error" }));
      }
    } finally {
      setIsSaving(false);
    }
  };

  // Toolbar handlers
  const handleSave = () => {
    handleSubmit(onSubmit)();
  };

  const handleEdit = () => {
    setEffectiveMode("edit");
  };

  const handleCancel = () => {
    if (inline && onCancelInline) {
      onCancelInline();
    } else if (effectiveMode === "add") {
      onCancelInline?.();
    } else {
      // Reset form to original data
      reset(dataToFormValues(data));
    }
  };

  // Show loading state while fetching
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <span className="ml-2 text-gray-600 dark:text-gray-400">Loading item...</span>
      </div>
    );
  }

  // View mode - show data display
  if (effectiveMode === "view" && data) {
    return (
      <>
        {/* Header */}
        <SimpleDetailHeader
          entityName="Item"
          recordId={data?.id}
          recordName={data?.name || data?.sku}
          mode={effectiveMode}
          backUrl={inline ? undefined : "/products/items"}
        />

        {/* Toolbar */}
        <SimpleDetailToolbar
          mode={effectiveMode}
          isSaving={isSaving}
          onSave={handleSave}
          onCancel={handleCancel}
          onEdit={handleEdit}
        />

        <ComponentCard>
          <ItemDataView data={data} isAdmin={isAdmin} />
        </ComponentCard>

        {effectiveMode === "view" && data && (
          <div className="mt-4 space-y-0">
            <ScalarCard
              title="Item Scalars"
              icon={<FaBox size={14} />}
              fields={[
                { label: "name", value: data.name },
                { label: "sku", value: data.sku },
                { label: "qr_code", value: data.qr_code },
                { label: "kind", value: data.kind },
                { label: "uom", value: data.uom },
                { label: "base_uom", value: data.base_uom },
                { label: "specification_id", value: data.specification_id },
                { label: "description", value: data.description },
              ]}
              columns={3}
            />
            <JsonCard title="Price" icon={<FaDollarSign size={14} />} fieldName="price" data={data.price} />
            <JsonCard title="Cost" icon={<FaDollarSign size={14} />} fieldName="cost" data={data.cost} />
            <JsonCard title="GLs" icon={<FaCalculator size={14} />} fieldName="gls" data={data.gls} />
            <JsonCard title="Tax Code" icon={<FaFileInvoice size={14} />} fieldName="tax_code" data={data.tax_code} />
            <JsonCard title="Catalog" icon={<FaListAlt size={14} />} fieldName="catalog" data={data.catalog} />
            <BaseModelCards data={data as Record<string, unknown>} />
          </div>
        )}

        {/* Tab Navigation */}
        {data?.id && (
          <>
            <DetailTabs
              entityType="item_detail"
              activeTab={activeTab}
              onTabChange={setActiveTab}
              standardTabs={[]}
              additionalTabs={tabs}
            />
            <div className="mt-4">
              {activeTab === "actions" && (
                <ActionsPanel entityType="item" entityId={data.id} data={data?.actions?.items || data?.actions} isEditing={false} />
              )}
              {activeTab === "comments" && (
                <CommentsPanel entityType="item" entityId={data.id} comments={data?.comments} isEditing={false} />
              )}
              {activeTab === "documents" && (
                <DocumentsPanel parent_model="item" parentId={data.id} data={data?.refs?.links?.document} isEditing={false} />
              )}
              {activeTab === "raw" && (
                <JsonFieldEditor label="Full Item JSON" value={data} readonly defaultExpanded maxHeight="600px" />
              )}
            </div>
          </>
        )}
      </>
    );
  }

  // Edit/Add mode - show form
  return (
    <>
      {/* Header */}
      <SimpleDetailHeader
        entityName="Item"
        recordId={data?.id}
        recordName={data?.name || data?.sku}
        mode={effectiveMode}
        backUrl={inline ? undefined : "/products/items"}
      />

      {/* Toolbar */}
      <SimpleDetailToolbar
        mode={effectiveMode}
        isSaving={isSaving}
        onSave={handleSave}
        onCancel={handleCancel}
        onEdit={handleEdit}
      />

      <ComponentCard>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">

          {/* ── 1. Identity ────────────────────────────────────────── */}
          <Section title="Identity" icon={<FaBox className="w-4 h-4" />} defaultExpanded={true}>
            {shouldRenderField("name") && (
              <FieldRow label="Name" htmlFor="name" error={errors.name?.message as string | undefined} required>
                <Input
                  type="text"
                  id="name"
                  placeholder="Item name"
                  {...register("name")}
                  error={!!errors.name?.message}
                  disabled={isFieldDisabled("name")}
                />
              </FieldRow>
            )}

            {shouldRenderField("category") && (
              <FieldRow label="Category" htmlFor="category" error={errors.category?.message as string | undefined} required>
                <Input
                  type="text"
                  id="category"
                  placeholder="Category"
                  {...register("category")}
                  error={!!errors.category?.message}
                  disabled={isFieldDisabled("category")}
                />
              </FieldRow>
            )}

            {shouldRenderField("description") && (
              <FieldRow label="Description" htmlFor="description" error={errors.description?.message as string | undefined} required>
                <Input
                  type="text"
                  id="description"
                  placeholder="Description"
                  {...register("description")}
                  error={!!errors.description?.message}
                  disabled={isFieldDisabled("description")}
                />
              </FieldRow>
            )}
            {shouldRenderField("kind") && (
              <FieldRow label="Kind" htmlFor="kind">
                <Controller name="kind" control={control} render={({ field }) => (
                  <Select value={field.value ?? "physical"} onChange={field.onChange} disabled={isFieldDisabled("kind")}
                    options={[{ value: "physical", label: "Physical" }, { value: "service", label: "Service" }, { value: "bundle", label: "Bundle" }]} />
                )} />
              </FieldRow>
            )}
            {shouldRenderField("uom") && (
              <FieldRow label="UOM" htmlFor="uom" hint="Unit of measure">
                <Input type="text" id="uom" placeholder="ea, lb, kg …" {...register("uom")} disabled={isFieldDisabled("uom")} />
              </FieldRow>
            )}
            {shouldRenderField("base_uom") && (
              <FieldRow label="Base UOM" htmlFor="base_uom">
                <Input type="text" id="base_uom" placeholder="Base unit" {...register("base_uom")} disabled={isFieldDisabled("base_uom")} />
              </FieldRow>
            )}
            <div className="lg:col-span-2">
              {shouldRenderField("description") && (
                <FieldRow label="Description" htmlFor="description">
                  <textarea id="description" rows={3} placeholder="Item description" {...register("description")}
                    disabled={isFieldDisabled("description")}
                    className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2 text-sm shadow-theme-xs placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-white/30 dark:focus:border-brand-800" />
                </FieldRow>
              )}
            </div>
            {shouldRenderField("specification_id") && (
              <FieldRow label="Spec ID" htmlFor="specification_id">
                <Input type="number" id="specification_id" placeholder="Specification ID" {...register("specification_id")} disabled={isFieldDisabled("specification_id")} />
              </FieldRow>
            )}
            <FieldRow label="Active" htmlFor="is_active">
              <Controller name="is_active" control={control} render={({ field }) => (
                <Checkbox id="is_active" checked={field.value ?? true} onChange={(c) => field.onChange(c)} disabled={isFieldDisabled("is_active")} label="Item is active" />
              )} />
            </FieldRow>
          </Section>

          {/* Tax Section */}
          <Section title="Tax Information" icon={<FaFileInvoice className="w-4 h-4" />} defaultExpanded={false}>
            <FieldRow label="Tax Code" htmlFor="tax_code_code">
              <Input type="text" id="tax_code_code" {...register("tax_code_code")} disabled={isFieldDisabled("tax_code")} />
            </FieldRow>

            <FieldRow label="Jurisdiction" htmlFor="tax_code_jurisdiction">
              <Input type="text" id="tax_code_jurisdiction" {...register("tax_code_jurisdiction")} disabled={isFieldDisabled("tax_code")} />
            </FieldRow>

            <FieldRow label="Category" htmlFor="tax_code_category">
              <Input type="text" id="tax_code_category" {...register("tax_code_category")} disabled={isFieldDisabled("tax_code")} />
            </FieldRow>

            <FieldRow label="Rate" htmlFor="tax_code_rate">
              <Input type="number" id="tax_code_rate" step="0.01" {...register("tax_code_rate", { valueAsNumber: true })} disabled={isFieldDisabled("tax_code")} />
            </FieldRow>

            <FieldRow label="Exemptions" htmlFor="tax_code_exemptions" hint="Comma-separated exemptions">
              <Input type="text" id="tax_code_exemptions" {...register("tax_code_exemptions")} disabled={isFieldDisabled("tax_code")} />
            </FieldRow>

            <FieldRow label="Jurisdiction Params (JSON)" htmlFor="tax_code_jurisdiction_params_json" hint='JSON array of params'>
              <textarea
                id="tax_code_jurisdiction_params_json"
                {...register("tax_code_jurisdiction_params_json")}
                className="w-full text-sm px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-slate-800 text-gray-900 dark:text-white"
                rows={4}
                disabled={isFieldDisabled("tax_code")}
              />
            </FieldRow>
          </Section>

          {/* Catalog Section */}
          <Section title="Catalog" icon={<FaListAlt className="w-4 h-4" />} defaultExpanded={false}>
            <FieldRow label="Categories" htmlFor="catalog_categories" hint="Comma-separated categories">
              <Input type="text" id="catalog_categories" {...register("catalog_categories")} disabled={isFieldDisabled("catalog")} />
            </FieldRow>

            <FieldRow label="Attributes (JSON)" htmlFor="catalog_attributes_json" hint='JSON object: {"color":"red"}'>
              <textarea
                id="catalog_attributes_json"
                {...register("catalog_attributes_json")}
                className="w-full text-sm px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-slate-800 text-gray-900 dark:text-white"
                rows={4}
                disabled={isFieldDisabled("catalog")}
              />
            </FieldRow>

            <FieldRow label="Web Slug" htmlFor="catalog_web_slug">
              <Input type="text" id="catalog_web_slug" {...register("catalog_web_slug")} disabled={isFieldDisabled("catalog")} />
            </FieldRow>

            <FieldRow label="Web Title" htmlFor="catalog_web_title">
              <Input type="text" id="catalog_web_title" {...register("catalog_web_title")} disabled={isFieldDisabled("catalog")} />
            </FieldRow>

            <FieldRow label="Web Short" htmlFor="catalog_web_short">
              <Input type="text" id="catalog_web_short" {...register("catalog_web_short")} disabled={isFieldDisabled("catalog")} />
            </FieldRow>

            <FieldRow label="Flags (JSON)" htmlFor="catalog_flags_json" hint='JSON object of flags e.g. {"featured":true}'>
              <textarea
                id="catalog_flags_json"
                {...register("catalog_flags_json")}
                className="w-full text-sm px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-slate-800 text-gray-900 dark:text-white"
                rows={3}
                disabled={isFieldDisabled("catalog")}
              />
            </FieldRow>
          </Section>

          {/* 3. Cost Section (mirror Pricing) */}
          <Section
            title="Cost"
            icon={<FaCalculator className="w-4 h-4" />}
            defaultExpanded={true}
          >
            {shouldRenderField("cost") && (
              <>
                <FieldRow label="Standard" htmlFor="cost_standard">
                  <Input
                    type="number"
                    id="cost_standard"
                    placeholder="0.00"
                    step="0.01"
                    {...register("cost_standard", { valueAsNumber: true })}
                    disabled={isFieldDisabled("cost")}
                  />
                </FieldRow>

                <FieldRow label="Last" htmlFor="cost_last">
                  <Input
                    type="number"
                    id="cost_last"
                    placeholder="0.00"
                    step="0.01"
                    {...register("cost_last", { valueAsNumber: true })}
                    disabled={isFieldDisabled("cost")}
                  />
                </FieldRow>

                <FieldRow label="Avg" htmlFor="cost_avg">
                  <Input
                    type="number"
                    id="cost_avg"
                    placeholder="0.00"
                    step="0.01"
                    {...register("cost_avg", { valueAsNumber: true })}
                    disabled={isFieldDisabled("cost")}
                  />
                </FieldRow>

                <FieldRow label="Landed" htmlFor="cost_landed">
                  <Input
                    type="number"
                    id="cost_landed"
                    placeholder="0.00"
                    step="0.01"
                    {...register("cost_landed", { valueAsNumber: true })}
                    disabled={isFieldDisabled("cost")}
                  />
                </FieldRow>

                <FieldRow label="Currency" htmlFor="cost_currency">
                  <Input
                    type="text"
                    id="cost_currency"
                    placeholder="USD"
                    {...register("cost_currency")}
                    disabled={isFieldDisabled("cost")}
                  />
                </FieldRow>

                <FieldRow label="Components (JSON)" htmlFor="cost_components_json" hint='JSON object: {"partA":1.23}'>
                  <textarea
                    id="cost_components_json"
                    {...register("cost_components_json")}
                    className="w-full text-sm px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-slate-800 text-gray-900 dark:text-white"
                    rows={4}
                    disabled={isFieldDisabled("cost")}
                  />
                </FieldRow>

                <FieldRow label="Cost Breaks (JSON)" htmlFor="cost_qty_breaks_json" hint='JSON array: [{"min_qty":1,"unit_cost":1.23}]'>
                  <textarea
                    id="cost_qty_breaks_json"
                    {...register("cost_qty_breaks_json")}
                    className="w-full text-sm px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-slate-800 text-gray-900 dark:text-white"
                    rows={4}
                    disabled={isFieldDisabled("cost")}
                  />
                </FieldRow>
              </>
            )}
          </Section>

          {/* 2. Pricing Section */}
          <Section
            title="Pricing"
            icon={<FaDollarSign className="w-4 h-4" />}
            defaultExpanded={true}
          >
            {shouldRenderField("price") && (
              <>
                <FieldRow label="Base" htmlFor="price_base">
                  <Input
                    type="number"
                    id="price_base"
                    placeholder="0.00"
                    step="0.01"
                    {...register("price_base", { valueAsNumber: true })}
                    disabled={isFieldDisabled("price")}
                  />
                </FieldRow>

                <FieldRow label="MSRP" htmlFor="price_msrp">
                  <Input
                    type="number"
                    id="price_msrp"
                    placeholder="0.00"
                    step="0.01"
                    {...register("price_msrp", { valueAsNumber: true })}
                    disabled={isFieldDisabled("price")}
                  />
                </FieldRow>

                <FieldRow label="Retail" htmlFor="price_retail">
                  <Input
                    type="number"
                    id="price_retail"
                    placeholder="0.00"
                    step="0.01"
                    {...register("price_retail", { valueAsNumber: true })}
                    disabled={isFieldDisabled("price")}
                  />
                </FieldRow>

                <FieldRow label="Wholesale" htmlFor="price_wholesale">
                  <Input
                    type="number"
                    id="price_wholesale"
                    placeholder="0.00"
                    step="0.01"
                    {...register("price_wholesale", { valueAsNumber: true })}
                    disabled={isFieldDisabled("price")}
                  />
                </FieldRow>

                <FieldRow label="Distributor" htmlFor="price_distributor">
                  <Input
                    type="number"
                    id="price_distributor"
                    placeholder="0.00"
                    step="0.01"
                    {...register("price_distributor", { valueAsNumber: true })}
                    disabled={isFieldDisabled("price")}
                  />
                </FieldRow>

                <FieldRow label="Sample" htmlFor="price_sample">
                  <Input
                    type="number"
                    id="price_sample"
                    placeholder="0.00"
                    step="0.01"
                    {...register("price_sample", { valueAsNumber: true })}
                    disabled={isFieldDisabled("price")}
                  />
                </FieldRow>

                <FieldRow label="Currency" htmlFor="price_currency">
                  <Input
                    type="text"
                    id="price_currency"
                    placeholder="USD"
                    {...register("price_currency")}
                    disabled={isFieldDisabled("price")}
                  />
                </FieldRow>

                <FieldRow label="Qty Breaks (JSON)" htmlFor="price_qty_breaks_json" hint='JSON array: [{"min_qty":1,"unit_price":9.99}]'>
                  <textarea
                    id="price_qty_breaks_json"
                    {...register("price_qty_breaks_json")}
                    className="w-full text-sm px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-slate-800 text-gray-900 dark:text-white"
                    rows={4}
                    disabled={isFieldDisabled("price")}
                  />
                </FieldRow>

                <FieldRow label="History (JSON)" htmlFor="price_history_json" hint='JSON array of history objects'>
                  <textarea
                    id="price_history_json"
                    {...register("price_history_json")}
                    className="w-full text-sm px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-slate-800 text-gray-900 dark:text-white"
                    rows={4}
                    disabled={isFieldDisabled("price")}
                  />
                </FieldRow>
              </>
            )}
          </Section>

        </form>
      </ComponentCard>
      
      {/* Tab Navigation */}
      {mode !== "add" && activeItemId && (
        <>
          <DetailTabs
            entityType="item_detail"
            activeTab={activeTab}
            onTabChange={setActiveTab}
            standardTabs={[]}
            additionalTabs={tabs}
          />
          <div className="mt-4">
            {activeTab === "actions" && (
              <ActionsPanel entityType="item" entityId={activeItemId} data={data?.actions?.items || data?.actions} isEditing={effectiveMode !== "view"} onChange={(actions: any) => console.log('Actions updated:', actions)} />
            )}
            {activeTab === "comments" && (
              <CommentsPanel entityType="item" entityId={activeItemId} comments={data?.comments} isEditing={effectiveMode !== "view"} onChange={(comments: any) => console.log('Comments updated:', comments)} />
            )}
            {activeTab === "documents" && (
              <DocumentsPanel parent_model="item" parentId={activeItemId} data={data?.refs?.links?.document} isEditing={effectiveMode !== "view"} />
            )}
            {activeTab === "raw" && (
              <JsonFieldEditor label="Full Item JSON" value={data} readonly defaultExpanded maxHeight="600px" />
            )}
          </div>
        </>
      )}
    </>
  );
}