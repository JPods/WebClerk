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
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import DetailShell from "@/components/common/DetailShell";
import ComponentCard from "@/components/common/ComponentCard";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
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
import { itemSchema } from "../utils/itemSchema";
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

// Panel Components
import {
  CommentsPanel,
  MetadataPanel,
  RefsPanel,
  PrefsPanel,
  RawDataPanel,
  ActionsPanel,
  LinkagesPanel,
} from "@/apps/common/components/panels";

// ============================================================================
// Types
// ============================================================================

interface QuantityData {
  on_hand?: number;
  allocated?: number;
  available?: number;
  on_so?: number;
  on_po?: number;
  on_p?: number;
  on_wo?: number;
  invoiced?: number;
}

interface PriceData {
  base?: number;
  retail?: number;
  wholesale?: number;
  sale?: number;
  breaks?: Array<{ qty: number; price: number }>;
}

interface CostData {
  average?: number;
  last?: number;
  standard?: number;
  landed?: number;
}

interface ItemData {
  id?: number;
  name?: string;
  sku?: string;
  kind?: string;
  uom?: string;
  description?: string;
  category?: string;
  specification_id?: number;
  price?: PriceData | number;
  cost?: CostData;
  quantity?: QuantityData;
  flags?: Record<string, boolean>;
  gls?: Record<string, string>;
  tax_code?: Record<string, any>;
  catalog?: Record<string, any>;
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
    { label: "On WO", value: quantity.on_wo, highlight: false },
    { label: "Invoiced", value: quantity.invoiced, highlight: false },
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
    if (typeof price === "object" && price) return price.base ?? price.retail;
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
        {/* Row 1: name, sku, ida, uom */}
        <DataFieldGrid columns={4}>
          <DataField label="name" value={data.name} highlight />
          <DataField label="sku" value={data.sku} />
          <DataField label="ida" value={data.id} />
          <DataField label="uom" value={data.uom} />
        </DataFieldGrid>
        {/* Row 2: description (full width) */}
        <DataFieldGrid columns={2}>
          <div className="col-span-2">
            <DataField label="description" value={data.description} />
          </div>
        </DataFieldGrid>
        {/* Row 3: kind, specification_id */}
        <DataFieldGrid columns={2}>
          <DataField label="kind" value={data.kind} />
          <DataField label="specification_id" value={data.specification_id} />
        </DataFieldGrid>
      </DataSection>

      {/* 2. Pricing & Cost with Image - side by side layout */}
      <div className="flex gap-4 mb-4">
        {/* Pricing & Cost Column (60%) */}
        <div className="w-[60%] space-y-4">
          {/* Pricing - expanded */}
          <DataSection title="Pricing" icon={<FaDollarSign className="w-4 h-4" />} defaultOpen={true} noTable>
            {typeof data.price === "object" && data.price ? (
              <DataFieldGrid columns={2}>
                <DataField label=".base" value={data.price.base} highlight isCurrency />
                <DataField label=".retail" value={data.price.retail} isCurrency />
                <DataField label=".wholesale" value={data.price.wholesale} isCurrency />
                <DataField label=".sale" value={data.price.sale} isCurrency />
                {data.price.breaks && data.price.breaks.length > 0 && (
                  <div className="sm:col-span-2">
                    <DataField
                      label=".breaks"
                      value={data.price.breaks
                        .map((b) => `${b.qty}+ @ $${b.price}`)
                        .join(", ")}
                    />
                  </div>
                )}
              </DataFieldGrid>
            ) : (
              <DataFieldGrid columns={2}>
                <DataField label="price" value={getPrice(data.price)} highlight isCurrency />
              </DataFieldGrid>
            )}
          </DataSection>

          {/* Cost - expanded */}
          {data.cost && typeof data.cost === "object" && (
            <DataSection title="Cost" icon={<FaCalculator className="w-4 h-4" />} defaultOpen={true} noTable>
              <DataFieldGrid columns={2}>
                <DataField label=".average" value={data.cost.average} isCurrency />
                <DataField label=".last" value={data.cost.last} isCurrency />
                <DataField label=".standard" value={data.cost.standard} isCurrency />
                <DataField label=".landed" value={data.cost.landed} isCurrency />
              </DataFieldGrid>
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

      {/* 6. Linkages Panel - collapsed */}
      {data.id && (
        <LinkagesPanel
          entityType="item"
          entityId={data.id}
          data={data.refs?.links}
          defaultCollapsed={true}
        />
      )}

      {/* 7. Actions Panel - collapsed */}
      {data.id && (
        <ActionsPanel
          entityType="item"
          entityId={data.id}
          data={data.actions}
          onChange={(actions) => {
            console.log('Actions updated:', actions);
          }}
          defaultCollapsed={true}
        />
      )}

      {/* 8. Comments Panel - collapsed */}
      {data.id && (
        <CommentsPanel
          entityType="item"
          entityId={data.id}
          data={data.comments}
          onChange={(comments) => {
            console.log('Comments updated:', comments);
          }}
          defaultCollapsed={true}
        />
      )}

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
      {data.gls && Object.keys(data.gls).length > 0 && (
        <DataSection title="GL Accounts" icon={<FaListAlt className="w-4 h-4" />} defaultOpen={false}>
          <TableBody>
            {Object.entries(data.gls).map(([key, value]) => (
              <DataRow
                key={key}
                label={key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                value={value}
              />
            ))}
          </TableBody>
        </DataSection>
      )}

      {/* 11. Tax Information - collapsed */}
      {data.tax_code && Object.keys(data.tax_code).length > 0 && (
        <DataSection title="Tax Information" icon={<FaFileInvoice className="w-4 h-4" />} defaultOpen={false}>
          <TableBody>
            {Object.entries(data.tax_code).map(([key, value]) => (
              <DataRow
                key={key}
                label={key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                value={value}
              />
            ))}
          </TableBody>
        </DataSection>
      )}

      {/* 12. Metadata Panel - collapsed (admin only) */}
      {data.id && isAdmin && (
        <MetadataPanel
          entityType="item"
          entityId={data.id}
          data={data.metadata}
          onChange={(metadata) => {
            console.log('Metadata updated:', metadata);
          }}
          defaultCollapsed={true}
        />
      )}

      {/* 13. Prefs Panel - collapsed */}
      {data.id && (
        <PrefsPanel
          entityType="item"
          entityId={data.id}
          data={data.prefs}
          onChange={(prefs) => {
            console.log('Prefs updated:', prefs);
          }}
          defaultCollapsed={true}
        />
      )}

      {/* 14. Refs Panel - collapsed (admin only) */}
      {data.id && isAdmin && (
        <RefsPanel
          entityType="item"
          entityId={data.id}
          data={data.refs}
          onChange={(refs) => {
            console.log('Refs updated:', refs);
          }}
          defaultCollapsed={true}
        />
      )}

      {/* 15. Record Information - collapsed */}
      <DataSection title="Record Information" icon={<FaCog className="w-4 h-4" />} defaultOpen={false}>
        <TableBody>
          <DataRow label="Record ID" value={data.id} />
          <DataRow label="Version" value={data.version} />
          <DataRow label="Created" value={formatDate(data.dt_created)} />
          <DataRow label="Last Modified" value={formatDate(data.dt_modified)} />
          <DataRow label="Active" value={data.is_active} />
        </TableBody>
      </DataSection>

      {/* 16. Raw Data Panel - collapsed (admin only, seldom used) */}
      {data.id && isAdmin && (
        <RawDataPanel
          entityType="item"
          entityId={data.id}
          data={data}
          defaultCollapsed={true}
        />
      )}
    </div>
  );
}

// ============================================================================
// Field Configuration
// ============================================================================

const ITEM_DETAIL_FIELDS = [
  "name",
  "sku",
  "kind",
  "uom",
  "description",
  "category",
  "price",
  "cost",
  "quantity",
  "flags",
  "gls",
  "tax_code",
  "is_active",
] as const;

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
  
  // Allow toggling between view and edit modes
  const [effectiveMode, setEffectiveMode] = useState<"add" | "edit" | "view">(mode);
  
  // Sync effectiveMode when mode prop changes
  useEffect(() => {
    setEffectiveMode(mode);
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
    formState: { errors },
  } = useForm({
    resolver: zodResolver(itemSchema),
    defaultValues: {
      name: "",
      description: "",
      price: 0,
      category: "",
    },
  });

  // Load Edit Data
  useEffect(() => {
    if (!data) {
      reset({});
      return;
    }

    const normalizedItem = {
      name: data.name || "",
      description: data.description || "",
      price: typeof data.price === "number" ? data.price : (data.price as PriceData)?.base || 0,
      category: data.category || "",
    };

    reset(normalizedItem);
  }, [data, reset]);

  // Form submission
  const onSubmit = async (formData: z.infer<typeof itemSchema>) => {
    try {
      const payload = {
        ...formData,
        ...(mode === "edit" && data?.id ? { id: data.id } : {}),
      };

      const res = mode === "add"
        ? await createItem(payload)
        : await updateItem({ ...payload, id: data!.id! });

      if (res) {
        dispatch(showToast({ 
          message: `Item ${mode === "add" ? "created" : "updated"} successfully`, 
          type: "success" 
        }));
        if (onSaved) onSaved();
      }
    } catch (error: unknown) {
      if (error instanceof Error) {
        dispatch(showToast({ message: error.message, type: "error" }));
      }
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
      <DetailShell
        title="Item"
        mode={effectiveMode}
        inline={inline}
        hideBreadcrumb={hideBreadcrumb}
        onCancelInline={onCancelInline}
        card={false}
      >
        <ComponentCard>
          <ItemDataView data={data} isAdmin={isAdmin} />
        </ComponentCard>
      </DetailShell>
    );
  }

  // Edit/Add mode - show form
  return (
    <DetailShell
      title="Item"
      mode={effectiveMode}
      inline={inline}
      hideBreadcrumb={hideBreadcrumb}
      onCancelInline={onCancelInline}
      card={false}
    >
      <ComponentCard>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* 1. Basic Information Section */}
          <Section
            title="Basic Information"
            icon={<FaBox className="w-4 h-4" />}
            defaultExpanded={true}
          >
            {shouldRenderField("name") && (
              <FieldRow label="Name" htmlFor="name" error={errors.name?.message} required>
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
              <FieldRow label="Category" htmlFor="category" error={errors.category?.message} required>
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
              <FieldRow label="Description" htmlFor="description" error={errors.description?.message} required>
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
          </Section>

          {/* 2. Pricing Section */}
          <Section
            title="Pricing"
            icon={<FaDollarSign className="w-4 h-4" />}
            defaultExpanded={true}
          >
            {shouldRenderField("price") && (
              <FieldRow label="Price" htmlFor="price" error={errors.price?.message} required>
                <Input
                  type="number"
                  id="price"
                  placeholder="0.00"
                  step="0.01"
                  {...register("price", { valueAsNumber: true })}
                  error={!!errors.price?.message}
                  disabled={isFieldDisabled("price")}
                />
              </FieldRow>
            )}
          </Section>

          {/* 3. Panels for edit mode (existing record) */}
          {mode !== "add" && activeItemId && (
            <>
              {/* Linkages Panel */}
              <LinkagesPanel
                entityType="item"
                entityId={activeItemId}
                data={data?.refs?.links}
                defaultCollapsed={true}
              />

              {/* Actions Panel */}
              <ActionsPanel
                entityType="item"
                entityId={activeItemId}
                data={data?.actions}
                onChange={(actions) => {
                  console.log('Actions updated:', actions);
                }}
                defaultCollapsed={true}
              />

              {/* Comments Panel */}
              <CommentsPanel
                entityType="item"
                entityId={activeItemId}
                data={data?.comments}
                onChange={(comments) => {
                  console.log('Comments updated:', comments);
                }}
                defaultCollapsed={true}
              />

              {/* Metadata Panel (admin only) */}
              {isAdmin && (
                <MetadataPanel
                  entityType="item"
                  entityId={activeItemId}
                  data={data?.metadata}
                  onChange={(metadata) => {
                    console.log('Metadata updated:', metadata);
                  }}
                  defaultCollapsed={true}
                />
              )}

              {/* Prefs Panel */}
              <PrefsPanel
                entityType="item"
                entityId={activeItemId}
                data={data?.prefs}
                onChange={(prefs) => {
                  console.log('Prefs updated:', prefs);
                }}
                defaultCollapsed={true}
              />

              {/* Refs Panel (admin only) */}
              {isAdmin && (
                <RefsPanel
                  entityType="item"
                  entityId={activeItemId}
                  data={data?.refs}
                  onChange={(refs) => {
                    console.log('Refs updated:', refs);
                  }}
                  defaultCollapsed={true}
                />
              )}

              {/* Raw Data Panel (admin only) */}
              {isAdmin && (
                <RawDataPanel
                  entityType="item"
                  entityId={activeItemId}
                  data={data}
                  defaultCollapsed={true}
                />
              )}
            </>
          )}

          {/* Submit Button */}
          {effectiveMode !== "view" && (
            <div className="flex items-center gap-2 pt-4 border-t border-slate-200 dark:border-slate-700">
              <button
                type="submit"
                className="flex items-center px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
              >
                {mode === "edit" ? "Update" : "Create"}
              </button>
              {inline && onCancelInline && (
                <button
                  type="button"
                  onClick={onCancelInline}
                  className="flex items-center px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
                >
                  Cancel
                </button>
              )}
            </div>
          )}
        </form>
      </ComponentCard>
    </DetailShell>
  );
}