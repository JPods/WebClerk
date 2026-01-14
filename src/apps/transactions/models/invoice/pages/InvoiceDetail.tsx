import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent as ReactDragEvent,
  type ReactNode,
} from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input, TextArea } from "../../../../../components/wrapper";
import { showToast } from "../../../../../store/slices/toastSlice";

import { invoiceSchema } from "../utils/invoiceSchema";
import {
  createInvoice,
  updateInvoice,
  fetchInvoiceDetail,
  searchCustomers,
} from "../services/invoiceApi";
import { saveRecord, deleteRecord } from "../../../../../api/wcapi";
import { InvoiceAddProps } from "../types/invoiceType";
import { AuditTrail } from "../../../../../components/transactions/common/AuditTrail";
import InvoiceStatus from "../components/InvoiceStatus";
import InvoiceItemSearch from "../components/InvoiceItemSearch";
import type { ItemSearchResult } from "../types/itemSearchType";
import type { InvoiceLine } from "../types/invoiceLineType";
import {
  resolveItemCode,
  resolveItemDescription,
  resolveItemKey,
  resolveUnitCost,
  resolveUnitPrice,
} from "../utils/itemSearchHelpers";
import {
  formatNumberValue,
  formatQuantityValue,
} from "../../common/numberFormat";

const STATUS_OPTIONS = [
  { value: "draft", label: "Draft" },
  { value: "sent", label: "Sent" },
  { value: "paid", label: "Paid" },
  { value: "overdue", label: "Overdue" },
  { value: "cancelled", label: "Cancelled" },
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

type InvoiceForm = z.infer<typeof invoiceSchema>;

type InvoiceLineRecord = InvoiceLine & Record<string, unknown>;

type CustomerSearchResult = Record<string, unknown> & {
  id?: number | string;
  display_name?: string;
  org_type?: string;
  status?: string;
  email?: string;
  phone?: string;
  ida_customer?: string;
  ida?: string;
};

type ContactLinkRecord = Record<string, unknown> & {
  id?: number | string;
  contact?: Record<string, unknown>;
};

interface ContactLinkDisplayRow {
  id: number | null;
  alias: string;
  name: string;
  role: string;
  purpose: string;
  email: string;
  phone: string;
  raw: ContactLinkRecord;
}

type ContactColumnKey =
  | "id"
  | "alias"
  | "name"
  | "role"
  | "purpose"
  | "email"
  | "phone";

interface ContactLinkColumnDef {
  key: ContactColumnKey;
  label: string;
  render: (row: ContactLinkDisplayRow) => ReactNode;
}

const CONTACT_LINK_COLUMN_DEFS: ContactLinkColumnDef[] = [
  {
    key: "id",
    label: "id",
    render: (row) => row.id ?? "--",
  },
  {
    key: "alias",
    label: "ida_contact",
    render: (row) => row.alias || "--",
  },
  {
    key: "name",
    label: "display_name",
    render: (row) => row.name,
  },
  {
    key: "role",
    label: "role",
    render: (row) => row.role || "--",
  },
  {
    key: "purpose",
    label: "purpose",
    render: (row) => row.purpose || "--",
  },
  {
    key: "email",
    label: "email",
    render: (row) => row.email || "--",
  },
  {
    key: "phone",
    label: "phone",
    render: (row) => row.phone || "--",
  },
];

const CONTACT_LINK_COLUMN_LOOKUP: Record<
  ContactColumnKey,
  ContactLinkColumnDef
> = CONTACT_LINK_COLUMN_DEFS.reduce((acc, def) => {
  acc[def.key] = def;
  return acc;
}, {} as Record<ContactColumnKey, ContactLinkColumnDef>);

const CONTACT_LINK_CELL_CLASS: Record<ContactColumnKey, string> = {
  id: "px-3 py-2 text-gray-800 dark:text-gray-100",
  alias: "px-3 py-2 text-gray-600 dark:text-gray-300",
  name: "px-3 py-2 text-gray-800 dark:text-gray-100",
  role: "px-3 py-2 text-gray-600 dark:text-gray-300",
  purpose: "px-3 py-2 text-gray-600 dark:text-gray-300",
  email: "px-3 py-2 text-gray-600 dark:text-gray-300",
  phone: "px-3 py-2 text-gray-600 dark:text-gray-300",
};

const READONLY_FIELD_NAMES = new Set(["ida", "invoice_no", "subtotal"]);
const READONLY_JSON_FIELDS = new Set<JsonFieldPath>([
  "cost",
  "sell",
  "finance",
  "flow",
]);

function normalizeLines(raw: unknown): InvoiceLineRecord[] {
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
    return raw as InvoiceLineRecord[];
  }
  if (typeof raw === "object") {
    const container = raw as Record<string, unknown>;
    if (Array.isArray(container.results)) {
      return container.results as InvoiceLineRecord[];
    }
    if (Array.isArray(container.data)) {
      return container.data as InvoiceLineRecord[];
    }
    if (Array.isArray(container.items)) {
      return container.items as InvoiceLineRecord[];
    }
    const keys = Object.keys(container);
    if (keys.length > 0 && keys.every((key) => /^\d+$/.test(key))) {
      return Object.values(container) as InvoiceLineRecord[];
    }
  }
  return [];
}

const DEFAULT_FORM_VALUES: InvoiceForm = {
  ida: "",
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
  id_transaction: 0,
  customer_id: 0,
  subtotal: 0,
  total: 0,
  tax: 0,
  discount: 0,
  metadata: { priority: "" },
  prefs: { userdefined: {} },
  refs: { links: { contact: [], customer: [] } },
  status: "draft",
  priority: "",
  price_level: "",
  manufacturer_id: 0,
  vendor_id: 0,
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

function setDeepValue(
  target: Record<string, unknown>,
  path: string,
  value: unknown
) {
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

function resolveStringField(
  record: Record<string, unknown>,
  keys: string[]
): string {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string") {
      const trimmed = value.trim();
      if (trimmed) {
        return trimmed;
      }
    }
  }
  return "";
}

function resolveCustomerId(record: Record<string, unknown>): number | null {
  const candidates = [
    record.id,
    record.id_customer,
    record.customer_id,
    record.customerId,
    record.pk,
    record.org_id,
  ];

  for (const candidate of candidates) {
    if (
      typeof candidate === "number" &&
      Number.isFinite(candidate) &&
      candidate > 0
    ) {
      return candidate;
    }
    if (typeof candidate === "string") {
      const parsed = Number.parseInt(candidate, 10);
      if (Number.isFinite(parsed) && parsed > 0) {
        return parsed;
      }
    }
  }

  return null;
}

function resolveCustomerLabel(record: Record<string, unknown>): string {
  const nameFirst = resolveStringField(record, ["name_first", "first_name"]);
  const nameLast = resolveStringField(record, ["name_last", "last_name"]);
  const combined = `${nameFirst} ${nameLast}`.trim();
  if (combined) {
    return combined;
  }

  const label = resolveStringField(record, [
    "display_name",
    "company",
    "name",
    "organization_name",
  ]);
  if (label) {
    return label;
  }

  const id = resolveCustomerId(record);
  return id ? `Customer #${id}` : "Customer";
}

function resolveCustomerAlias(record: Record<string, unknown>): string {
  return resolveStringField(record, [
    "ida_customer",
    "ida",
    "customer_code",
    "customer_number",
  ]);
}

function resolveContactRecord(
  entry: ContactLinkRecord
): Record<string, unknown> {
  if (entry.contact && typeof entry.contact === "object" && entry.contact) {
    return entry.contact;
  }
  return entry;
}

function resolveContactId(entry: ContactLinkRecord): number | null {
  const record = resolveContactRecord(entry);
  const candidates = [
    entry.id,
    record.id,
    record.contact_id,
    record.id_contact,
    record.contactId,
  ];
  for (const candidate of candidates) {
    if (
      typeof candidate === "number" &&
      Number.isFinite(candidate) &&
      candidate > 0
    ) {
      return candidate;
    }
    if (typeof candidate === "string") {
      const parsed = Number.parseInt(candidate, 10);
      if (Number.isFinite(parsed) && parsed > 0) {
        return parsed;
      }
    }
  }
  return null;
}

function resolveContactName(entry: ContactLinkRecord): string {
  const record = resolveContactRecord(entry);
  const first = resolveStringField(record, [
    "name_first",
    "first_name",
    "given_name",
  ]);
  const last = resolveStringField(record, [
    "name_last",
    "last_name",
    "family_name",
  ]);
  const combined = `${first} ${last}`.trim();
  if (combined) {
    return combined;
  }
  const display = resolveStringField(record, ["display_name", "label", "name"]);
  if (display) {
    return display;
  }
  const id = resolveContactId(entry);
  return id ? `Contact #${id}` : "Contact";
}

function resolveContactAlias(entry: ContactLinkRecord): string {
  const record = resolveContactRecord(entry);
  return resolveStringField(record, ["ida_contact", "ida", "contact_code"]);
}

function resolveContactEmail(entry: ContactLinkRecord): string {
  const record = resolveContactRecord(entry);
  return resolveStringField(record, [
    "email",
    "email_primary",
    "contact_email",
  ]);
}

function resolveContactPhone(entry: ContactLinkRecord): string {
  const record = resolveContactRecord(entry);
  return resolveStringField(record, [
    "phone",
    "phone_primary",
    "phoneCell",
    "phone_number",
  ]);
}

function resolveContactRole(entry: ContactLinkRecord): string {
  const record = resolveContactRecord(entry);
  return resolveStringField(record, ["role", "relation", "type", "category"]);
}

function resolveContactPurpose(entry: ContactLinkRecord): string {
  const fallbackTargets = entry as Record<string, unknown>;
  const record = resolveContactRecord(entry);
  const purpose = resolveStringField(record, [
    "purpose",
    "contact_purpose",
    "link_purpose",
    "context",
  ]);
  if (purpose) {
    return purpose;
  }
  return resolveStringField(fallbackTargets, [
    "purpose",
    "contact_purpose",
    "link_purpose",
    "context",
  ]);
}

function getErrorMessage(
  errors: Record<string, unknown>,
  path: string
): string | undefined {
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

function extractNumericId(candidate: unknown): number | null {
  if (
    typeof candidate === "number" &&
    Number.isFinite(candidate) &&
    candidate > 0
  ) {
    return candidate;
  }
  if (typeof candidate === "string") {
    const parsed = Number.parseInt(candidate, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  }
  return null;
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

function cloneLine(line: InvoiceLineRecord): InvoiceLineRecord {
  try {
    return JSON.parse(JSON.stringify(line)) as InvoiceLineRecord;
  } catch (error) {
    return { ...(line as Record<string, unknown>) } as InvoiceLineRecord;
  }
}

function resolveLineId(line: InvoiceLineRecord): number | null {
  if (!line || typeof line !== "object") {
    return null;
  }
  return extractNumericId((line as Record<string, unknown>).id);
}

function recalculateLineFinancials(line: InvoiceLineRecord): void {
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
      extractValue(quantityObject, "placed") ??
        extractValue(quantityObject, "ordered") ??
        0
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
        extractValue(quantityObject, "placed") ??
          extractValue(quantityObject, "ordered") ??
          0
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
  const pricePrecision =
    typeof priceObject.precision === "number" ? priceObject.precision : 2;
  const priceFactor = 10 ** Math.max(0, pricePrecision);
  const extendedRaw = Math.max(
    unitValue * resolvedQuantity - discountAmount,
    0
  );
  const extendedValue = Number.isFinite(extendedRaw)
    ? Math.round(extendedRaw * priceFactor) / priceFactor
    : 0;
  priceObject.extended = extendedValue;
  container.price = priceObject;

  const costRaw = container.cost;
  if (costRaw && typeof costRaw === "object") {
    const costObject = { ...(costRaw as Record<string, unknown>) };
    const unitCost = toNumeric(costObject.unit);
    const costPrecision =
      typeof costObject.precision === "number" ? costObject.precision : 2;
    const costFactor = 10 ** Math.max(0, costPrecision);
    const costExtendedRaw = unitCost * resolvedQuantity;
    if (Number.isFinite(unitCost)) {
      costObject.unit = unitCost;
    }
    if (Number.isFinite(costExtendedRaw)) {
      costObject.extended =
        Math.round(costExtendedRaw * costFactor) / costFactor;
    }
    container.cost = costObject;
  }
}

function resolveLineKey(line: InvoiceLineRecord): string {
  const container = line as Record<string, unknown>;
  const item = container.item as Record<string, unknown> | undefined;
  const candidates: unknown[] = [
    container.item_id,
    container.item_code,
    container.item_key,
    item?.id,
    item?.ida_item,
    item?.["ida_item"],
    item?.["item_num"],
    item?.["itemNum"],
    item?.["code"],
    item?.["sku"],
    line.id,
  ];

  for (const candidate of candidates) {
    if (candidate === null || candidate === undefined) {
      continue;
    }
    const text = String(candidate).trim();
    if (text) {
      return text;
    }
  }
  return "";
}

function buildLineFromItem(
  item: ItemSearchResult,
  quantity: number
): InvoiceLineRecord {
  const normalizedQuantity =
    Number.isFinite(quantity) && quantity > 0 ? quantity : 0;
  const description = resolveItemDescription(item) || "Item";
  const itemCode = resolveItemCode(item);
  const unitPrice = resolveUnitPrice(item);
  const unitCost = resolveUnitCost(item);

  const line = {
    description,
    quantity: normalizedQuantity,
    price: {
      sell: unitPrice,
      cost: unitCost,
    },
    discount_amount: 0,
  } as unknown as InvoiceLineRecord;

  const container = line as Record<string, unknown>;
  const itemId = item.id ?? item.item_id ?? item.itemId ?? undefined;

  container.item_id = itemId ?? undefined;
  container.item_code = itemCode || undefined;
  container.item_key = resolveItemKey(item) || undefined;
  container.item_name = description;
  container.key_tags = item.key_tags ?? item.keyTags ?? undefined;
  container.item = {
    id: itemId,
    ida_item: itemCode || undefined,
    code: itemCode || undefined,
    description,
    sku: item.sku ?? undefined,
    key_tags: item.key_tags ?? item.keyTags ?? undefined,
  };
  container.quantity = {
    placed: normalizedQuantity,
    ordered: normalizedQuantity,
    remaining: 0,
  };
  container.price = {
    unit: unitPrice,
    sell: unitPrice,
    discount_amount: 0,
    discount_percent: 0,
    precision: 2,
  };
  container.cost = {
    unit: unitCost,
    precision: 2,
  };

  recalculateLineFinancials(line);

  return line;
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

function InvoiceLinesPanel({
  lines,
  isReadOnly,
  onFieldChange,
}: {
  lines: InvoiceLineRecord[];
  isReadOnly: boolean;
  onFieldChange?: (
    index: number,
    field: "quantity.placed" | "price.unit",
    value: number
  ) => void;
}) {
  if (!Array.isArray(lines) || lines.length === 0) {
    return (
      <ComponentCard>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          No line items available.
        </div>
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
              <th className="px-3 py-2 font-medium text-gray-700 dark:text-gray-200">
                item.ida_item
              </th>
              <th className="px-3 py-2 font-medium text-gray-700 dark:text-gray-200">
                item.description
              </th>
              <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-200">
                quantity.placed
              </th>
              <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-200">
                quantity.remaining
              </th>
              <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-200">
                price.unit
              </th>
              <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-200">
                price.discount_percent
              </th>
              <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-200">
                price.extended
              </th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line, index) => {
              const item = (line as Record<string, unknown>).item as
                | Record<string, unknown>
                | undefined;
              const quantity = (line as Record<string, unknown>).quantity as
                | Record<string, unknown>
                | number
                | undefined;
              const price = (line as Record<string, unknown>).price as
                | Record<string, unknown>
                | undefined;
              const idaItem = extractValue(item ?? {}, "ida_item") ?? "";
              const itemDescription =
                extractValue(item ?? {}, "description") ?? "";
              const placedNumeric =
                typeof quantity === "number"
                  ? toNumeric(quantity)
                  : toNumeric(extractValue(quantity ?? {}, "placed"));
              const remaining =
                typeof quantity === "number"
                  ? undefined
                  : extractValue(quantity ?? {}, "remaining");
              const priceUnit = toNumeric(
                extractValue(price ?? {}, "unit") ??
                  extractValue(price ?? {}, "sell") ??
                  0
              );
              const priceDiscountPercent = extractValue(
                price ?? {},
                "discount_percent"
              );
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
                <tr
                  key={rowKey}
                  className="border-b border-gray-100 dark:border-gray-700"
                >
                  <td className="px-3 py-2 text-gray-800 dark:text-gray-100">
                    {String(idaItem || "")}
                  </td>
                  <td className="px-3 py-2 text-gray-800 dark:text-gray-100">
                    {String(itemDescription || "")}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-600 dark:text-gray-300">
                    {isReadOnly ? (
                      formatQuantityValue(placedNumeric)
                    ) : (
                      <input
                        type="number"
                        className="h-9 w-full rounded border border-gray-300 bg-white px-2 text-right text-sm text-gray-800 focus:border-blue-400 focus:outline-hidden focus:ring-2 focus:ring-blue-200 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                        step={0.01}
                        value={
                          Number.isFinite(placedNumeric) ? placedNumeric : 0
                        }
                        onChange={(event) =>
                          handleQuantityChange(Number(event.target.value) || 0)
                        }
                      />
                    )}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-600 dark:text-gray-300">
                    {formatQuantityValue(remaining)}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-600 dark:text-gray-300">
                    {isReadOnly ? (
                      formatNumberValue(priceUnit)
                    ) : (
                      <input
                        type="number"
                        className="h-9 w-full rounded border border-gray-300 bg-white px-2 text-right text-sm text-gray-800 focus:border-blue-400 focus:outline-hidden focus:ring-2 focus:ring-blue-200 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                        step={0.01}
                        value={Number.isFinite(priceUnit) ? priceUnit : 0}
                        onChange={(event) =>
                          handleUnitPriceChange(Number(event.target.value) || 0)
                        }
                      />
                    )}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-600 dark:text-gray-300">
                    {formatNumberValue(priceDiscountPercent)}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-600 dark:text-gray-300">
                    {formatNumberValue(priceExtended)}
                  </td>
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
}: InvoiceAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<InvoiceForm>({
    resolver: zodResolver(invoiceSchema),
    defaultValues: DEFAULT_FORM_VALUES,
    mode: "onBlur",
  });

  const [jsonDrafts, setJsonDrafts] = useState<Record<JsonFieldPath, string>>(
    () => {
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
    }
  );
  const [jsonErrors, setJsonErrors] = useState<
    Record<JsonFieldPath, string | undefined>
  >({
    cost: undefined,
    sell: undefined,
    finance: undefined,
    flow: undefined,
    source: undefined,
    subtotals: undefined,
    "prefs.userdefined": undefined,
    "refs.links": undefined,
  });
  const [lineDrafts, setLineDrafts] = useState<InvoiceLineRecord[]>([]);
  const [isNotesLocked, setIsNotesLocked] = useState(true);
  const location = useLocation();
  const routeState = (location.state as Record<string, unknown>) || {};
  const mode = (modeProp || routeState.mode || "add") as
    | "add"
    | "edit"
    | "view";
  const data = (dataProp || routeState.data || null) as
    | (InvoiceForm & { id?: number })
    | null;
  const isReadOnly = mode === "view";

  const [recordData, setRecordData] = useState<
    (InvoiceForm & { id?: number }) | null
  >(data);

  const [customerSearchKeyword, setCustomerSearchKeyword] = useState("");
  const [customerSearchId, setCustomerSearchId] = useState("");
  const [customerSearchIda, setCustomerSearchIda] = useState("");
  const [customerSearchResults, setCustomerSearchResults] = useState<
    CustomerSearchResult[]
  >([]);
  const [customerSearchLoading, setCustomerSearchLoading] = useState(false);
  const [customerSearchError, setCustomerSearchError] = useState<string | null>(
    null
  );
  const [contactColumnOrder, setContactColumnOrder] = useState<
    ContactColumnKey[]
  >(() => CONTACT_LINK_COLUMN_DEFS.map((def) => def.key));
  const draggingContactColumn = useRef<ContactColumnKey | null>(null);

  const rawCustomerId = watch("customer_id");
  const refsValue = watch("refs");
  const customerIdValue =
    typeof rawCustomerId === "number"
      ? rawCustomerId
      : Number.parseInt(String(rawCustomerId ?? 0), 10) || 0;
  const showCustomerSearchPanel = !isReadOnly && customerIdValue <= 0;

  useEffect(() => {
    setContactColumnOrder((prev) => {
      const knownKeys = CONTACT_LINK_COLUMN_DEFS.map((def) => def.key);
      const filtered = prev.filter((key): key is ContactColumnKey =>
        knownKeys.includes(key)
      );
      if (filtered.length === knownKeys.length) {
        return filtered;
      }
      const missing = knownKeys.filter((key) => !filtered.includes(key));
      return [...filtered, ...missing];
    });
  }, []);

  const orderedContactColumns = useMemo(() => {
    return contactColumnOrder
      .map((key) => CONTACT_LINK_COLUMN_LOOKUP[key])
      .filter((column): column is ContactLinkColumnDef => Boolean(column));
  }, [contactColumnOrder]);

  const handleContactColumnDragStart = useCallback(
    (key: ContactColumnKey) =>
      (event: ReactDragEvent<HTMLTableHeaderCellElement>) => {
        draggingContactColumn.current = key;
        event.dataTransfer.effectAllowed = "move";
      },
    []
  );

  const handleContactColumnDragOver = useCallback(
    (event: ReactDragEvent<HTMLTableHeaderCellElement>) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
    },
    []
  );

  const handleContactColumnDrop = useCallback(
    (targetKey: ContactColumnKey) =>
      (event: ReactDragEvent<HTMLTableHeaderCellElement>) => {
        event.preventDefault();
        const sourceKey = draggingContactColumn.current;
        if (!sourceKey || sourceKey === targetKey) {
          return;
        }
        setContactColumnOrder((prev) => {
          const next = [...prev];
          const sourceIndex = next.indexOf(sourceKey);
          const targetIndex = next.indexOf(targetKey);
          if (sourceIndex === -1 || targetIndex === -1) {
            return prev;
          }
          next.splice(sourceIndex, 1);
          next.splice(targetIndex, 0, sourceKey);
          return next;
        });
        draggingContactColumn.current = null;
      },
    []
  );

  const handleContactColumnDragEnd = useCallback(() => {
    draggingContactColumn.current = null;
  }, []);

  const contactLinkRows = useMemo<ContactLinkDisplayRow[]>(() => {
    if (!refsValue || typeof refsValue !== "object") {
      return [];
    }
    const container = refsValue as Record<string, unknown>;
    const links = container.links;
    if (!links || typeof links !== "object") {
      return [];
    }
    const contacts = (links as Record<string, unknown>).contact;
    if (!Array.isArray(contacts)) {
      return [];
    }
    return contacts
      .map((entry) =>
        typeof entry === "object" && entry
          ? (entry as ContactLinkRecord)
          : ({} as ContactLinkRecord)
      )
      .map((entry) => {
        const id = resolveContactId(entry);
        return {
          id,
          alias: resolveContactAlias(entry),
          name: resolveContactName(entry),
          role: resolveContactRole(entry),
          purpose: resolveContactPurpose(entry),
          email: resolveContactEmail(entry),
          phone: resolveContactPhone(entry),
          raw: entry,
        };
      });
  }, [refsValue]);

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
        const detail = await fetchInvoiceDetail(data.id);
        if (!cancelled) {
          setRecordData(detail as InvoiceForm & { id?: number });
        }
      } catch (error) {
        if (!cancelled) {
          const message =
            error instanceof Error
              ? error.message
              : "Failed to load sales order";
          dispatchToastError(message);
        }
      }
    };
    loadDetail();
    return () => {
      cancelled = true;
    };
  }, [data, dispatchToastError]);

  const handleCustomerSearchReset = useCallback(() => {
    setCustomerSearchKeyword("");
    setCustomerSearchId("");
    setCustomerSearchIda("");
    setCustomerSearchResults([]);
    setCustomerSearchError(null);
    setCustomerSearchLoading(false);
  }, []);

  const handleCustomerSearch = useCallback(
    async (event?: FormEvent<HTMLFormElement>) => {
      event?.preventDefault();
      if (isReadOnly) {
        return;
      }

      if (customerSearchLoading) {
        return;
      }

      const keyword = customerSearchKeyword.trim();
      const idaValue = customerSearchIda.trim();
      const rawId = customerSearchId.trim();
      const parsedId = rawId ? Number.parseInt(rawId, 10) : Number.NaN;

      if (!keyword && !idaValue && (Number.isNaN(parsedId) || parsedId <= 0)) {
        setCustomerSearchError("Enter a keyword, id, or ida value");
        setCustomerSearchResults([]);
        return;
      }

      setCustomerSearchLoading(true);
      setCustomerSearchError(null);

      try {
        const response = await searchCustomers({
          keyword: keyword || undefined,
          ida: idaValue || undefined,
          id: Number.isNaN(parsedId) || parsedId <= 0 ? undefined : parsedId,
          limit: 25,
        });
        const results = (response?.data?.results ??
          []) as CustomerSearchResult[];
        setCustomerSearchResults(results);
        if (results.length === 0) {
          setCustomerSearchError("No matching customers found");
        }
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Customer search failed";
        setCustomerSearchError(message);
        dispatchToastError(message);
      } finally {
        setCustomerSearchLoading(false);
      }
    },
    [
      customerSearchId,
      customerSearchIda,
      customerSearchKeyword,
      customerSearchLoading,
      dispatchToastError,
      isReadOnly,
    ]
  );

  const handleAssignCustomer = useCallback(
    (record: CustomerSearchResult) => {
      const resolvedId = resolveCustomerId(record);
      if (!resolvedId) {
        dispatchToastError("Unable to assign customer without an id");
        return;
      }

      setValue("customer_id", resolvedId, {
        shouldDirty: true,
        shouldValidate: true,
      });

      const label = resolveCustomerLabel(record);
      const existingCompany = watch("company");
      if ((!existingCompany || !String(existingCompany).trim()) && label) {
        setValue("company", label, {
          shouldDirty: true,
          shouldValidate: false,
        });
      }

      handleCustomerSearchReset();
      dispatch(
        showToast({
          message: `Customer #${resolvedId} assigned`,
          type: "success",
        })
      );
    },
    [dispatch, dispatchToastError, handleCustomerSearchReset, setValue, watch]
  );

  const mergedDefaults = useMemo(() => {
    if (!recordData) {
      return DEFAULT_FORM_VALUES;
    }

    const recordContainer = recordData as Record<string, unknown>;

    const resolvedCustomerId = extractNumericId(
      recordContainer.customer_id ?? recordContainer.id_customer
    );
    const resolvedManufacturerId = extractNumericId(
      recordContainer.manufacturer_id ?? recordContainer.id_manufacturer
    );
    const resolvedVendorId = extractNumericId(
      recordContainer.vendor_id ?? recordContainer.id_vendor
    );
    const resolvedIda = (() => {
      const candidates = [
        recordContainer.ida,
        recordContainer.invoice_no,
        recordContainer.ida_sales_order,
      ];
      for (const candidate of candidates) {
        if (typeof candidate === "string" && candidate.trim()) {
          return candidate.trim();
        }
      }
      return DEFAULT_FORM_VALUES.ida;
    })();

    return {
      ...DEFAULT_FORM_VALUES,
      ...recordData,
      ida: resolvedIda,
      customer_id: resolvedCustomerId ?? DEFAULT_FORM_VALUES.customer_id,
      manufacturer_id:
        resolvedManufacturerId ?? DEFAULT_FORM_VALUES.manufacturer_id,
      vendor_id: resolvedVendorId ?? DEFAULT_FORM_VALUES.vendor_id,
      metadata: {
        ...DEFAULT_FORM_VALUES.metadata,
        ...(typeof recordData.metadata === "object" && recordData.metadata
          ? recordData.metadata
          : {}),
      },
      prefs: {
        ...DEFAULT_FORM_VALUES.prefs,
        ...(typeof recordData.prefs === "object" && recordData.prefs
          ? recordData.prefs
          : {}),
      },
      refs: {
        ...DEFAULT_FORM_VALUES.refs,
        ...(typeof recordData.refs === "object" && recordData.refs
          ? recordData.refs
          : {}),
      },
      cost:
        typeof recordData.cost === "object" && recordData.cost
          ? recordData.cost
          : {},
      sell:
        typeof recordData.sell === "object" && recordData.sell
          ? recordData.sell
          : {},
      finance:
        typeof recordData.finance === "object" && recordData.finance
          ? recordData.finance
          : {},
      flow:
        typeof recordData.flow === "object" && recordData.flow
          ? recordData.flow
          : {},
      source:
        typeof recordData.source === "object" && recordData.source
          ? recordData.source
          : {},
      subtotals:
        typeof recordData.subtotals === "object" && recordData.subtotals
          ? recordData.subtotals
          : {},
      lines: normalizeLines(recordContainer.lines),
    } as InvoiceForm;
  }, [recordData]);

  useEffect(() => {
    reset(mergedDefaults);
    const drafts: Partial<Record<JsonFieldPath, string>> = {};
    JSON_FIELD_PATHS.forEach((path) => {
      drafts[path] = serializeJson(
        extractValue(mergedDefaults as Record<string, unknown>, path)
      );
      setValue(
        path as any,
        extractValue(mergedDefaults as Record<string, unknown>, path) as any
      );
    });
    setJsonDrafts(
      (prev) => ({ ...prev, ...drafts } as Record<JsonFieldPath, string>)
    );
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
    setValue("lines" as any, clonedLines as any, {
      shouldDirty: false,
      shouldValidate: false,
    });
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
        extractValue(
          line as Record<string, unknown>,
          "price.discount_amount"
        ) ?? extractValue(line as Record<string, unknown>, "discount_amount")
      );
      if (!lineDiscount) {
        const discountPercent = toNumeric(
          extractValue(
            line as Record<string, unknown>,
            "price.discount_percent"
          )
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
      const lineSellBeforeTax =
        extractedExtended || Math.max(lineSubtotal - lineDiscount, 0);
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
      const lineCost =
        extractedCostExtended ||
        (unitCost && quantity ? unitCost * quantity : unitCost);

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

  const handleAddSearchedItem = useCallback(
    (item: ItemSearchResult, rawQuantity: number) => {
      const quantity =
        Number.isFinite(rawQuantity) && rawQuantity > 0 ? rawQuantity : 0;
      if (!quantity) {
        return;
      }
      const identifier = resolveItemKey(item) || resolveItemCode(item) || "";

      setLineDrafts((previousLines) => {
        const currentLines = Array.isArray(previousLines) ? previousLines : [];
        const existingIndex = identifier
          ? currentLines.findIndex(
              (line) => resolveLineKey(line) === identifier
            )
          : -1;

        if (existingIndex >= 0) {
          const nextLines = currentLines.map((line, index) => {
            if (index !== existingIndex) {
              return line;
            }
            const updated = cloneLine(line);
            const container = updated as Record<string, unknown>;

            const resolvedQuantity = (() => {
              if (typeof container.quantity === "number") {
                return {
                  placed: toNumeric(container.quantity),
                  ordered: toNumeric(container.quantity),
                  remaining: 0,
                } as Record<string, unknown>;
              }
              if (
                container.quantity &&
                typeof container.quantity === "object"
              ) {
                return { ...(container.quantity as Record<string, unknown>) };
              }
              return {} as Record<string, unknown>;
            })();

            const previousPlaced = toNumeric(
              extractValue(resolvedQuantity, "placed") ??
                resolvedQuantity.placed
            );
            const previousOrdered = Math.max(
              previousPlaced,
              toNumeric(
                extractValue(resolvedQuantity, "ordered") ??
                  resolvedQuantity.ordered
              )
            );
            const nextPlaced = previousPlaced + quantity;
            const nextOrdered = previousOrdered + quantity;

            resolvedQuantity.placed = nextPlaced;
            resolvedQuantity.ordered = nextOrdered;
            resolvedQuantity.remaining = Math.max(nextOrdered - nextPlaced, 0);
            container.quantity = resolvedQuantity;

            const priceRaw = container.price;
            const priceObject =
              priceRaw && typeof priceRaw === "object"
                ? { ...(priceRaw as Record<string, unknown>) }
                : {
                    unit: 0,
                    sell: 0,
                    discount_amount: 0,
                    discount_percent: 0,
                    precision: 2,
                  };
            if (!toNumeric(priceObject.unit)) {
              priceObject.unit = resolveUnitPrice(item);
            }
            if (!toNumeric(priceObject.sell)) {
              priceObject.sell = priceObject.unit;
            }
            if (
              (priceObject as Record<string, any>).discount_amount === undefined
            ) {
              (priceObject as Record<string, any>).discount_amount = 0;
            }
            if (
              (priceObject as Record<string, any>).discount_percent ===
              undefined
            ) {
              (priceObject as Record<string, any>).discount_percent = 0;
            }
            if ((priceObject as Record<string, any>).precision === undefined) {
              (priceObject as Record<string, any>).precision = 2;
            }
            container.price = priceObject;

            const costRaw = container.cost;
            const costObject =
              costRaw && typeof costRaw === "object"
                ? { ...(costRaw as Record<string, unknown>) }
                : { unit: resolveUnitCost(item), precision: 2 };
            if (!toNumeric(costObject.unit)) {
              costObject.unit = resolveUnitCost(item);
            }
            if ((costObject as Record<string, any>).precision === undefined) {
              (costObject as Record<string, any>).precision = 2;
            }
            container.cost = costObject;

            recalculateLineFinancials(updated);
            return updated;
          });

          setValue("lines" as any, nextLines as any, {
            shouldDirty: true,
            shouldValidate: false,
          });
          return nextLines;
        }

        const nextLines = [...currentLines, buildLineFromItem(item, quantity)];
        setValue("lines" as any, nextLines as any, {
          shouldDirty: true,
          shouldValidate: false,
        });
        return nextLines;
      });
    },
    [setValue]
  );

  const handleLineFieldChange = useCallback(
    (
      index: number,
      field: "quantity.placed" | "price.unit",
      rawValue: number
    ) => {
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

        setValue("lines" as any, next as any, {
          shouldDirty: true,
          shouldValidate: false,
        });
        return next;
      });
    },
    [setValue]
  );

  useEffect(() => {
    setValue("subtotal", aggregatedFinancials.subtotal, {
      shouldDirty: false,
      shouldValidate: false,
    });
    setValue("discount", aggregatedFinancials.discount, {
      shouldDirty: false,
      shouldValidate: false,
    });
    setValue("tax", aggregatedFinancials.tax, {
      shouldDirty: false,
      shouldValidate: false,
    });
    setValue("total", aggregatedFinancials.total, {
      shouldDirty: false,
      shouldValidate: false,
    });
    setValue("cost" as any, aggregatedFinancials.costDetails as any, {
      shouldDirty: false,
      shouldValidate: false,
    });
    setValue("sell" as any, aggregatedFinancials.sellDetails as any, {
      shouldDirty: false,
      shouldValidate: false,
    });

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

  const applyJsonDraftsToPayload = (payload: InvoiceForm) => {
    JSON_FIELD_PATHS.forEach((path) => {
      const draft = jsonDrafts[path];
      if (!draft || !draft.trim()) {
        setDeepValue(
          payload as unknown as Record<string, unknown>,
          path,
          undefined
        );
        return;
      }
      try {
        const parsed = JSON.parse(draft);
        setDeepValue(
          payload as unknown as Record<string, unknown>,
          path,
          parsed
        );
      } catch (error) {
        throw new Error(`Invalid JSON for ${path}`);
      }
    });
  };

  const onSubmit = async (formData: InvoiceForm) => {
    const linesForSync = Array.isArray(formData.lines)
      ? formData.lines.map((line) => cloneLine(line))
      : [];

    try {
      applyJsonDraftsToPayload(formData);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Invalid JSON payload";
      dispatchToastError(message);
      return;
    }

    try {
      const { lines: _unsentLines, ...rest } = formData;
      const orderPayload = JSON.parse(JSON.stringify(rest)) as Record<
        string,
        unknown
      >;
      delete orderPayload.ida;
      delete orderPayload.id_customer;
      delete orderPayload.id_vendor;
      delete orderPayload.id_manufacturer;
      const saveResult =
        mode === "add"
          ? await createInvoice(orderPayload)
          : await (async () => {
              const existingId = extractNumericId(recordData?.id);
              if (!existingId) {
                throw new Error("Sales order id missing");
              }
              return updateInvoice(existingId, orderPayload);
            })();

      const orderIdCandidates: unknown[] = [
        (saveResult as Record<string, unknown>)?.id,
        (
          (saveResult as Record<string, unknown>)?.record as Record<
            string,
            unknown
          >
        )?.id,
        (
          (saveResult as Record<string, unknown>)?.data as Record<
            string,
            unknown
          >
        )?.id,
        (
          (
            (saveResult as Record<string, unknown>)?.data as Record<
              string,
              unknown
            >
          )?.record as Record<string, unknown>
        )?.id,
        recordData?.id,
        (formData as unknown as Record<string, unknown>)?.id,
      ];

      const resolvedOrderId = orderIdCandidates.reduce<number | null>(
        (acc, value) => {
          if (acc) {
            return acc;
          }
          return extractNumericId(value);
        },
        null
      );

      if (!resolvedOrderId) {
        throw new Error("Sales order id missing after save");
      }

      const originalLineIds = new Set<number>();
      lineItems.forEach((line) => {
        const existingId = resolveLineId(line);
        if (existingId) {
          originalLineIds.add(existingId);
        }
      });

      const retainedLineIds = new Set<number>();
      const lineOperations: Promise<unknown>[] = [];

      linesForSync.forEach((line) => {
        if (!line || typeof line !== "object") {
          return;
        }
        const payload = line as Record<string, unknown>;
        const lineId = resolveLineId(line);
        payload.parent = resolvedOrderId;
        if (lineId) {
          retainedLineIds.add(lineId);
          payload.id = lineId;
        } else {
          delete payload.id;
        }
        lineOperations.push(
          (async () => {
            await saveRecord(
              "sales_order_line",
              JSON.parse(JSON.stringify(payload))
            );
          })()
        );
      });

      originalLineIds.forEach((lineId) => {
        if (!retainedLineIds.has(lineId)) {
          lineOperations.push(
            (async () => {
              await deleteRecord("sales_order_line", lineId);
            })()
          );
        }
      });

      if (lineOperations.length > 0) {
        const results = await Promise.allSettled(lineOperations);
        const rejected = results.find((result) => result.status === "rejected");
        if (rejected && rejected.status === "rejected") {
          throw rejected.reason instanceof Error
            ? rejected.reason
            : new Error("Failed syncing line items");
        }
      }

      try {
        const refreshed = await fetchInvoiceDetail(resolvedOrderId);
        if (refreshed && typeof refreshed === "object") {
          setRecordData(refreshed as InvoiceForm & { id?: number });
        }
      } catch {
        // Best-effort refresh; ignore errors so a successful save is not blocked.
      }

      dispatch(
        showToast({
          message: `Sales order ${
            mode === "add" ? "created" : "updated"
          } successfully`,
          type: "success",
        })
      );
      if (onSaved) {
        onSaved();
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Operation failed";
      dispatchToastError(message);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!recordData?.id) {
      return;
    }
    try {
      await updateInvoice(recordData.id, {
        ...mergedDefaults,
        status: newStatus,
      });
      dispatch(
        showToast({
          message: `Sales order marked as ${newStatus}`,
          type: "success",
        })
      );
      if (onSaved) {
        onSaved();
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to update status";
      dispatchToastError(message);
    }
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
              {mode === "edit"
                ? "Edit Sales Order"
                : mode === "view"
                ? "View Sales Order"
                : "Add Sales Order"}
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

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {showCustomerSearchPanel && (
            <section className="rounded-lg border border-dashed border-blue-300 bg-blue-50/60 p-4 dark:border-blue-500/50 dark:bg-blue-900/10">
              <h4 className="text-sm font-semibold uppercase tracking-wide text-blue-800 dark:text-blue-200">
                Assign customer
              </h4>
              <p className="mt-1 text-xs text-blue-700 dark:text-blue-300">
                No customer is linked to this order. Search by keyword, id, or
                ida to attach one.
              </p>
              <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-4">
                <div>
                  <Label htmlFor="customer-search-keyword">keyword</Label>
                  <input
                    id="customer-search-keyword"
                    type="text"
                    value={customerSearchKeyword}
                    onChange={(event) =>
                      setCustomerSearchKeyword(event.target.value)
                    }
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        handleCustomerSearch();
                      }
                    }}
                    placeholder="Company, name, or tag"
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-hidden focus:ring-2 focus:ring-blue-200 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <Label htmlFor="customer-search-id">id</Label>
                  <input
                    id="customer-search-id"
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    value={customerSearchId}
                    onChange={(event) =>
                      setCustomerSearchId(
                        event.target.value.replace(/[^0-9]/g, "")
                      )
                    }
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        handleCustomerSearch();
                      }
                    }}
                    placeholder="Internal id"
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-hidden focus:ring-2 focus:ring-blue-200 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <Label htmlFor="customer-search-ida">ida</Label>
                  <input
                    id="customer-search-ida"
                    type="text"
                    value={customerSearchIda}
                    onChange={(event) =>
                      setCustomerSearchIda(event.target.value)
                    }
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        handleCustomerSearch();
                      }
                    }}
                    placeholder="Legacy identifier"
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-hidden focus:ring-2 focus:ring-blue-200 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                  />
                </div>
                <div className="flex items-end gap-2">
                  <button
                    type="button"
                    onClick={() => handleCustomerSearch()}
                    className="h-10 flex-1 rounded-md bg-blue-500 px-4 text-sm font-medium text-white hover:bg-blue-600 focus:outline-hidden focus:ring-2 focus:ring-blue-400 disabled:cursor-not-allowed disabled:bg-blue-400"
                    disabled={customerSearchLoading}
                  >
                    {customerSearchLoading ? "Searching…" : "Search"}
                  </button>
                  <button
                    type="button"
                    onClick={handleCustomerSearchReset}
                    className="h-10 rounded-md border border-blue-200 px-4 text-sm font-medium text-blue-700 hover:bg-blue-100 focus:outline-hidden focus:ring-2 focus:ring-blue-200 disabled:cursor-not-allowed dark:border-blue-500/60 dark:text-blue-200 dark:hover:bg-blue-900/30"
                    disabled={customerSearchLoading}
                  >
                    Clear
                  </button>
                </div>
              </div>
              {customerSearchError && (
                <div className="mt-3 rounded-md border border-error-200 bg-error-50 px-3 py-2 text-xs text-error-700 dark:border-error-500/60 dark:bg-error-900/20 dark:text-error-200">
                  {customerSearchError}
                </div>
              )}
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-blue-100 text-blue-900 dark:bg-blue-900/40 dark:text-blue-100">
                    <tr>
                      <th className="px-3 py-2 font-medium uppercase tracking-wide text-xs">
                        id
                      </th>
                      <th className="px-3 py-2 font-medium uppercase tracking-wide text-xs">
                        ida
                      </th>
                      <th className="px-3 py-2 font-medium uppercase tracking-wide text-xs">
                        display_name
                      </th>
                      <th className="px-3 py-2 font-medium uppercase tracking-wide text-xs">
                        org_type
                      </th>
                      <th className="px-3 py-2 font-medium uppercase tracking-wide text-xs">
                        status
                      </th>
                      <th className="px-3 py-2 font-medium uppercase tracking-wide text-xs">
                        contact
                      </th>
                      <th className="px-3 py-2 font-medium uppercase tracking-wide text-xs text-right">
                        actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {customerSearchLoading ? (
                      <tr>
                        <td
                          className="px-3 py-3 text-center text-sm text-blue-700 dark:text-blue-200"
                          colSpan={7}
                        >
                          Looking for customers…
                        </td>
                      </tr>
                    ) : customerSearchResults.length === 0 ? (
                      <tr>
                        <td
                          className="px-3 py-3 text-center text-sm text-gray-500 dark:text-gray-400"
                          colSpan={7}
                        >
                          Enter criteria above and run a search to locate a
                          customer.
                        </td>
                      </tr>
                    ) : (
                      customerSearchResults.map((record, index) => {
                        const resolvedId = resolveCustomerId(record);
                        const alias = resolveCustomerAlias(record);
                        const label = resolveCustomerLabel(record);
                        const orgType = resolveStringField(record, [
                          "org_type",
                          "type",
                          "category",
                        ]);
                        const status = resolveStringField(record, [
                          "status",
                          "state",
                        ]);
                        const email = resolveStringField(record, [
                          "email",
                          "contact_email",
                          "primary_email",
                        ]);
                        const phone = resolveStringField(record, [
                          "phone",
                          "phoneCell",
                          "phone_primary",
                          "phone_number",
                        ]);
                        const rowKey = resolvedId
                          ? `customer-${resolvedId}`
                          : `customer-row-${index}`;
                        return (
                          <tr
                            key={rowKey}
                            className="border-b border-blue-100 last:border-none dark:border-blue-900/40"
                          >
                            <td className="px-3 py-2 text-gray-800 dark:text-gray-100">
                              {resolvedId ?? "--"}
                            </td>
                            <td className="px-3 py-2 text-gray-600 dark:text-gray-300">
                              {alias || "--"}
                            </td>
                            <td className="px-3 py-2 text-gray-800 dark:text-gray-100">
                              {label}
                            </td>
                            <td className="px-3 py-2 text-gray-600 dark:text-gray-300">
                              {orgType || "--"}
                            </td>
                            <td className="px-3 py-2 text-gray-600 dark:text-gray-300">
                              {status || "--"}
                            </td>
                            <td className="px-3 py-2 text-gray-600 dark:text-gray-300">
                              {email && <div>{email}</div>}
                              {phone && <div>{phone}</div>}
                              {!email && !phone && "--"}
                            </td>
                            <td className="px-3 py-2 text-right">
                              <button
                                type="button"
                                onClick={() => handleAssignCustomer(record)}
                                disabled={!resolvedId}
                                className="rounded-md bg-green-500 px-3 py-1 text-sm font-medium text-white hover:bg-green-600 focus:outline-hidden focus:ring-2 focus:ring-green-400 disabled:cursor-not-allowed disabled:bg-gray-400 dark:disabled:bg-gray-700"
                              >
                                Assign
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
            <div>
              <Label htmlFor="ida">ida</Label>
              <Input
                type="text"
                id="ida"
                placeholder="Invoice Number"
                {...register("ida")}
                error={Boolean(errors.ida?.message)}
                hint={errors.ida?.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="status">status</Label>
              <select
                id="status"
                {...register("status")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                <option value="draft">Draft</option>
                <option value="sent">Sent</option>
                <option value="paid">Paid</option>
                <option value="overdue">Overdue</option>
                <option value="cancelled">Cancelled</option>
              </select>
              {errors.status && (
                <p className="text-red-500 text-sm">{errors.status.message}</p>
              )}
            </div>

            <div>
              <Label htmlFor="company">company</Label>
              <Input
                type="text"
                id="company"
                placeholder="Company"
                {...register("company")}
                error={Boolean(errors.company?.message)}
                hint={errors.company?.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="attention">attention</Label>
              <Input
                type="text"
                id="attention"
                placeholder="Attention"
                {...register("attention")}
                error={Boolean(errors.attention?.message)}
                hint={errors.attention?.message}
                disabled={mode === "view"}
              />
            </div>

            <div>
              <Label htmlFor="address1">address1</Label>
              <Input
                type="text"
                id="address1"
                placeholder="Address line 1"
                {...register("address1")}
                error={Boolean(errors.address1?.message)}
                hint={errors.address1?.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="address2">address2</Label>
              <Input
                type="text"
                id="address2"
                placeholder="Address line 2"
                {...register("address2")}
                disabled={mode === "view"}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
            <div>
              <Label htmlFor="city">city</Label>
              <Input
                type="text"
                id="city"
                placeholder="City"
                {...register("city")}
                error={Boolean(errors.city?.message)}
                hint={errors.city?.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="state">state</Label>
              <Input
                type="text"
                id="state"
                placeholder="State"
                {...register("state")}
                error={Boolean(errors.state?.message)}
                hint={errors.state?.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="zip">zip</Label>
              <Input
                type="text"
                id="zip"
                placeholder="Zip"
                {...register("zip")}
                error={Boolean(errors.zip?.message)}
                hint={errors.zip?.message}
                disabled={mode === "view"}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
            <div>
              <Label htmlFor="email">email</Label>
              <Input
                type="email"
                id="email"
                placeholder="Email"
                {...register("email")}
                error={Boolean(errors.email?.message)}
                hint={errors.email?.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="phoneCell">phoneCell</Label>
              <Input
                type="text"
                id="phoneCell"
                placeholder="Cell Phone"
                {...register("phoneCell")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="phone">phone</Label>
              <Input
                type="text"
                id="phone"
                placeholder="Phone"
                {...register("phone")}
                disabled={mode === "view"}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <Label htmlFor="actionBy">actionBy</Label>
              <Input
                type="text"
                id="actionBy"
                placeholder="Action By"
                {...register("actionBy")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="action">action</Label>
              <Input
                type="text"
                id="action"
                placeholder="Action"
                {...register("action")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="actionDate">actionDate</Label>
              <Input
                type="date"
                id="actionDate"
                {...register("actionDate")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="actionTime">actionTime</Label>
              <Input
                type="time"
                id="actionTime"
                {...register("actionTime")}
                disabled={mode === "view"}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <Label htmlFor="salesName">salesName</Label>
              <Input
                type="text"
                id="salesName"
                placeholder="Sales Name"
                {...register("salesName")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="orderedBy">orderedBy</Label>
              <Input
                type="text"
                id="orderedBy"
                placeholder="Ordered By"
                {...register("orderedBy")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="contractDetailTag">contractDetailTag</Label>
              <Input
                type="text"
                id="contractDetailTag"
                placeholder="Contract Detail"
                {...register("contractDetailTag")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="terms">terms</Label>
              <Input
                type="text"
                id="terms"
                placeholder="Terms"
                {...register("terms")}
                disabled={mode === "view"}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
            <div>
              <Label htmlFor="typeSale">typeSale</Label>
              <Input
                type="text"
                id="typeSale"
                placeholder="Type of Sale"
                {...register("typeSale")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="taxJuris">taxJuris</Label>
              <Input
                type="text"
                id="taxJuris"
                placeholder="Tax Jurisdiction"
                {...register("taxJuris")}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="adSource">adSource</Label>
              <Input
                type="text"
                id="adSource"
                placeholder="Ad Source"
                {...register("adSource")}
                disabled={mode === "view"}
              />
            </div>
          </div>

          <div>
            <Label htmlFor="addComment">addComment</Label>
            <TextArea
              rows={3}
              placeholder="Add comment"
              register={register("addComment")}
              disabled={mode === "view"}
              error={errors.addComment}
              hint={errors.addComment?.message}
            />
          </div>

          <div className="flex items-center justify-between">
            <h4 className="font-semibold text-gray-800 dark:text-white">
              Notes
            </h4>
            {mode !== "view" && (
              <button
                type="button"
                onClick={() => setIsNotesLocked((prev) => !prev)}
                className="px-3 py-1 text-sm rounded-md border border-gray-300 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:border-gray-700"
              >
                {isNotesLocked ? "Edit" : "Lock"}
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <Label htmlFor="comment">comment</Label>
              <TextArea
                rows={4}
                placeholder="Comment"
                register={register("comment")}
                disabled={mode === "view" || isNotesLocked}
                error={errors.comment}
                hint={errors.comment?.message}
              />
            </div>
            <div>
              <Label htmlFor="contractDetail">contractDetail</Label>
              <TextArea
                rows={4}
                placeholder="Contract Detail"
                register={register("contractDetail")}
                disabled={mode === "view" || isNotesLocked}
                error={errors.contractDetail}
                hint={errors.contractDetail?.message}
              />
            </div>
          </div>

          <section>
            <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-300">
              refs.links.contact
            </h4>
            <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-gray-50 text-gray-700 dark:bg-gray-800 dark:text-gray-100">
                  <tr>
                    {orderedContactColumns.map((column) => (
                      <th
                        key={column.key}
                        draggable
                        onDragStart={handleContactColumnDragStart(column.key)}
                        onDragOver={handleContactColumnDragOver}
                        onDrop={handleContactColumnDrop(column.key)}
                        onDragEnd={handleContactColumnDragEnd}
                        className="px-3 py-2 font-medium uppercase tracking-wide text-xs"
                      >
                        <span className="flex items-center gap-1">
                          <span>{column.label}</span>
                          <span className="text-[10px] text-gray-400">↕</span>
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {contactLinkRows.length === 0 ? (
                    <tr>
                      <td
                        colSpan={orderedContactColumns.length || 1}
                        className="px-3 py-3 text-center text-sm text-gray-500 dark:text-gray-400"
                      >
                        No linked contacts.
                      </td>
                    </tr>
                  ) : (
                    contactLinkRows.map((row, index) => (
                      <tr
                        key={`contact-row-${index}`}
                        className="border-b border-gray-100 last:border-none dark:border-gray-700"
                      >
                        {orderedContactColumns.map((column) => (
                          <td
                            key={column.key}
                            className={CONTACT_LINK_CELL_CLASS[column.key]}
                          >
                            {column.render(row)}
                          </td>
                        ))}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {mode === "view" && recordData?.id && (
            <section className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div>
                <Label>dt_created</Label>
                <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300">
                  {mergedDefaults.dt_created
                    ? new Date(
                        Number(mergedDefaults.dt_created) *
                          (String(mergedDefaults.dt_created).length === 13
                            ? 1
                            : 1000)
                      ).toLocaleString()
                    : "--"}
                </div>
              </div>
              <div>
                <Label>dt_modified</Label>
                <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300">
                  {mergedDefaults.dt_modified
                    ? new Date(
                        Number(mergedDefaults.dt_modified) *
                          (String(mergedDefaults.dt_modified).length === 13
                            ? 1
                            : 1000)
                      ).toLocaleString()
                    : "--"}
                </div>
              </div>
              <div>
                <Label>Audit</Label>
                <AuditTrail transactionId={recordData.id} model="sales_order" />
              </div>
              <div>
                <Label>Status flow</Label>
                <InvoiceStatus
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

      {!isReadOnly && (
        <ComponentCard>
          <div className="mb-4">
            <h3 className="text-lg font-semibold dark:text-white">Add Items</h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Search the catalog and append matching items to this sales order.
            </p>
          </div>
          <InvoiceItemSearch onAddItem={handleAddSearchedItem} />
        </ComponentCard>
      )}

      <InvoiceLinesPanel
        lines={lineDrafts}
        isReadOnly={isReadOnly}
        onFieldChange={isReadOnly ? undefined : handleLineFieldChange}
      />
    </>
  );
}
