/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Shared Panel Components - Barrel Export
 *
 * Reusable panels for displaying and editing common data structures
 * across all model detail pages.
 *
 * @see README.md for documentation
 */

// Types
export type {
  UserRole,
  EntityType,
  PanelPermissions,
  BasePanelProps,
  RefLink,
  EntityMetadata,
  EntityRefs,
  EntityPrefs,
  CommentMessage,
  CommentEntry,
  EntityComments,
  RawEntityComments,
  ActionEntry,
  ActionStatus,
  ActionPriority,
  ActionKind,
  QAEntry,
  DocumentEntry,
  FinancialSummary,
  PaymentEntry,
  EmailLink,
  PhoneLink,
  AddressLink,
  DomainLink,
} from "./types";

// Constants
export {
  ADMIN_ROLES,
  MANAGER_ROLES,
  USER_ROLES,
  ALL_ROLES,
  DEFAULT_PANEL_PERMISSIONS,
} from "./types";

// Hooks
export { usePermissions } from "./usePermissions";
export type {
  UsePermissionsOptions,
  UsePermissionsResult,
} from "./usePermissions";

// Utilities
export { getModelDetailPath, getModelWindowTitle } from "./getModelDetailPath";

// Panel Components - JSONB Field Editors (Admin)
export { default as CommentsPanel } from "./CommentsPanel";
export { default as MetadataPanel } from "./MetadataPanel";
export { default as RefsPanel } from "./RefsPanel";
export { default as PrefsPanel } from "./PrefsPanel";
export { default as RawDataPanel } from "./RawDataPanel";

// Panel Components - Entity Features
export { default as ActionsPanel } from "./ActionsPanel";
export { default as BasicInformationPanel } from "./BasicInformationPanel";
export { default as DocumentsPanel } from "./DocumentsPanel";
export { default as QAPanel } from "./QAPanel";
export { default as ContactPanel } from "./ContactPanel";
export { default as ContactLinksPanel } from "./ContactPanel";
export {
  normalizeRefsLinksContact,
} from "./ContactPanel";
export type { RefContact } from "./ContactPanel";

// ContactPanelx2 archived — replaced by CommPanel
export { default as FinancialsPanel } from "./FinancialsPanel";
export { default as ItemsPanel } from "./ItemsPanel";
export type { ItemsPanelProps, LineItemRecord } from "./ItemsPanel";
export { default as SerialPanel } from "./SerialPanel";
export type { SerialPanelProps, SerialRecord } from "./SerialPanel";
export { default as ShippingPanel } from "./ShippingPanel";
export { default as TransactionsPanel } from "./TransactionsPanel";
export type { TransactionsPanelProps, TransactionRecord } from "./TransactionsPanel";
export { default as TransactionPanel } from "./TransactionPanel";
export type { TransactionPanelProps, TransactionHeaderData } from "./TransactionPanel";
export { default as PaymentPanel } from "./PaymentPanel";
// Removed FinancialSummaryPanel and CustomerFinancialPanel (consolidated to FinancialsPanel)
// CommunicationsPanel and CommLinkPanel archived — replaced by CommPanel/CommCard
export { default as EmailGatePanel } from "./EmailGatePanel";
export type { EmailGateResult, EmailGatePanelProps } from "./EmailGatePanel";
export { default as OrgLinkPanel } from "./OrgLinkPanel";
export type { OrgField, OrgScalarField, OrgLinkPanelProps } from "./OrgLinkPanel";
export { default as LinkagesPanel } from "./LinkagesPanel";
export { default as CoreTabPanel } from "./CoreTabPanel";
export type { CoreTabPanelProps } from "./CoreTabPanel";

// Shared panel table component
export { PanelTable } from "./PanelTable";
export type { PanelColumnDef, PanelTableProps } from "./PanelTable";

// Q&A utilities and types
export {
  getQAQuestions,
  getQAAnswers,
  getAllQAQuestionGroups,
  getScopedQAQuestionGroups,
  getAppForModel,
  isAppName,
  APP_MODEL_REGISTRY,
  getQACounters,
  saveQAAnswer,
  deleteQAAnswer,
  getEffectiveOptions,
  uploadQAImage,
  applyQuestionGroup,
} from "./qaUtils";
export type {
  QAQuestionTemplate,
  QAAnswerChoice,
  QAQuestionDef,
  QAQuestionsData,
  QAQuestionsSetting,
  QACountersData,
  QAEffectiveOptions,
  QAAnswerRecord,
  ScopedQAGroups,
  ApplyQuestionGroupResponse,
} from "./qaUtils";

// Document upload utilities and types
export {
  uploadDocument,
  uploadDocuments,
  uploadDocumentWithLocation,
  deleteDocument,
  getDocumentUrl,
  formatFileSize,
  isAllowedFileType,
  validateFile,
  getBrowserGeolocation,
  useDocumentUpload,
} from "./documentUpload";
export type {
  DocumentRecord,
  DocumentMetadata,
  DocumentAddress,
  VirusScanResult,
  ExifData,
  GeoLocation,
  UploadDocumentOptions,
  UploadDocumentResult,
  UploadProgressCallback,
} from "./documentUpload";

// Linkages types (exported from component file)
export type {
  LinkageData,
  LinkedRecord,
  LinkagesPanelProps,
} from "./LinkagesPanel";

// BasicInformation types
export type { BasicInformationData } from "./BasicInformationPanel";
