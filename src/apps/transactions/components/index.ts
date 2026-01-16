/**
 * Transaction Shared Components Index
 * Barrel export for all transaction detail components
 */

// Labels and Field Components
export { default as FieldLabel } from './FieldLabel';

// Refs/Links Components
export { default as RefsLinksContactPanel } from './RefsLinksContactPanel';
export { default as RefsLinksTable } from './RefsLinksTable';
export { default as ContactLinksTable } from './ContactLinksTable';
export type { 
  ContactLinkDisplayRow, 
  ContactColumnKey, 
  ContactLinkColumnDef, 
  ContactLinksTableProps 
} from './ContactLinksTable';

// Comments and Actions
export { default as CommentsPanel } from './CommentsPanel';
export { default as ActionsCard } from './ActionsCard';

// Metadata and Admin
export { default as MetadataPanel } from './MetadataPanel';
export { default as JsonFieldEditor } from './JsonFieldEditor';

// Financials
export { default as FinancialsCard } from './FinancialsCard';

// Flow and Lineage
export { default as FlowDiagram } from './FlowDiagram';

// Base Detail Component
export { default as TransactionDetailBase } from './TransactionDetailBase';
export type { TransactionTab } from './TransactionDetailBase';

// Line Item Modals
export { default as LineDetailsModal } from './LineDetailsModal';
export { default as SplitLineModal } from './SplitLineModal';

// Activity and Audit
export { default as ActivityLogTab } from './ActivityLogTab';

// Print Preview
export { default as PrintPreviewModal } from './PrintPreviewModal';

// Attachments
export { default as AttachmentsTab } from './AttachmentsTab';

// Quick Add Recent Items
export { default as QuickAddRecent } from './QuickAddRecent';
