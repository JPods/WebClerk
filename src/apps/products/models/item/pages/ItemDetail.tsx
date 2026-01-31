import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";
import {
  Table,
  TableBody,
  TableCell,
  TableRow,
} from "../../../../../components/ui/table";
import Badge from "../../../../../components/ui/badge/Badge";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createItem, updateItem, fetchItem } from "../services/itemApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useParams } from "react-router";
import { itemSchema } from "../utils/itemSchema";
import { ItemAddProps } from "../types/itemType";

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
  [key: string]: any;
}

// ============================================================================
// Helper Components
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
      // Format as currency if it looks like a price/cost
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

interface DataSectionProps {
  title: string;
  children: React.ReactNode;
  collapsible?: boolean;
  defaultOpen?: boolean;
}

function DataSection({
  title,
  children,
  collapsible = true,
  defaultOpen = true,
}: DataSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="mb-6">
      <div
        className={`flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800 rounded-t-lg ${
          collapsible ? "cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" : ""
        }`}
        onClick={() => collapsible && setIsOpen(!isOpen)}
      >
        <h3 className="font-semibold text-gray-700 dark:text-gray-200">{title}</h3>
        {collapsible && (
          <svg
            className={`w-5 h-5 text-gray-500 transition-transform ${
              isOpen ? "rotate-180" : ""
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        )}
      </div>
      {isOpen && (
        <div className="border border-t-0 border-gray-200 dark:border-gray-700 rounded-b-lg overflow-hidden">
          <Table>{children}</Table>
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
// View Mode: Data Table Display
// ============================================================================

function ItemDataView({ data }: { data: ItemData }) {
  const formatDate = (timestamp?: number): string => {
    if (!timestamp) return "—";
    return new Date(timestamp).toLocaleString();
  };

  // Extract price value for display
  const getPrice = (price: PriceData | number | undefined): number | undefined => {
    if (typeof price === "number") return price;
    if (typeof price === "object" && price) return price.base ?? price.retail;
    return undefined;
  };

  return (
    <div className="space-y-6">
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

      {/* Basic Information */}
      <DataSection title="Basic Information" defaultOpen={true}>
        <TableBody>
          <DataRow label="Name" value={data.name} highlight />
          <DataRow label="SKU" value={data.sku} />
          <DataRow label="Kind" value={data.kind} />
          <DataRow label="Unit of Measure" value={data.uom} />
          <DataRow label="Category" value={data.category} />
          <DataRow label="Description" value={data.description} />
        </TableBody>
      </DataSection>

      {/* Pricing */}
      <DataSection title="Pricing" defaultOpen={true}>
        <TableBody>
          {typeof data.price === "object" && data.price ? (
            <>
              <DataRow label="Base Price" value={data.price.base} highlight />
              <DataRow label="Retail Price" value={data.price.retail} />
              <DataRow label="Wholesale Price" value={data.price.wholesale} />
              <DataRow label="Sale Price" value={data.price.sale} />
              {data.price.breaks && data.price.breaks.length > 0 && (
                <DataRow
                  label="Price Breaks"
                  value={data.price.breaks
                    .map((b) => `${b.qty}+ @ $${b.price}`)
                    .join(", ")}
                />
              )}
            </>
          ) : (
            <DataRow label="Price" value={getPrice(data.price)} highlight />
          )}
        </TableBody>
      </DataSection>

      {/* Cost */}
      {data.cost && typeof data.cost === "object" && (
        <DataSection title="Cost" defaultOpen={false}>
          <TableBody>
            <DataRow label="Average Cost" value={data.cost.average} />
            <DataRow label="Last Cost" value={data.cost.last} />
            <DataRow label="Standard Cost" value={data.cost.standard} />
            <DataRow label="Landed Cost" value={data.cost.landed} />
          </TableBody>
        </DataSection>
      )}

      {/* Inventory / Quantity - Horizontal Layout */}
      {data.quantity && (
        <DataSection title="Inventory Status" defaultOpen={true}>
          <InventoryGrid quantity={data.quantity} />
        </DataSection>
      )}

      {/* Flags */}
      {data.flags && Object.keys(data.flags).length > 0 && (
        <DataSection title="Flags & Settings" defaultOpen={false}>
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

      {/* GL Accounts */}
      {data.gls && Object.keys(data.gls).length > 0 && (
        <DataSection title="GL Accounts" defaultOpen={false}>
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

      {/* Tax Code */}
      {data.tax_code && Object.keys(data.tax_code).length > 0 && (
        <DataSection title="Tax Information" defaultOpen={false}>
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

      {/* Metadata */}
      <DataSection title="Record Information" defaultOpen={false}>
        <TableBody>
          <DataRow label="Record ID" value={data.id} />
          <DataRow label="Version" value={data.version} />
          <DataRow label="Created" value={formatDate(data.dt_created)} />
          <DataRow label="Last Modified" value={formatDate(data.dt_modified)} />
          <DataRow label="Active" value={data.is_active} />
        </TableBody>
      </DataSection>
    </div>
  );
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
}: ItemAddProps) {
  const dispatch = useDispatch();
  const { id } = useParams<{ id: string }>();
  const [itemData, setItemData] = useState<ItemData | null>(dataProp || null);
  const [loading, setLoading] = useState(false);

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof itemSchema>>({
    resolver: zodResolver(itemSchema),
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;

  // Fetch item data if we have an ID but no data
  useEffect(() => {
    const loadItem = async () => {
      if (id && !dataProp && (mode === "view" || mode === "edit")) {
        setLoading(true);
        try {
          const response = await fetchItem(parseInt(id, 10));
          if (response?.data) {
            setItemData(response.data);
          }
        } catch (error) {
          console.error("Failed to load item:", error);
          dispatch(showToast({ message: "Failed to load item", type: "error" }));
        } finally {
          setLoading(false);
        }
      }
    };
    loadItem();
  }, [id, dataProp, mode, dispatch]);

  useEffect(() => {
    if (mode === "add") {
      reset();
    } else if (data) {
      setItemData(data);
      Object.keys(data).forEach((key: any) => {
        if (data[key] !== undefined) {
          setValue(key, data[key]);
        }
      });
    } else {
      reset({});
    }
  }, [data, reset, setValue, mode]);

  const onSubmit = async (formData: z.infer<typeof itemSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createItem(formData)
          : await updateItem({ ...formData, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Item ${
              mode === "add" ? "created" : "updated"
            } successfully`,
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        }
      }
    } catch (error: any) {
      dispatch(showToast({ message: error.message, type: "error" }));
    }
  };

  // Loading state
  if (loading) {
    return (
      <ComponentCard>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-gray-500 dark:text-gray-400">Loading item...</span>
        </div>
      </ComponentCard>
    );
  }

  // View mode - show data tables
  if (mode === "view" && itemData) {
    return (
      <>
        {!hideBreadcrumb && !inline && (
          <PageBreadcrumb pageTitle="View Item" />
        )}
        <ComponentCard>
          {inline && (
            <div className="flex justify-between items-center mb-4">
              <h3 className="dark:text-white text-lg font-semibold">View Item</h3>
              {onCancelInline && (
                <button
                  type="button"
                  onClick={onCancelInline}
                  className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                >
                  &times;
                </button>
              )}
            </div>
          )}
          <ItemDataView data={itemData} />
        </ComponentCard>
      </>
    );
  }

  // Edit/Add mode - show form
  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Item"
              : mode === "view"
              ? "View Item"
              : "Item Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Item"
                : mode === "view"
                ? "View Item"
                : "Add New Item"}
            </h3>
            {onCancelInline && (
              <button
                type="button"
                onClick={onCancelInline}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                &times;
              </button>
            )}
          </div>
        )}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="name">Name</Label>
              <Input
                type="text"
                id="name"
                placeholder="Item Name"
                {...register("name")}
                error={errors.name && errors.name.message ? true : false}
                hint={errors.name && errors.name.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="category">Category</Label>
              <Input
                type="text"
                id="category"
                placeholder="Category"
                {...register("category")}
                error={errors.category && errors.category.message ? true : false}
                hint={errors.category && errors.category.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div>
            <Label htmlFor="description">Description</Label>
            <Input
              type="text"
              id="description"
              placeholder="Description"
              {...register("description")}
              error={errors.description && errors.description.message ? true : false}
              hint={errors.description && errors.description.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="price">Price</Label>
            <Input
              type="number"
              id="price"
              placeholder="Price"
              {...register("price", { valueAsNumber: true })}
              error={errors.price && errors.price.message ? true : false}
              hint={errors.price && errors.price.message}
              disabled={mode === "view"}
            />
          </div>
          {mode !== "view" && (
            <div className="flex items-center gap-2">
              <button
                type="submit"
                className="flex items-center px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
              >
                {mode === "edit" ? "Update" : "Submit"}
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
    </>
  );
}