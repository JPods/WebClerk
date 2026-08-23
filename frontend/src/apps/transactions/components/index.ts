/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Transaction Shared Components Index
 * Barrel export for all transaction detail components
 */

// Labels and Field Components
export { default as FieldLabel } from "./FieldLabel";

// Refs/Links Components
export { default as ContactLinksTable } from "./ContactLinksTable";
export type {
  ContactLinkDisplayRow,
  ContactColumnKey,
  ContactLinkColumnDef,
  ContactLinksTableProps,
} from "./ContactLinksTable";

// Comments and Actions

// Metadata and Admin
export { default as MetadataPanel } from "./MetadataPanel";

// Financials

// Flow and Lineage

// Base Detail Component
export { default as TransactionDetailBase } from "./TransactionDetailBase";
export type { TransactionTab } from "./TransactionDetailBase";

// Line Item Modals
export { default as LineDetailsModal } from "./LineDetailsModal";
export { default as SplitLineModal } from "./SplitLineModal";

// Activity and Audit
export { default as ActivityLogTab } from "./ActivityLogTab";

// Print Preview
export { default as PrintPreviewModal } from "./PrintPreviewModal";

// Payment Modals
export { default as AddPaymentModal } from "./AddPaymentModal";
export { default as ApplyPaymentModal } from "./ApplyPaymentModal";

// Item Search (shared across all transaction types)
export { default as TransactionItemSearch } from "./TransactionItemSearch";
export type { ItemSearchResult } from "./TransactionItemSearch";
export {
  resolveItemCode,
  resolveItemDescription,
  resolveItemKey,
  resolveUnitPrice,
  resolveUnitCost,
  resolveQtyOnHand,
} from "./TransactionItemSearch";

// Quick Add Recent Items
export { default as QuickAddRecent } from "./QuickAddRecent";

// Party Selector (Customer/Vendor/Manufacturer)
export {
  default as PartySelector,
  CustomerSelector,
  VendorSelector,
  ManufacturerSelector,
  TransactionPartySelector,
} from "./PartySelector";
export type {
  PartyType,
  SelectedParty,
  PartySelectorProps,
  CustomerSelectorProps,
  VendorSelectorProps,
  ManufacturerSelectorProps,
  TransactionPartyType,
  TransactionPartySelectorProps,
} from "./PartySelector";

// Transaction Task Modal
export { default as TransactionTaskModal } from "./TransactionTaskModal";
export type {
  TransactionTaskModalProps,
  TransactionTaskFormState,
  TaskKind,
  TaskPriority,
  TaskStatus,
  AssigneeInfo,
  ProjectOption,
  ContactOption,
} from "./TransactionTaskModal.types";
export {
  createDefaultTaskState,
  TASK_KIND_OPTIONS,
  PRIORITY_OPTIONS,
  STATUS_OPTIONS,
  PROGRESS_OPTIONS,
  DIFFICULTY_OPTIONS,
  PRIORITY_VALUES,
  VALUE_TO_PRIORITY,
  STATUS_CONFIG,
} from "./TransactionTaskModal.types";

// Transaction Tasks Hook
export { default as useTransactionTasks } from "./useTransactionTasks";

// Print Document Components
export * from "./print";
