import { useCallback, useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";
import { showToast } from "../../../../../store/slices/toastSlice";

import { salesOrderSchema } from "../utils/salesOrderSchema";
import { createSalesOrder, updateSalesOrder, fetchSalesOrderDetail } from "../services/salesOrderApi";
import { SalesOrderAddProps } from "../types/salesOrderType";
import { AuditTrail } from "../../../../../components/transactions/common/AuditTrail";
import SalesOrderStatus from "../components/SalesOrderStatus";
import type { SalesOrderLine } from "../types/salesOrderLineType";
import { formatNumberValue, formatQuantityValue } from "../../common/numberFormat";

const STATUS_OPTIONS = [
  { value: "planned", label: "planned" },
  { value: "released", label: "released" },
  { value: "in_progress", label: "in_progress" },
  { value: "hold", label: "hold" },
  { value: "complete", label: "complete" },
  { value: "canceled", label: "canceled" },
];

type FieldType = "text" | "number" | "select";

interface FieldConfig {
  name: string;
  label: string;
  type: FieldType;
  options?: { value: string; label: string }[];
  step?: number;
  min?: number;
}

interface FieldGroup {
  title: string;
  fields: FieldConfig[];
}

const FIELD_GROUPS: FieldGroup[] = [
  {
    title: "Primary",
    fields: [
      { name: "sales_order_no", label: "sales_order_no", type: "text" },
      { name: "status", label: "status", type: "select", options: STATUS_OPTIONS },
      { name: "priority", label: "priority", type: "text" },
      { name: "price_level", label: "price_level", type: "text" },
    ],
  },
  {
    title: "Associations",
    fields: [
      { name: "id_customer", label: "id_customer", type: "number", min: 1 },
      { name: "id_manufacturer", label: "id_manufacturer", type: "number", min: 0 },
      { name: "id_vendor", label: "id_vendor", type: "number", min: 0 },
    ],
  },
  {
    title: "Financial",
    fields: [
      { name: "subtotal", label: "subtotal", type: "number", step: 0.01 },
      { name: "tax", label: "tax", type: "number", step: 0.01 },
      { name: "discount", label: "discount", type: "number", step: 0.01 },
      { name: "total", label: "total", type: "number", step: 0.01 },
    ],
  },
  {
    title: "Metadata",
    fields: [{ name: "metadata.priority", label: "metadata.priority", type: "text" }],
  },
];

const JSON_FIELD_PATHS = [
  "cost",
  "sell",
  "finance",
  "flow",
  "source",
  "subtotals",
  "prefs.userdefined",
  "refs.links",
] as const;

type JsonFieldPath = (typeof JSON_FIELD_PATHS)[number];

type SalesOrderForm = z.infer<typeof salesOrderSchema>;

type SalesOrderLineRecord = SalesOrderLine & Record<string, unknown>;

function normalizeLines(raw: unknown): SalesOrderLineRecord[] {
  if (!raw) {
    return [];
  }
  if (typeof raw === "string") {
    try {
      const parsed = JSON.parse(raw);
      return normalizeLines(parsed);
    } catch {
      return [];
    }
  }
  if (Array.isArray(raw)) {
    return raw as SalesOrderLineRecord[];
  }
  if (typeof raw === "object") {
    const container = raw as Record<string, unknown>;
    if (Array.isArray(container.results)) {
      return container.results as SalesOrderLineRecord[];
    }
    if (Array.isArray(container.data)) {
      return container.data as SalesOrderLineRecord[];
    }
    if (Array.isArray(container.items)) {
      return container.items as SalesOrderLineRecord[];
    }
    const keys = Object.keys(container);
    if (keys.length > 0 && keys.every((key) => /^\d+$/.test(key))) {
      return Object.values(container) as SalesOrderLineRecord[];
    }
  }
  return [];
}

const DEFAULT_FORM_VALUES: SalesOrderForm = {
  company: "",
  attention: "",
  address1: "",
  address2: "",
  city: "",
  state: "",
  zip: "",
  email: "",
  phoneCell: "",
  phone: "",
  actionBy: "",
  action: "",
  actionDate: "",
  actionTime: "",
  salesNameID: "",
  orderedBy: "",
  contractDetailTag: "",
  terms: "",
  typeSale: "",
  taxJuris: "",
  adSource: "",
  addComment: "",
  comment: "",
  contractDetail: "",
  id_transaction: "",
  id_customer: 0,
  subtotal: 0,
  total: 0,
  tax: 0,
  discount: 0,
  metadata: { priority: "" },
  prefs: { userdefined: {} },
  refs: { links: { contact: [], customer: [] } },
  sales_order_no: "",
  status: "planned",
  priority: "",
  price_level: "",
  id_manufacturer: 0,
  id_vendor: 0,
  cost: {},
  sell: {},
  finance: {},
  flow: {},
  source: {},
  subtotals: {},
  lines: [],
  dt_created: undefined,
  dt_updated: undefined,
  dt_modified: undefined,
  due_date: undefined,
  valid_until: undefined,
  version: undefined,
};

function serializeJson(value: unknown): string {
  if (value === undefined || value === null) {
    return "";
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch (error) {
    return "";
  }
}

function extractValue(source: Record<string, unknown>, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc === undefined || acc === null) {
      return undefined;
    }
    if (typeof acc !== "object") {
      return undefined;
    }
    return (acc as Record<string, unknown>)[key];
  }, source);
}

function setDeepValue(target: Record<string, unknown>, path: string, value: unknown) {
  const segments = path.split(".");
  let cursor: Record<string, unknown> = target;
  segments.forEach((segment, index) => {
    if (index === segments.length - 1) {
      if (value === undefined) {
        delete cursor[segment];
      } else {
        cursor[segment] = value;
      }
      return;
    }
    if (!cursor[segment] || typeof cursor[segment] !== "object") {
      cursor[segment] = {};
    }
    cursor = cursor[segment] as Record<string, unknown>;
  });
}

function getErrorMessage(errors: Record<string, unknown>, path: string): string | undefined {
  const segments = path.split(".");
  let cursor: unknown = errors;
  for (const segment of segments) {
    if (!cursor || typeof cursor !== "object") {
      return undefined;
    }
    cursor = (cursor as Record<string, unknown>)[segment];
  }
  if (!cursor || typeof cursor !== "object") {
    return undefined;
  }
  const message = (cursor as { message?: unknown }).message;
  return typeof message === "string" ? message : undefined;
}

function toNumeric(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function cloneLine(line: SalesOrderLineRecord): SalesOrderLineRecord {
  try {
    return JSON.parse(JSON.stringify(line)) as SalesOrderLineRecord;
  } catch (error) {
    return { ...(line as Record<string, unknown>) } as SalesOrderLineRecord;
  }
}

function recalculateLineFinancials(line: SalesOrderLineRecord): void {
  const container = line as Record<string, unknown>;

  const quantityRaw = container.quantity;
  if (typeof quantityRaw === "number") {
    container.quantity = toNumeric(quantityRaw);
  } else {
    const quantityObject =
      quantityRaw && typeof quantityRaw === "object"
        ? { ...(quantityRaw as Record<string, unknown>) }
        : {};
    const placedValue = toNumeric(
      extractValue(quantityObject, "placed") ?? extractValue(quantityObject, "ordered") ?? 0
    );
    quantityObject.placed = placedValue;
    if ("ordered" in quantityObject) {
      const orderedValue = toNumeric(quantityObject.ordered);
      quantityObject.remaining = Math.max(orderedValue - placedValue, 0);
    }
    container.quantity = quantityObject;
  }

  const resolvedQuantity = (() => {
    if (typeof container.quantity === "number") {
      return toNumeric(container.quantity);
    }
    if (container.quantity && typeof container.quantity === "object") {
      const quantityObject = container.quantity as Record<string, unknown>;
      return toNumeric(
        extractValue(quantityObject, "placed") ?? extractValue(quantityObject, "ordered") ?? 0
      );
    }
    return 0;
  })();

  const priceRaw = container.price;
  const priceObject =
    priceRaw && typeof priceRaw === "object"
      ? { ...(priceRaw as Record<string, unknown>) }
      : {
          unit: toNumeric(priceRaw),
          sell: toNumeric(priceRaw),
          discount_amount: 0,
          precision: 2,
        };

  const unitValue = toNumeric(priceObject.unit ?? priceObject.sell ?? 0);
  priceObject.unit = unitValue;
  if (!("sell" in priceObject) || priceObject.sell === undefined) {
    priceObject.sell = unitValue;
  }
  const discountAmount = toNumeric(priceObject.discount_amount);
  const pricePrecision = typeof priceObject.precision === "number" ? priceObject.precision : 2;
  const priceFactor = 10 ** Math.max(0, pricePrecision);
  const extendedRaw = Math.max(unitValue * resolvedQuantity - discountAmount, 0);
  const extendedValue = Number.isFinite(extendedRaw)
    ? Math.round(extendedRaw * priceFactor) / priceFactor
    : 0;
  priceObject.extended = extendedValue;
  container.price = priceObject;

  const costRaw = container.cost;
  if (costRaw && typeof costRaw === "object") {
    const costObject = { ...(costRaw as Record<string, unknown>) };
    const unitCost = toNumeric(costObject.unit);
    const costPrecision = typeof costObject.precision === "number" ? costObject.precision : 2;
    const costFactor = 10 ** Math.max(0, costPrecision);
    const costExtendedRaw = unitCost * resolvedQuantity;
    if (Number.isFinite(unitCost)) {
      costObject.unit = unitCost;
    }
    if (Number.isFinite(costExtendedRaw)) {
      costObject.extended = Math.round(costExtendedRaw * costFactor) / costFactor;
    }
    container.cost = costObject;
  }
}

interface AggregatedFinancials {
  subtotal: number;
  discount: number;
  tax: number;
  total: number;
  costTotal: number;
  costDetails: Record<string, number>;
  sellDetails: Record<string, number>;
}

function SalesOrderLinesPanel({
  lines,
  isReadOnly,
  onFieldChange,
}: {
  lines: SalesOrderLineRecord[];
  isReadOnly: boolean;
  onFieldChange?: (index: number, field: "quantity.placed" | "price.unit", value: number) => void;
}) {
  if (!Array.isArray(lines) || lines.length === 0) {
    return (
      <ComponentCard>
        <div className="text-sm text-gray-500 dark:text-gray-400">No line items available.</div>
      </ComponentCard>
    );
  }

  return (
    <ComponentCard>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold dark:text-white">Line Items</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th className="px-3 py-2 font-medium text-gray-700 dark:text-gray-200">item.ida_item</th>
                <th className="px-3 py-2 font-medium text-gray-700 dark:text-gray-200">item.description</th>
                <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-200">quantity.placed</th>
                <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-200">quantity.remaining</th>
                <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-200">price.unit</th>
                <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-200">price.discount_percent</th>
                <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-200">price.extended</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line, index) => {
                const item = (line as Record<string, unknown>).item as Record<string, unknown> | undefined;
                const quantity = (line as Record<string, unknown>).quantity as Record<string, unknown> | number | undefined;
                const price = (line as Record<string, unknown>).price as Record<string, unknown> | undefined;
                const idaItem = extractValue(item ?? {}, "ida_item") ?? "";
                const itemDescription = extractValue(item ?? {}, "description") ?? "";
                const placedNumeric =
                  typeof quantity === "number"
                    ? toNumeric(quantity)
                    : toNumeric(extractValue(quantity ?? {}, "placed"));
                const remaining = typeof quantity === "number" ? undefined : extractValue(quantity ?? {}, "remaining");
                const priceUnit = toNumeric(
                  extractValue(price ?? {}, "unit") ?? extractValue(price ?? {}, "sell") ?? 0
                );
                const priceDiscountPercent = extractValue(price ?? {}, "discount_percent");
                const priceExtended = extractValue(price ?? {}, "extended");

                const handleQuantityChange = (value: number) => {
                  if (!onFieldChange) {
                    return;
                  }
                  onFieldChange(index, "quantity.placed", value);
                };

                const handleUnitPriceChange = (value: number) => {
                  if (!onFieldChange) {
                    return;
                  }
                  onFieldChange(index, "price.unit", value);
                };

                const rowKey = (line.id ?? index).toString();

                return (
                  <tr key={rowKey} className="border-b border-gray-100 dark:border-gray-700">
                    <td className="px-3 py-2 text-gray-800 dark:text-gray-100">{String(idaItem || "")}</td>
                    <td className="px-3 py-2 text-gray-800 dark:text-gray-100">{String(itemDescription || "")}</td>
                    <td className="px-3 py-2 text-right text-gray-600 dark:text-gray-300">
                      {isReadOnly ? (
                        formatQuantityValue(placedNumeric)
                      ) : (
                        <input
                          type="number"
                          className="h-9 w-full rounded border border-gray-300 bg-white px-2 text-right text-sm text-gray-800 focus:border-blue-400 focus:outline-hidden focus:ring-2 focus:ring-blue-200 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                          step={0.01}
                          value={Number.isFinite(placedNumeric) ? placedNumeric : 0}
                          onChange={(event) => handleQuantityChange(Number(event.target.value) || 0)}
                        />
                      )}
                    </td>
                    <td className="px-3 py-2 text-right text-gray-600 dark:text-gray-300">{formatQuantityValue(remaining)}</td>
                    <td className="px-3 py-2 text-right text-gray-600 dark:text-gray-300">
                      {isReadOnly ? (
                        formatNumberValue(priceUnit)
                      ) : (
                        <input
                          type="number"
                          className="h-9 w-full rounded border border-gray-300 bg-white px-2 text-right text-sm text-gray-800 focus:border-blue-400 focus:outline-hidden focus:ring-2 focus:ring-blue-200 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                          step={0.01}
                          value={Number.isFinite(priceUnit) ? priceUnit : 0}
                          onChange={(event) => handleUnitPriceChange(Number(event.target.value) || 0)}
                        />
                      )}
                    </td>
                    <td className="px-3 py-2 text-right text-gray-600 dark:text-gray-300">{formatNumberValue(priceDiscountPercent)}</td>
                    <td className="px-3 py-2 text-right text-gray-600 dark:text-gray-300">{formatNumberValue(priceExtended)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
    </ComponentCard>
  );
}

export default function SalesOrderDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: SalesOrderAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<SalesOrderForm>({
    resolver: zodResolver(salesOrderSchema),
    defaultValues: DEFAULT_FORM_VALUES,
    mode: "onBlur",
  });

  const [jsonDrafts, setJsonDrafts] = useState<Record<JsonFieldPath, string>>(() => {
    const base: Record<JsonFieldPath, string> = {
      cost: "",
      sell: "",
      finance: "",
      flow: "",
      source: "",
      subtotals: "",
      "prefs.userdefined": "",
      "refs.links": "",
    };
    return base;
  });
  const [jsonErrors, setJsonErrors] = useState<Record<JsonFieldPath, string | undefined>>({
    cost: undefined,
    sell: undefined,
    finance: undefined,
    flow: undefined,
    source: undefined,
    subtotals: undefined,
    "prefs.userdefined": undefined,
    "refs.links": undefined,
  });
  const [lineDrafts, setLineDrafts] = useState<SalesOrderLineRecord[]>([]);

  const location = useLocation();
  const routeState = (location.state as Record<string, unknown>) || {};
  const mode = (modeProp || routeState.mode || "add") as "add" | "edit" | "view";
  const data = (dataProp || routeState.data || null) as (SalesOrderForm & { id?: number }) | null;
  const isReadOnly = mode === "view";

  const [recordData, setRecordData] = useState<(SalesOrderForm & { id?: number }) | null>(data);

  useEffect(() => {
    setRecordData(data);
  }, [data]);

  const dispatchToastError = useCallback(
    (message: string) => {
      dispatch(showToast({ message, type: "error" }));
    },
    [dispatch]
  );

  useEffect(() => {
    if (!data?.id) {
      return;
    }
    if (normalizeLines((data as Record<string, unknown>)?.lines).length > 0) {
      return;
    }
    let cancelled = false;
    const loadDetail = async () => {
      try {
        const detail = await fetchSalesOrderDetail(data.id);
        if (!cancelled) {
          setRecordData(detail as SalesOrderForm & { id?: number });
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Failed to load sales order";
          dispatchToastError(message);
        }
      }
    };
    loadDetail();
    return () => {
      cancelled = true;
    };
  }, [data, dispatchToastError]);

  const mergedDefaults = useMemo(() => {
    if (!recordData) {
      return DEFAULT_FORM_VALUES;
    }
    return {
      ...DEFAULT_FORM_VALUES,
      ...recordData,
      metadata: {
        ...DEFAULT_FORM_VALUES.metadata,
        ...(typeof recordData.metadata === "object" && recordData.metadata ? recordData.metadata : {}),
      },
      prefs: {
        ...DEFAULT_FORM_VALUES.prefs,
        ...(typeof recordData.prefs === "object" && recordData.prefs ? recordData.prefs : {}),
      },
      refs: {
        ...DEFAULT_FORM_VALUES.refs,
        ...(typeof recordData.refs === "object" && recordData.refs ? recordData.refs : {}),
      },
      cost: typeof recordData.cost === "object" && recordData.cost ? recordData.cost : {},
      sell: typeof recordData.sell === "object" && recordData.sell ? recordData.sell : {},
      finance: typeof recordData.finance === "object" && recordData.finance ? recordData.finance : {},
      flow: typeof recordData.flow === "object" && recordData.flow ? recordData.flow : {},
      source: typeof recordData.source === "object" && recordData.source ? recordData.source : {},
      subtotals: typeof recordData.subtotals === "object" && recordData.subtotals ? recordData.subtotals : {},
      lines: normalizeLines((recordData as Record<string, unknown>).lines),
    } as SalesOrderForm;
  }, [recordData]);

  useEffect(() => {
    reset(mergedDefaults);
    const drafts: Partial<Record<JsonFieldPath, string>> = {};
    JSON_FIELD_PATHS.forEach((path) => {
      drafts[path] = serializeJson(extractValue(mergedDefaults as Record<string, unknown>, path));
      setValue(path as any, extractValue(mergedDefaults as Record<string, unknown>, path) as any);
    });
    setJsonDrafts((prev) => ({ ...prev, ...drafts } as Record<JsonFieldPath, string>));
    setJsonErrors({
      cost: undefined,
      sell: undefined,
      finance: undefined,
      flow: undefined,
      source: undefined,
      subtotals: undefined,
      "prefs.userdefined": undefined,
      "refs.links": undefined,
    });
  }, [mergedDefaults, reset, setValue]);

  const lineItems = useMemo(() => {
    if (recordData && typeof recordData === "object") {
      return normalizeLines((recordData as Record<string, unknown>).lines);
    }
    return [];
  }, [recordData]);

  useEffect(() => {
    const clonedLines = lineItems.map((line) => cloneLine(line));
    setLineDrafts(clonedLines);
    setValue("lines" as any, clonedLines as any, { shouldDirty: false, shouldValidate: false });
  }, [lineItems, setValue]);

  const aggregatedFinancials = useMemo<AggregatedFinancials>(() => {
    let subtotal = 0;
    let discount = 0;
    let tax = 0;
    let total = 0;
    let costTotal = 0;

    lineDrafts.forEach((line) => {
      const quantityPlaced = toNumeric(
        extractValue(line as Record<string, unknown>, "quantity.placed") ??
          extractValue(line as Record<string, unknown>, "quantity.ordered") ??
          (line as Record<string, unknown>).quantity
      );
      const quantity = quantityPlaced || 0;

      const unitSell = toNumeric(
        extractValue(line as Record<string, unknown>, "price.unit") ??
          extractValue(line as Record<string, unknown>, "price.sell") ??
          extractValue(line as Record<string, unknown>, "sell.unit")
      );
      const lineSubtotal = quantity ? quantity * unitSell : unitSell;

      let lineDiscount = toNumeric(
        extractValue(line as Record<string, unknown>, "price.discount_amount") ??
          extractValue(line as Record<string, unknown>, "discount_amount")
      );
      if (!lineDiscount) {
        const discountPercent = toNumeric(
          extractValue(line as Record<string, unknown>, "price.discount_percent")
        );
        if (discountPercent && lineSubtotal) {
          lineDiscount = (lineSubtotal * discountPercent) / 100;
        }
      }

      const lineTax = toNumeric(
        extractValue(line as Record<string, unknown>, "price.tax") ??
          extractValue(line as Record<string, unknown>, "tax")
      );

      const extractedExtended = toNumeric(
        extractValue(line as Record<string, unknown>, "price.extended") ??
          extractValue(line as Record<string, unknown>, "price.total") ??
          extractValue(line as Record<string, unknown>, "extended_price")
      );
      const lineSellBeforeTax = extractedExtended || Math.max(lineSubtotal - lineDiscount, 0);
      const lineTotal = lineSellBeforeTax + lineTax;

      const unitCost = toNumeric(
        extractValue(line as Record<string, unknown>, "cost.unit") ??
          extractValue(line as Record<string, unknown>, "price.cost") ??
          extractValue(line as Record<string, unknown>, "cost")
      );
      const extractedCostExtended = toNumeric(
        extractValue(line as Record<string, unknown>, "cost.extended") ??
          extractValue(line as Record<string, unknown>, "cost.total") ??
          extractValue(line as Record<string, unknown>, "extended_cost")
      );
      const lineCost = extractedCostExtended || (unitCost && quantity ? unitCost * quantity : unitCost);

      subtotal += Number.isFinite(lineSubtotal) ? lineSubtotal : 0;
      discount += Number.isFinite(lineDiscount) ? lineDiscount : 0;
      tax += Number.isFinite(lineTax) ? lineTax : 0;
      total += Number.isFinite(lineTotal) ? lineTotal : 0;
      costTotal += Number.isFinite(lineCost) ? lineCost : 0;
    });

    const sellDetails: Record<string, number> = {
      subtotal: Number(subtotal.toFixed(2)),
      discount: Number(discount.toFixed(2)),
      tax: Number(tax.toFixed(2)),
      total: Number(total.toFixed(2)),
    };

    const costDetails: Record<string, number> = {
      subtotal: Number(costTotal.toFixed(2)),
      total: Number(costTotal.toFixed(2)),
    };

    return {
      subtotal: Number(subtotal.toFixed(2)),
      discount: Number(discount.toFixed(2)),
      tax: Number(tax.toFixed(2)),
      total: Number(total.toFixed(2)),
      costTotal: Number(costTotal.toFixed(2)),
      costDetails,
      sellDetails,
    };
  }, [lineDrafts]);

  const handleLineFieldChange = useCallback(
    (index: number, field: "quantity.placed" | "price.unit", rawValue: number) => {
      const value = Number.isFinite(rawValue) ? rawValue : 0;
      setLineDrafts((prev) => {
        const next = prev.map((line, idx) => {
          if (idx !== index) {
            return line;
          }
          const nextLine = cloneLine(line);
          const container = nextLine as Record<string, unknown>;

          if (field === "quantity.placed") {
            const quantityRaw = container.quantity;
            if (typeof quantityRaw === "number") {
              container.quantity = value;
            } else {
              const quantityObject =
                quantityRaw && typeof quantityRaw === "object"
                  ? { ...(quantityRaw as Record<string, unknown>) }
                  : {};
              quantityObject.placed = value;
              if ("ordered" in quantityObject) {
                const orderedValue = toNumeric(quantityObject.ordered);
                quantityObject.remaining = Math.max(orderedValue - value, 0);
              }
              container.quantity = quantityObject;
            }
          } else if (field === "price.unit") {
            const priceRaw = container.price;
            const priceObject =
              priceRaw && typeof priceRaw === "object"
                ? { ...(priceRaw as Record<string, unknown>) }
                : { discount_amount: 0, precision: 2 };
            priceObject.unit = value;
            priceObject.sell = value;
            container.price = priceObject;
          }

          recalculateLineFinancials(nextLine);
          return nextLine;
        });

        setValue("lines" as any, next as any, { shouldDirty: true, shouldValidate: false });
        return next;
      });
    },
    [setValue]
  );

  useEffect(() => {
    setValue("subtotal", aggregatedFinancials.subtotal, { shouldDirty: false, shouldValidate: false });
    setValue("discount", aggregatedFinancials.discount, { shouldDirty: false, shouldValidate: false });
    setValue("tax", aggregatedFinancials.tax, { shouldDirty: false, shouldValidate: false });
    setValue("total", aggregatedFinancials.total, { shouldDirty: false, shouldValidate: false });
    setValue("cost" as any, aggregatedFinancials.costDetails as any, { shouldDirty: false, shouldValidate: false });
    setValue("sell" as any, aggregatedFinancials.sellDetails as any, { shouldDirty: false, shouldValidate: false });

    const nextCost = serializeJson(aggregatedFinancials.costDetails);
    const nextSell = serializeJson(aggregatedFinancials.sellDetails);

    setJsonDrafts((prev) => {
      if (prev.cost === nextCost && prev.sell === nextSell) {
        return prev;
      }
      return {
        ...prev,
        cost: nextCost,
        sell: nextSell,
      };
    });
  }, [aggregatedFinancials, setValue]);

  const handleJsonDraftChange = (path: JsonFieldPath, value: string) => {
    setJsonDrafts((prev) => ({ ...prev, [path]: value }));
  };

  const handleJsonBlur = (path: JsonFieldPath) => {
    const raw = jsonDrafts[path];
    if (!raw.trim()) {
      setJsonErrors((prev) => ({ ...prev, [path]: undefined }));
      setValue(path as any, undefined);
      return;
    }
    try {
      const parsed = JSON.parse(raw);
      setValue(path as any, parsed);
      setJsonErrors((prev) => ({ ...prev, [path]: undefined }));
    } catch (error) {
      setJsonErrors((prev) => ({ ...prev, [path]: "Invalid JSON" }));
    }
  };

  const applyJsonDraftsToPayload = (payload: SalesOrderForm) => {
    JSON_FIELD_PATHS.forEach((path) => {
      const draft = jsonDrafts[path];
      if (!draft || !draft.trim()) {
        setDeepValue(payload as unknown as Record<string, unknown>, path, undefined);
        return;
      }
      try {
        const parsed = JSON.parse(draft);
        setDeepValue(payload as unknown as Record<string, unknown>, path, parsed);
      } catch (error) {
        throw new Error(`Invalid JSON for ${path}`);
      }
    });
  };

  const onSubmit = async (formData: SalesOrderForm) => {
    try {
      applyJsonDraftsToPayload(formData);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Invalid JSON payload";
      dispatchToastError(message);
      return;
    }

    try {
      const result =
        mode === "add"
          ? await createSalesOrder(formData)
          : await updateSalesOrder(recordData?.id as number, formData);

      if (result) {
        dispatch(
          showToast({
            message: `Sales order ${mode === "add" ? "created" : "updated"} successfully`,
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Operation failed";
      dispatchToastError(message);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!recordData?.id) {
      return;
    }
    try {
      await updateSalesOrder(recordData.id, { ...mergedDefaults, status: newStatus });
      dispatch(showToast({ message: `Sales order marked as ${newStatus}`, type: "success" }));
      if (onSaved) {
        onSaved();
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to update status";
      dispatchToastError(message);
    }
  };

  const renderField = (field: FieldConfig) => {
    const inputId = field.name.replace(/\./g, "-");
    const errorMessage = getErrorMessage(errors as unknown as Record<string, unknown>, field.name);

    if (field.type === "select" && field.options) {
      return (
        <div key={field.name}>
          <Label htmlFor={inputId}>{field.label}</Label>
          <select
            id={inputId}
            disabled={isReadOnly}
            className={`h-10 w-full rounded-lg border px-3 text-sm focus:outline-hidden focus:ring-2 dark:bg-gray-900 dark:text-white/90 ${
              errorMessage ? "border-error-500" : "border-gray-300"
            }`}
            {...register(field.name as any)}
          >
            <option value="">--</option>
            {field.options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          {errorMessage && <p className="mt-1 text-xs text-error-500">{errorMessage}</p>}
        </div>
      );
    }

    const registerOptions = field.type === "number" ? { valueAsNumber: true } : undefined;

    return (
      <div key={field.name}>
        <Label htmlFor={inputId}>{field.label}</Label>
        <Input
          id={inputId}
          type={field.type === "number" ? "number" : "text"}
          step={field.step}
          min={field.min}
          disabled={isReadOnly && field.name !== "metadata.priority"}
          error={Boolean(errorMessage)}
          hint={errorMessage}
          {...register(field.name as any, registerOptions)}
        />
      </div>
    );
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Sales Order"
              : mode === "view"
              ? "View Sales Order"
              : "Sales Order Detail"
          }
        />
      )}

      <ComponentCard>
        {inline && (
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold dark:text-white">
              {mode === "edit" ? "Edit Sales Order" : mode === "view" ? "View Sales Order" : "Add Sales Order"}
            </h3>
            {onCancelInline && (
              <button
                type="button"
                onClick={onCancelInline}
                className="text-2xl leading-none text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
          {FIELD_GROUPS.map((group) => (
            <section key={group.title}>
              <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-300">
                {group.title}
              </h4>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {group.fields.map(renderField)}
              </div>
            </section>
          ))}

          <section>
            <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-300">
              JSON envelopes
            </h4>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {JSON_FIELD_PATHS.map((path) => {
                const inputId = path.replace(/\./g, "-");
                const errorMessage = jsonErrors[path];
                return (
                  <div key={path}>
                    <Label htmlFor={inputId}>{path}</Label>
                    <textarea
                      id={inputId}
                      className={`min-h-[140px] w-full rounded-lg border px-3 py-2 text-sm font-mono focus:outline-hidden focus:ring-2 dark:bg-gray-900 dark:text-white/90 ${
                        errorMessage ? "border-error-500" : "border-gray-300"
                      }`}
                      placeholder={`{ /* ${path} payload */ }`}
                      value={jsonDrafts[path] ?? ""}
                      onChange={(event) => handleJsonDraftChange(path, event.target.value)}
                      onBlur={() => handleJsonBlur(path)}
                      disabled={isReadOnly}
                    />
                    {errorMessage && <p className="mt-1 text-xs text-error-500">{errorMessage}</p>}
                  </div>
                );
              })}
            </div>
          </section>

          {mode === "view" && recordData?.id && (
            <section className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div>
                <Label>dt_created</Label>
                <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300">
                  {mergedDefaults.dt_created ? new Date(Number(mergedDefaults.dt_created) * (String(mergedDefaults.dt_created).length === 13 ? 1 : 1000)).toLocaleString() : "--"}
                </div>
              </div>
              <div>
                <Label>dt_modified</Label>
                <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300">
                  {mergedDefaults.dt_modified ? new Date(Number(mergedDefaults.dt_modified) * (String(mergedDefaults.dt_modified).length === 13 ? 1 : 1000)).toLocaleString() : "--"}
                </div>
              </div>
              <div>
                <Label>Audit</Label>
                <AuditTrail transactionId={recordData.id} model="sales_order" />
              </div>
              <div>
                <Label>Status flow</Label>
                <SalesOrderStatus
                  currentStatus={(mergedDefaults.status ?? "draft") as any}
                  onStatusChange={handleStatusChange}
                  readonly={false}
                  showHistory
                />
              </div>
            </section>
          )}

          {mode !== "view" && (
            <div className="flex items-center gap-3">
              <button
                type="submit"
                className="rounded-md bg-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-blue-600 focus:outline-hidden focus:ring-2 focus:ring-blue-400"
              >
                {mode === "edit" ? "Save" : "Create"}
              </button>
            </div>
          )}
        </form>
      </ComponentCard>

      <SalesOrderLinesPanel
        lines={lineDrafts}
        isReadOnly={isReadOnly}
        onFieldChange={isReadOnly ? undefined : handleLineFieldChange}
      />
    </>
  );
}
