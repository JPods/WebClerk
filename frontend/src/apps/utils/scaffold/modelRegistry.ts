/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { kebabCaseToTitle } from "./scaffoldUtils";

export type ModelRegistration = {
  app: string;
  model: string;
  label: string;
};

// Registry generated from folder structure. Customize labels as needed.
export const modelRegistry: ModelRegistration[] = [
  // accounts
  { app: "accounts", model: "audit", label: kebabCaseToTitle("audit") },
  { app: "accounts", model: "currency", label: kebabCaseToTitle("currency") },
  { app: "accounts", model: "exchange_rate", label: kebabCaseToTitle("exchange_rate") },
  { app: "accounts", model: "exchange_transaction", label: kebabCaseToTitle("exchange_transaction") },
  { app: "accounts", model: "gl_account", label: kebabCaseToTitle("gl_account") },
  { app: "accounts", model: "gl_journal", label: kebabCaseToTitle("gl_journal") },
  { app: "accounts", model: "ledger", label: kebabCaseToTitle("ledger") },
  { app: "accounts", model: "tax_jurisdiction", label: kebabCaseToTitle("tax_jurisdiction") },
  { app: "accounts", model: "term", label: kebabCaseToTitle("term") },

  // communications
  { app: "communications", model: "domain", label: kebabCaseToTitle("domain") },
  { app: "communications", model: "email", label: kebabCaseToTitle("email") },
  { app: "communications", model: "address", label: kebabCaseToTitle("address") },
  { app: "communications", model: "phone", label: kebabCaseToTitle("phone") },

  // core
  { app: "core", model: "action", label: kebabCaseToTitle("action") },
  { app: "core", model: "contact", label: kebabCaseToTitle("contact") },
  { app: "core", model: "notification", label: kebabCaseToTitle("notification") },
  { app: "core", model: "pending", label: kebabCaseToTitle("pending") },
  { app: "core", model: "report", label: kebabCaseToTitle("report") },
  { app: "core", model: "setting", label: kebabCaseToTitle("setting") },
  { app: "core", model: "soft_delete", label: kebabCaseToTitle("soft_delete") },
  { app: "core", model: "template", label: kebabCaseToTitle("template") },

  // orgs
  { app: "orgs", model: "base_org_model", label: kebabCaseToTitle("base_org_model") },
  { app: "orgs", model: "customer", label: kebabCaseToTitle("customer") },
  { app: "orgs", model: "employee", label: kebabCaseToTitle("employee") },
  { app: "orgs", model: "manufacturer", label: kebabCaseToTitle("manufacturer") },
  { app: "orgs", model: "organization", label: kebabCaseToTitle("organization") },
  { app: "orgs", model: "rep", label: kebabCaseToTitle("rep") },
  { app: "orgs", model: "vendor", label: kebabCaseToTitle("vendor") },

  // products
  { app: "products", model: "bill_of_material", label: kebabCaseToTitle("bill_of_material") },
  { app: "products", model: "catalog", label: kebabCaseToTitle("catalog") },
  { app: "products", model: "flow", label: kebabCaseToTitle("flow") },
  { app: "products", model: "item", label: kebabCaseToTitle("item") },
  { app: "products", model: "item_xref", label: kebabCaseToTitle("item_xref") },
  { app: "products", model: "matrics", label: kebabCaseToTitle("matrics") },
  { app: "products", model: "org_item", label: kebabCaseToTitle("org_item") },
  { app: "products", model: "serial", label: kebabCaseToTitle("serial") },
  { app: "products", model: "service", label: kebabCaseToTitle("service") },
  { app: "products", model: "specification", label: kebabCaseToTitle("specification") },
  { app: "products", model: "usage", label: kebabCaseToTitle("usage") },
  { app: "products", model: "variant", label: kebabCaseToTitle("variant") },
  { app: "products", model: "warehouse", label: kebabCaseToTitle("warehouse") },

  // support
  { app: "support", model: "campaign", label: kebabCaseToTitle("campaign") },
  { app: "support", model: "quality", label: kebabCaseToTitle("quality") },

  // transactions
  { app: "transactions", model: "base", label: kebabCaseToTitle("base") },
  { app: "transactions", model: "common", label: kebabCaseToTitle("common") },
  { app: "transactions", model: "invoice", label: kebabCaseToTitle("invoice") },
  { app: "transactions", model: "invoice_line", label: kebabCaseToTitle("invoice_line") },
  { app: "transactions", model: "linkage", label: kebabCaseToTitle("linkage") },
  { app: "transactions", model: "project", label: kebabCaseToTitle("project") },
  { app: "transactions", model: "proposal", label: kebabCaseToTitle("proposal") },
  { app: "transactions", model: "proposal_line", label: kebabCaseToTitle("proposal_line") },
  { app: "transactions", model: "purchase", label: kebabCaseToTitle("purchase") },
  { app: "transactions", model: "purchase_line", label: kebabCaseToTitle("purchase_line") },
  { app: "transactions", model: "receipt", label: kebabCaseToTitle("receipt") },
  { app: "transactions", model: "payment", label: kebabCaseToTitle("payment") },
  { app: "transactions", model: "requisition", label: kebabCaseToTitle("requisition") },
  { app: "transactions", model: "requisition_line", label: kebabCaseToTitle("requisition_line") },
  { app: "transactions", model: "order", label: kebabCaseToTitle("order") },
  { app: "transactions", model: "order_line", label: kebabCaseToTitle("order_line") },
  { app: "transactions", model: "workorder", label: kebabCaseToTitle("workorder") },
  { app: "transactions", model: "workorder_line", label: kebabCaseToTitle("workorder_line") },

  // sync
  { app: "sync", model: "bundle", label: kebabCaseToTitle("bundle") },
  { app: "sync", model: "connection", label: kebabCaseToTitle("connection") },
];

export const registryByModel = modelRegistry.reduce<Record<string, ModelRegistration>>(
  (acc, item) => {
    acc[item.model] = item;
    return acc;
  },
  {}
);
