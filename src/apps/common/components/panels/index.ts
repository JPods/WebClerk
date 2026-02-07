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
  CommentEntry,
  EntityComments,
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
} from './types';

// Constants
export {
  ADMIN_ROLES,
  MANAGER_ROLES,
  USER_ROLES,
  ALL_ROLES,
  DEFAULT_PANEL_PERMISSIONS,
} from './types';

// Hooks
export { usePermissions } from './usePermissions';
export type { UsePermissionsOptions, UsePermissionsResult } from './usePermissions';

// Panel Components - JSONB Field Editors (Admin)
export { default as CommentsPanel } from './CommentsPanel';
export { default as MetadataPanel } from './MetadataPanel';
export { default as RefsPanel } from './RefsPanel';
export { default as PrefsPanel } from './PrefsPanel';
export { default as RawDataPanel } from './RawDataPanel';

// Panel Components - Entity Features
export { default as ActionsPanel } from './ActionsPanel';
export { default as DocumentsPanel } from './DocumentsPanel';
export { default as QAPanel } from './QAPanel';
export { default as ContactLinksPanel } from './ContactLinksPanel';
export { default as FinancialsPanel } from './FinancialsPanel';
export { default as CommunicationsPanel } from './CommunicationsPanel';
export { default as LinkagesPanel } from './LinkagesPanel';

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
} from './qaUtils';
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
} from './qaUtils';

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
} from './documentUpload';
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
} from './documentUpload';

// Linkages types (exported from component file)
export type { LinkageData, LinkedRecord, LinkagesPanelProps } from './LinkagesPanel';

