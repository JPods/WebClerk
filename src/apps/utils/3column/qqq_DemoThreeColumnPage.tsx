/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect, useMemo, useState } from "react";
import { getModelDetail, getModelNames } from "../../../api/wcapi";
import type { ModelDetailPayload } from "../../../api/wcapi";
import { AdminThreeColumn } from "./AdminThreeColumn";
import { demoThreeColumnConfig } from "./sampleData";
import { createWcapiDataSource } from "./wcapiDataSource";
import type { AdminAppDefinition, AdminFieldDescriptor, AdminTableDefinition, AdminWorkspaceConfig } from "./types";

type ModelField = {
  name: string;
  type?: string;
  verbose_name?: string;
  help_text?: string;
  read_only?: boolean;
  editable?: boolean;
  required?: boolean;
  blank?: boolean;
  allow_blank?: boolean;
  null?: boolean;
  allow_null?: boolean;
  has_default?: boolean;
  default?: unknown;
  choices?: unknown;
  locked_to_entry?: boolean;
};

const SAMPLE_WORKSPACE_CONFIG: AdminWorkspaceConfig = {
  apps: demoThreeColumnConfig,
  storageKey: "webclerk:demo:3column",
  defaultPageSize: 15,
  pageSizeOptions: [10, 15, 25, 50],
};

const KNOWN_APP_MODEL_MAP: Record<string, string[]> = {
  accounts: [
    "Audit",
    "Currency",
    "ExchangeRate",
    "ExchangeTransaction",
    "GlAccount",
    "GlJournal",
    "Ledger",
    "TaxJurisdiction",
    "Term",
  ],
  communications: ["Address", "Domain", "Email", "Phone"],
  core: [
    "Action",
    "AuditLog",
    "Contact",
    "Notification",
    "Pending",
    "Report",
    "Setting",
    "SoftDeleteLedger",
    "Template",
  ],
  docs: ["Document", "QuestionAnswer", "Tag"],
  orgs: ["Customer", "Employee", "Manufacturer", "OrgBase", "Rep", "Vendor"],
  products: [
    "BillOfMaterial",
    "Catalog",
    "CatalogLine",
    "DeliveryLine",
    "DeliveryVisit",
    "InventoryAdjustmentProcessorRun",
    "InventoryCheck",
    "InventoryCheckLine",
    "InventoryLayer",
    "InventoryMetricsSnapshot",
    "InventoryMovement",
    "InventoryReservation",
    "Item",
    "ItemUsage",
    "ItemXRef",
    "OrgItem",
    "PendingInventoryAdjustment",
    "Serial",
    "SerialLog",
    "Service",
    "SiteInventory",
    "Specification",
    "Variant",
    "Warehouse",
  ],
  support: ["Campaign"],
  sync: ["Bundle", "Connection"],
  transactions: [
    "Invoice",
    "InvoiceLine",
    "Payment",
    "PaymentApplication",
    "PaymentMethod",
    "PaymentTerm",
    "Project",
    "ProjectAssociation",
    "Proposal",
    "ProposalLine",
    "Purchase",
    "PurchaseLine",
    "PurchaseReceipt",
    "Requisition",
    "RequisitionLine",
    "Order",
    "OrderLine",
    "WorkOrder",
    "WorkOrderLine",
  ],
};

const PREFERRED_APP_ORDER = Object.keys(KNOWN_APP_MODEL_MAP);

const normalizeSegment = (value: string) => value.replace(/[^a-z0-9]/gi, "").toLowerCase();

const normalizeModelKey = (appId: string, modelName: string) => `${normalizeSegment(appId)}.${normalizeSegment(modelName)}`;

const normalizeFullModelName = (value: string) => {
  const [appPart, ...rest] = value.split(".");
  if (rest.length === 0) {
    return normalizeSegment(value);
  }
  const modelPart = rest.join(".");
  return `${normalizeSegment(appPart)}.${normalizeSegment(modelPart)}`;
};

const PREFERRED_MODEL_SEQUENCE = Object.entries(KNOWN_APP_MODEL_MAP).flatMap(([appId, models]) =>
  models.map((modelName) => `${appId}.${modelName}`)
);

const PREFERRED_MODEL_KEY_SET = new Set(
  Object.entries(KNOWN_APP_MODEL_MAP).flatMap(([appId, models]) =>
    models.map((modelName) => normalizeModelKey(appId, modelName))
  )
);

const toTitle = (value: string) =>
  value
    .replace(/[_\-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^(.)|\s+(.)/g, (match) => match.toUpperCase());

const guessFieldKind = (type?: string): AdminFieldDescriptor["kind"] => {
  if (!type) {
    return "text";
  }
  const normalized = type.toLowerCase();
  if (normalized.includes("boolean")) {
    return "boolean";
  }
  if (normalized.includes("date") && normalized.includes("time")) {
    return "datetime";
  }
  if (normalized.includes("date")) {
    return "date";
  }
  if (normalized.includes("email")) {
    return "email";
  }
  if (normalized.includes("url")) {
    return "url";
  }
  if (normalized.includes("json")) {
    return "json";
  }
  if (normalized.includes("decimal") || normalized.includes("money")) {
    return "currency";
  }
  if (normalized.includes("int") || normalized.includes("number")) {
    return "integer";
  }
  if (normalized.includes("choice") || normalized.includes("enum") || normalized.includes("status")) {
    return "tag";
  }
  if (normalized.includes("foreign") || normalized.includes("relation")) {
    return "relation";
  }
  return "text";
};

const normalizeFields = (fields: unknown): ModelField[] => {
  if (Array.isArray(fields)) {
    return fields
      .map((field) => {
        if (typeof field === "string") {
          return { name: field };
        }
        if (field && typeof field === "object" && "name" in field) {
          return field as ModelField;
        }
        return null;
      })
      .filter((field): field is ModelField => Boolean(field?.name));
  }
  if (fields && typeof fields === "object") {
    return Object.keys(fields as Record<string, unknown>).map((name) => ({ name }));
  }
  return [];
};

const buildFieldDescriptors = (fields: ModelField[]): AdminFieldDescriptor[] =>
  fields.map((field) => {
    const label = field.name;
    const kind = guessFieldKind(field.type);
    const rawChoices = field.choices;
    const hasChoices = Array.isArray(rawChoices)
      ? rawChoices.length > 0
      : rawChoices && typeof rawChoices === "object"
      ? Object.keys(rawChoices as Record<string, unknown>).length > 0
      : false;
    const required =
      field.required === true ||
      field.blank === false ||
      field.allow_blank === false ||
      field.null === false ||
      field.allow_null === false;
    const isEditable = field.read_only === true ? false : field.editable === false ? false : true;
    const locked = field.locked_to_entry === true || field.read_only === true || isEditable === false;
    return {
      id: field.name,
      label,
      kind,
      description: field.help_text || field.verbose_name,
      sortable: true,
      filterable: kind !== "json",
      searchable: kind === "text" || kind === "email",
      editable: isEditable,
      readOnly: field.read_only === true,
      required,
      hasChoices,
      locked,
    } satisfies AdminFieldDescriptor;
  });

const buildTableDefinition = (model: ModelDetailPayload["model"]): AdminTableDefinition | null => {
  const modelName = model?.model_name;
  if (!modelName) {
    return null;
  }

  const primaryKey = (model?.pk_field || model?.primary_key || model?.pk || "id") as string;
  const fields = buildFieldDescriptors(normalizeFields(model?.fields)).filter((field, index, arr) => {
    return arr.findIndex((candidate) => candidate.id === field.id) === index;
  });

  if (fields.length === 0) {
    return null;
  }

  const defaultListFields = Array.from(
    new Set([
      primaryKey,
      ...fields
        .filter((field) => field.id !== primaryKey && field.kind !== "json")
        .slice(0, 5)
        .map((field) => field.id),
    ])
  );

  return {
    id: modelName,
    label: modelName,
    description: model?.verbose_name || model?.object_name || model?.verbose_name_plural,
    primaryKey,
    fields,
    defaultListFields,
    defaultDetailFields: fields.map((field) => field.id),
    dataSource: createWcapiDataSource({
      modelName,
      primaryKeyField: primaryKey,
    }),
    pageSizeOptions: [10, 25, 50, 100],
    defaultPageSize: 25,
  } satisfies AdminTableDefinition;
};

const getNormalizedTableKey = (appId: string, tableId: string) => {
  const parts = tableId.split(".");
  const modelSegment = parts.length > 1 ? parts[parts.length - 1] : tableId;
  return normalizeModelKey(appId, modelSegment);
};

const buildApps = (models: ModelDetailPayload["model"][]): AdminAppDefinition[] => {
  const appsMap = new Map<string, AdminAppDefinition>();

  models.forEach((model) => {
    const table = buildTableDefinition(model);
    if (!table) {
      return;
    }

    const rawAppId = (model?.app_label || model?.app || model?.app_label_name || model?.app_label_verbose) as string | undefined;
    const fallbackAppId = model?.model_name?.split(".")[0] ?? "default";
    const appId = (rawAppId || fallbackAppId || "default").toLowerCase();
    const appLabel = toTitle(rawAppId || fallbackAppId || "Default");

    if (!appsMap.has(appId)) {
      appsMap.set(appId, {
        id: appId,
        label: appLabel,
        tables: [],
      });
    }

    appsMap.get(appId)?.tables.push(table);
  });

  const apps = Array.from(appsMap.values())
    .map((app) => {
      const preferredModels = KNOWN_APP_MODEL_MAP[app.id] ?? [];
      const normalizedPreferred = preferredModels.map((modelName) => normalizeModelKey(app.id, modelName));
      const tables = [...app.tables];
      tables.sort((a, b) => {
        const keyA = getNormalizedTableKey(app.id, a.id);
        const keyB = getNormalizedTableKey(app.id, b.id);
        const indexA = normalizedPreferred.indexOf(keyA);
        const indexB = normalizedPreferred.indexOf(keyB);
        if (indexA === -1 && indexB === -1) {
          return a.label.localeCompare(b.label);
        }
        if (indexA === -1) {
          return 1;
        }
        if (indexB === -1) {
          return -1;
        }
        return indexA - indexB;
      });
      return {
        ...app,
        tables,
      };
    })
    .filter((app) => app.tables.length > 0);

  return apps.sort((a, b) => {
    const indexA = PREFERRED_APP_ORDER.indexOf(a.id);
    const indexB = PREFERRED_APP_ORDER.indexOf(b.id);
    if (indexA === -1 && indexB === -1) {
      return a.label.localeCompare(b.label);
    }
    if (indexA === -1) {
      return 1;
    }
    if (indexB === -1) {
      return -1;
    }
    return indexA - indexB;
  });
};

export const DemoThreeColumnPage = () => {
  const [config, setConfig] = useState<AdminWorkspaceConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const workspaceConfig = useMemo(() => {
    if (config) {
      return config;
    }
    if (error) {
      return SAMPLE_WORKSPACE_CONFIG;
    }
    return null;
  }, [config, error]);

  useEffect(() => {
    let isActive = true;

    const loadWorkspace = async () => {
      try {
        setLoading(true);
        setError(null);

        const namesPayload = await getModelNames();
        const modelNames = Array.isArray(namesPayload?.model_names) ? namesPayload.model_names : [];

        if (!modelNames.length) {
          throw new Error("No WCAPI models available");
        }

        const normalizedAvailableModels = new Map<string, string>();
        modelNames.forEach((name) => {
          normalizedAvailableModels.set(normalizeFullModelName(name), name);
        });

        const prioritizedModelNames = PREFERRED_MODEL_SEQUENCE.map((canonicalName) => {
          const normalizedKey = normalizeFullModelName(canonicalName);
          return normalizedAvailableModels.get(normalizedKey) ?? null;
        }).filter((name): name is string => Boolean(name));

        const prioritizedSet = new Set(prioritizedModelNames);
        const fallbackModelNames = modelNames.filter((name) => !prioritizedSet.has(name));

        const orderedModelNames: string[] = [];
        const seenModelNames = new Set<string>();
        [...prioritizedModelNames, ...fallbackModelNames].forEach((name) => {
          if (!seenModelNames.has(name)) {
            seenModelNames.add(name);
            orderedModelNames.push(name);
          }
        });

        let targetModelNames = orderedModelNames.filter((name) => PREFERRED_MODEL_KEY_SET.has(normalizeFullModelName(name)));
        if (targetModelNames.length === 0) {
          targetModelNames = orderedModelNames;
        }

        const detailResults = await Promise.allSettled(
          targetModelNames.map(async (modelName) => ({
            name: modelName,
            data: await getModelDetail(modelName),
          }))
        );

        const models = detailResults
          .filter((result): result is PromiseFulfilledResult<{ name: string; data: ModelDetailPayload }> => result.status === "fulfilled")
          .map((result) => result.value.data.model)
          .filter((model): model is ModelDetailPayload["model"] => Boolean(model?.model_name));

        if (!models.length) {
          throw new Error("Failed to load WCAPI model definitions");
        }

        const apps = buildApps(models);

        if (!apps.length) {
          throw new Error("No WCAPI apps could be constructed");
        }

        if (!isActive) {
          return;
        }

        setConfig({
          apps,
          storageKey: "webclerk:wcapi:3column",
          defaultPageSize: 25,
          pageSizeOptions: [10, 25, 50, 100],
          initialAppId: apps[0]?.id,
          initialTableId: apps[0]?.tables[0]?.id,
        });
      } catch (err) {
        if (!isActive) {
          return;
        }
        const status = typeof (err as { response?: { status?: number } })?.response?.status === "number"
          ? (err as { response?: { status?: number } }).response?.status
          : undefined;
        const message = status === 401
          ? "Sign in to load WCAPI workspace data"
          : err instanceof Error
            ? err.message
            : "Failed to load WCAPI workspace";
        setError(message);
        setConfig(null);
      } finally {
        if (isActive) {
          setLoading(false);
        }
      }
    };

    void loadWorkspace();

    return () => {
      isActive = false;
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-200 p-6 dark:bg-slate-950">
      {loading && (
        <div className="mb-4 rounded border border-slate-300 bg-white p-3 text-sm text-slate-600 shadow-sm">
          Loading WCAPI workspace…
        </div>
      )}
      {error && (
        <div className="mb-4 rounded border border-amber-400 bg-amber-50 p-3 text-sm text-amber-800">
          {error}. Showing demo data instead.
        </div>
      )}
      {workspaceConfig ? (
        <AdminThreeColumn config={workspaceConfig} />
      ) : (
        <div className="rounded border border-slate-300 bg-white p-4 text-sm text-slate-600 shadow-sm">
          Preparing workspace…
        </div>
      )}
    </div>
  );
};
