/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React, { useState, useEffect, useCallback, useMemo, Suspense, lazy, ComponentType } from 'react';
import { FaCheck, FaRedo, FaDownload, FaEye, FaFilter, FaChevronDown, FaChevronRight, FaComment, FaTimes, FaCopy, FaExternalLinkAlt, FaSyncAlt } from 'react-icons/fa';

// ========================================
// Lazy-loaded Detail Components
// ========================================

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyDetailComponent = ComponentType<any>;

// Define lazy imports for Detail components
const DETAIL_COMPONENTS: Record<string, React.LazyExoticComponent<AnyDetailComponent>> = {
  // Communications
  address: lazy(() => import('../../apps/communications/models/address/pages/AddressDetail')),
  domain: lazy(() => import('../../apps/communications/models/domain/pages/DomainDetail')),
  email: lazy(() => import('../../apps/communications/models/email/pages/EmailDetail')),
  phone: lazy(() => import('../../apps/communications/models/phone/pages/PhoneDetail')),
  
  // Accounts
  audit: lazy(() => import('../../apps/accounts/models/audit/pages/AuditDetail')),
  currency: lazy(() => import('../../apps/accounts/models/currency/pages/CurrencyDetail')),
  exchange_rate: lazy(() => import('../../apps/accounts/models/exchange_rate/pages/ExchangeRateDetail')),
  exchange_transaction: lazy(() => import('../../apps/accounts/models/exchange_transaction/pages/ExchangeTransactionDetail')),
  gl_account: lazy(() => import('../../apps/accounts/models/gl_account/pages/GLAccountDetail')),
  gl_journal: lazy(() => import('../../apps/accounts/models/gl_journal/pages/GLJournalDetail')),
  
  // Core
  contact: lazy(() => import('../../apps/core/models/contact/pages/ContactDetail')),
  action: lazy(() => import('../../apps/core/models/action/pages/ActionDetail')),
  api_log: lazy(() => import('../../apps/core/models/api_log/pages/APILogDetail')),
  report: lazy(() => import('../../apps/core/models/report/pages/ReportDetail')),
  setting: lazy(() => import('../../apps/core/models/setting/pages/SettingDetail')),
  template: lazy(() => import('../../apps/core/models/template/pages/TemplateDetail')),
  
  // Docs
  document: lazy(() => import('../../apps/docs/models/document/pages/DocumentDetail')),
  
  // Products
  bill_of_material: lazy(() => import('../../apps/products/models/bill_of_material/pages/BillOfMaterialDetail')),
  catalog: lazy(() => import('../../apps/products/models/catalog/pages/CatalogDetail')),
  flow: lazy(() => import('../../apps/products/models/flow/pages/FlowDetail')),
  item: lazy(() => import('../../apps/products/models/item/pages/ItemDetail')),
  item_xref: lazy(() => import('../../apps/products/models/item_xref/pages/ItemXrefDetail')),
  matrics: lazy(() => import('../../apps/products/models/matrics/pages/MatricsDetail')),
  org_item: lazy(() => import('../../apps/products/models/org_item/pages/OrgItemDetail')),
  serial: lazy(() => import('../../apps/products/models/serial/pages/SerialDetail')),
  service: lazy(() => import('../../apps/products/models/service/pages/ServiceDetail')),
  specification: lazy(() => import('../../apps/products/models/specification/pages/SpecificationDetail')),
  usage: lazy(() => import('../../apps/products/models/usage/pages/UsageDetail')),
  variant: lazy(() => import('../../apps/products/models/variant/pages/VariantDetail')),
  warehouse: lazy(() => import('../../apps/products/models/warehouse/pages/WarehouseDetail')),
  
  // Transactions
  invoice: lazy(() => import('../../apps/transactions/models/invoice/pages/InvoiceDetail')),
  invoice_line: lazy(() => import('../../apps/transactions/models/invoice_line/pages/InvoiceLineDetail')),
  order: lazy(() => import('../../apps/transactions/models/order/pages/OrderDetail')),
  order_line: lazy(() => import('../../apps/transactions/models/order_line/pages/OrderLineDetail')),
  project: lazy(() => import('../../apps/transactions/models/project/pages/ProjectDetail')),
  proposal: lazy(() => import('../../apps/transactions/models/proposal/pages/ProposalDetail')),
  proposal_line: lazy(() => import('../../apps/transactions/models/proposal_line/pages/ProposalLineDetail')),
  purchase: lazy(() => import('../../apps/transactions/models/purchase/pages/PurchaseDetail')),
  purchase_line: lazy(() => import('../../apps/transactions/models/purchase_line/pages/PurchaseLineDetail')),
  receipt: lazy(() => import('../../apps/transactions/models/receipt/pages/ReceiptDetail')),
  requisition: lazy(() => import('../../apps/transactions/models/requisition/pages/RequisitionDetail')),
  workorder: lazy(() => import('../../apps/transactions/models/workorder/pages/WorkorderDetail')),
  workorder_line: lazy(() => import('../../apps/transactions/models/workorder_line/pages/WorkOrderLineDetail')),
  
  // Orgs
  customer: lazy(() => import('../../apps/orgs/models/customer/pages/CustomerDetail')),
  employee: lazy(() => import('../../apps/orgs/models/employee/pages/EmployeeDetail')),
  vendor: lazy(() => import('../../apps/orgs/models/vendor/pages/VendorDetail')),
  
  // Sync
  bundle: lazy(() => import('../../apps/sync/models/bundle/pages/BundleDetail')),
  connection: lazy(() => import('../../apps/sync/connection/pages/ConnectionDetail')),
  
  // Support
  campaign: lazy(() => import('../../apps/support/models/campaign/pages/CampaignDetail')),
};

// ========================================
// Detail File Inventory - All 52 Detail.tsx files
// ========================================

interface DetailFileInfo {
  category: string;
  model: string;
  fileName: string;
  path: string;
  pattern: 'TransactionDetailBase' | 'DetailTabs' | 'SimpleForm' | 'CustomLayout' | 'ReadOnly';
  route?: string;  // Route path for iframe preview
  sampleId?: number;  // Sample record ID for preview
  notes?: string;
}

const DETAIL_FILES: DetailFileInfo[] = [
  // Communications (4)
  { category: 'communications', model: 'address', fileName: 'AddressDetail.tsx', path: 'src/apps/communications/models/address/pages/AddressDetail.tsx', pattern: 'SimpleForm', route: '/communications/address/detail' },
  { category: 'communications', model: 'domain', fileName: 'DomainDetail.tsx', path: 'src/apps/communications/models/domain/pages/DomainDetail.tsx', pattern: 'SimpleForm', route: '/communications/domain/detail' },
  { category: 'communications', model: 'email', fileName: 'EmailDetail.tsx', path: 'src/apps/communications/models/email/pages/EmailDetail.tsx', pattern: 'SimpleForm', route: '/communications/email/detail' },
  { category: 'communications', model: 'phone', fileName: 'PhoneDetail.tsx', path: 'src/apps/communications/models/phone/pages/PhoneDetail.tsx', pattern: 'SimpleForm', route: '/communications/phone/detail' },
  
  // Accounts (6)
  { category: 'accounts', model: 'audit', fileName: 'AuditDetail.tsx', path: 'src/apps/accounts/models/audit/pages/AuditDetail.tsx', pattern: 'ReadOnly', route: '/accounts/audit/detail', notes: 'System log view' },
  { category: 'accounts', model: 'currency', fileName: 'CurrencyDetail.tsx', path: 'src/apps/accounts/models/currency/pages/CurrencyDetail.tsx', pattern: 'SimpleForm', route: '/accounts/currency/detail' },
  { category: 'accounts', model: 'exchange_rate', fileName: 'ExchangeRateDetail.tsx', path: 'src/apps/accounts/models/exchange_rate/pages/ExchangeRateDetail.tsx', pattern: 'SimpleForm', route: '/accounts/exchange-rate/detail' },
  { category: 'accounts', model: 'exchange_transaction', fileName: 'ExchangeTransactionDetail.tsx', path: 'src/apps/accounts/models/exchange_transaction/pages/ExchangeTransactionDetail.tsx', pattern: 'SimpleForm', route: '/accounts/exchange-transaction/detail' },
  { category: 'accounts', model: 'gl_account', fileName: 'GLAccountDetail.tsx', path: 'src/apps/accounts/models/gl_account/pages/GLAccountDetail.tsx', pattern: 'CustomLayout', route: '/accounts/gl-account/detail', notes: 'Enterprise form' },
  { category: 'accounts', model: 'gl_journal', fileName: 'GLJournalDetail.tsx', path: 'src/apps/accounts/models/gl_journal/pages/GLJournalDetail.tsx', pattern: 'SimpleForm', route: '/accounts/gl-journal/detail' },
  
  // Transactions (14)
  { category: 'transactions', model: 'invoice', fileName: 'InvoiceDetail.tsx', path: 'src/apps/transactions/models/invoice/pages/InvoiceDetail.tsx', pattern: 'TransactionDetailBase', route: '/transactions/invoice/detail' },
  { category: 'transactions', model: 'invoice_line', fileName: 'InvoiceLineDetail.tsx', path: 'src/apps/transactions/models/invoice_line/pages/InvoiceLineDetail.tsx', pattern: 'SimpleForm', notes: 'Inline line editor' },
  { category: 'transactions', model: 'order', fileName: 'OrderDetail.tsx', path: 'src/apps/transactions/models/order/pages/OrderDetail.tsx', pattern: 'TransactionDetailBase', route: '/transactions/order/detail' },
  { category: 'transactions', model: 'order_line', fileName: 'OrderLineDetail.tsx', path: 'src/apps/transactions/models/order_line/pages/OrderLineDetail.tsx', pattern: 'SimpleForm', notes: 'Inline line editor' },
  { category: 'transactions', model: 'project', fileName: 'ProjectDetail.tsx', path: 'src/apps/transactions/models/project/pages/ProjectDetail.tsx', pattern: 'DetailTabs', notes: 'Rewritten with DetailTabs' },
  { category: 'transactions', model: 'proposal', fileName: 'ProposalDetail.tsx', path: 'src/apps/transactions/models/proposal/pages/ProposalDetail.tsx', pattern: 'TransactionDetailBase', route: '/transactions/proposal/detail' },
  { category: 'transactions', model: 'proposal_line', fileName: 'ProposalLineDetail.tsx', path: 'src/apps/transactions/models/proposal_line/pages/ProposalLineDetail.tsx', pattern: 'SimpleForm', notes: 'Inline line editor' },
  { category: 'transactions', model: 'purchase', fileName: 'PurchaseDetail.tsx', path: 'src/apps/transactions/models/purchase/pages/PurchaseDetail.tsx', pattern: 'TransactionDetailBase', route: '/transactions/purchase-order/detail' },
  { category: 'transactions', model: 'purchase_line', fileName: 'PurchaseLineDetail.tsx', path: 'src/apps/transactions/models/purchase_line/pages/PurchaseLineDetail.tsx', pattern: 'SimpleForm', notes: 'Inline line editor' },
  { category: 'transactions', model: 'receipt', fileName: 'ReceiptDetail.tsx', path: 'src/apps/transactions/models/receipt/pages/ReceiptDetail.tsx', pattern: 'TransactionDetailBase', route: '/transactions/receipt/detail' },
  { category: 'transactions', model: 'requisition', fileName: 'RequisitionDetail.tsx', path: 'src/apps/transactions/models/requisition/pages/RequisitionDetail.tsx', pattern: 'DetailTabs', notes: 'Rewritten with DetailTabs' },
  { category: 'transactions', model: 'workorder', fileName: 'WorkorderDetail.tsx', path: 'src/apps/transactions/models/workorder/pages/WorkorderDetail.tsx', pattern: 'TransactionDetailBase', route: '/transactions/work-order/detail' },
  { category: 'transactions', model: 'workorder_line', fileName: 'WorkOrderLineDetail.tsx', path: 'src/apps/transactions/models/workorder_line/pages/WorkOrderLineDetail.tsx', pattern: 'SimpleForm', notes: 'Inline line editor' },
  
  // Orgs (4)
  { category: 'orgs', model: 'contact', fileName: 'ContactDetail.tsx', path: 'src/apps/core/models/contact/pages/ContactDetail.tsx', pattern: 'CustomLayout', route: '/core/contact/detail', notes: 'Section layout with panels' },
  { category: 'orgs', model: 'customer', fileName: 'CustomerDetail.tsx', path: 'src/apps/orgs/models/customer/pages/CustomerDetail.tsx', pattern: 'DetailTabs', route: '/org/customer/detail' },
  { category: 'orgs', model: 'employee', fileName: 'EmployeeDetail.tsx', path: 'src/apps/orgs/models/employee/pages/EmployeeDetail.tsx', pattern: 'CustomLayout', notes: 'Uses OrgDetail base' },
  { category: 'orgs', model: 'vendor', fileName: 'VendorDetail.tsx', path: 'src/apps/orgs/models/vendor/pages/VendorDetail.tsx', pattern: 'DetailTabs' },
  
  // Products (13)
  { category: 'products', model: 'bill_of_material', fileName: 'BillOfMaterialDetail.tsx', path: 'src/apps/products/models/bill_of_material/pages/BillOfMaterialDetail.tsx', pattern: 'SimpleForm' },
  { category: 'products', model: 'catalog', fileName: 'CatalogDetail.tsx', path: 'src/apps/products/models/catalog/pages/CatalogDetail.tsx', pattern: 'SimpleForm' },
  { category: 'products', model: 'flow', fileName: 'FlowDetail.tsx', path: 'src/apps/products/models/flow/pages/FlowDetail.tsx', pattern: 'SimpleForm' },
  { category: 'products', model: 'item', fileName: 'ItemDetail.tsx', path: 'src/apps/products/models/item/pages/ItemDetail.tsx', pattern: 'CustomLayout', notes: 'Accordion+Panels (1411 lines)' },
  { category: 'products', model: 'item_xref', fileName: 'ItemXrefDetail.tsx', path: 'src/apps/products/models/item_xref/pages/ItemXrefDetail.tsx', pattern: 'SimpleForm' },
  { category: 'products', model: 'matrics', fileName: 'MatricsDetail.tsx', path: 'src/apps/products/models/matrics/pages/MatricsDetail.tsx', pattern: 'SimpleForm' },
  { category: 'products', model: 'org_item', fileName: 'OrgItemDetail.tsx', path: 'src/apps/products/models/org_item/pages/OrgItemDetail.tsx', pattern: 'SimpleForm' },
  { category: 'products', model: 'serial', fileName: 'SerialDetail.tsx', path: 'src/apps/products/models/serial/pages/SerialDetail.tsx', pattern: 'SimpleForm' },
  { category: 'products', model: 'service', fileName: 'ServiceDetail.tsx', path: 'src/apps/products/models/service/pages/ServiceDetail.tsx', pattern: 'SimpleForm' },
  { category: 'products', model: 'specification', fileName: 'SpecificationDetail.tsx', path: 'src/apps/products/models/specification/pages/SpecificationDetail.tsx', pattern: 'SimpleForm' },
  { category: 'products', model: 'usage', fileName: 'UsageDetail.tsx', path: 'src/apps/products/models/usage/pages/UsageDetail.tsx', pattern: 'SimpleForm' },
  { category: 'products', model: 'variant', fileName: 'VariantDetail.tsx', path: 'src/apps/products/models/variant/pages/VariantDetail.tsx', pattern: 'SimpleForm' },
  { category: 'products', model: 'warehouse', fileName: 'WarehouseDetail.tsx', path: 'src/apps/products/models/warehouse/pages/WarehouseDetail.tsx', pattern: 'SimpleForm' },
  
  // Core (6)
  { category: 'core', model: 'action', fileName: 'ActionDetail.tsx', path: 'src/apps/core/models/action/pages/ActionDetail.tsx', pattern: 'SimpleForm', route: '/core/actions/detail' },
  { category: 'core', model: 'api_log', fileName: 'APILogDetail.tsx', path: 'src/apps/core/models/api_log/pages/APILogDetail.tsx', pattern: 'ReadOnly', notes: 'System log view' },
  { category: 'core', model: 'report', fileName: 'ReportDetail.tsx', path: 'src/apps/core/models/report/pages/ReportDetail.tsx', pattern: 'SimpleForm', route: '/core/report/detail' },
  { category: 'core', model: 'setting', fileName: 'SettingDetail.tsx', path: 'src/apps/core/models/setting/pages/SettingDetail.tsx', pattern: 'SimpleForm', route: '/core/setting/detail' },
  { category: 'core', model: 'template', fileName: 'TemplateDetail.tsx', path: 'src/apps/core/models/template/pages/TemplateDetail.tsx', pattern: 'SimpleForm', route: '/core/template/detail' },
  
  // Sync (3)
  { category: 'sync', model: 'bundle', fileName: 'BundleDetail.tsx', path: 'src/apps/sync/models/bundle/pages/BundleDetail.tsx', pattern: 'SimpleForm' },
  { category: 'sync', model: 'connection', fileName: 'ConnectionDetail.tsx', path: 'src/apps/sync/connection/pages/ConnectionDetail.tsx', pattern: 'SimpleForm' },
  { category: 'sync', model: 'connection_alt', fileName: 'ConnectionDetail.tsx', path: 'src/apps/sync/models/bundle/pages/ConnectionDetail.tsx', pattern: 'SimpleForm' },
  
  // Docs (1)
  { category: 'docs', model: 'document', fileName: 'DocumentDetail.tsx', path: 'src/apps/docs/models/document/pages/DocumentDetail.tsx', pattern: 'SimpleForm', route: '/docs/document/detail' },
  
  // Support (1)
  { category: 'support', model: 'campaign', fileName: 'CampaignDetail.tsx', path: 'src/apps/support/models/campaign/pages/CampaignDetail.tsx', pattern: 'SimpleForm' },
];

// ========================================
// Review Status Types
// ========================================

type ReviewStatus = 'pending' | 'approved' | 'rework';

interface ReviewState {
  [filePath: string]: {
    status: ReviewStatus;
    notes?: string;
    reviewedAt?: string;
  };
}

interface GlobalComment {
  id: string;
  text: string;
  createdAt: string;
}

const STORAGE_KEY = 'detailReviewStatus';
const COMMENTS_STORAGE_KEY = 'detailReviewComments';

// ========================================
// Component
// ========================================

const DetailReview: React.FC = () => {
  const [reviewState, setReviewState] = useState<ReviewState>({});
  const [selectedFile, setSelectedFile] = useState<DetailFileInfo | null>(null);
  const [filterStatus, setFilterStatus] = useState<ReviewStatus | 'all'>('all');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [reviewNotes, setReviewNotes] = useState('');
  const [previewId, setPreviewId] = useState<string>('');
  
  // Record data state
  const [recordData, setRecordData] = useState<Record<string, unknown> | null>(null);
  const [recordLoading, setRecordLoading] = useState(false);
  const [recordError, setRecordError] = useState<string | null>(null);
  const [availableIds, setAvailableIds] = useState<number[]>([]);
  
  // Global comments state
  const [globalComments, setGlobalComments] = useState<GlobalComment[]>([]);
  const [showCommentDialog, setShowCommentDialog] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [exportContent, setExportContent] = useState('');

  // Fetch first available record when model changes
  const fetchFirstRecord = useCallback(async (modelName: string) => {
    setRecordLoading(true);
    setRecordError(null);
    setRecordData(null);
    setAvailableIds([]);
    
    try {
      // First, get page of records to find available IDs
      // API response is wrapped: { status, code, message, data: { results: [...] } }
      const listResponse = await fetch(`/wcapi/get/?model_name=${modelName}&page_size=10`);
      if (!listResponse.ok) throw new Error('Failed to fetch records list');
      const listJson = await listResponse.json();
      
      // Handle API envelope structure
      const listData = listJson.data || listJson;
      const results = listData.results || listData || [];
      
      if (Array.isArray(results) && results.length > 0) {
        const ids = results.map((r: { id: number }) => r.id).filter(Boolean);
        setAvailableIds(ids);
        
        // Use the first available ID
        const firstId = ids[0];
        setPreviewId(String(firstId));
        
        // Fetch the full record
        // API response for single record: { status, code, message, data: { record: {...} } }
        const recordResponse = await fetch(`/wcapi/get/?model_name=${modelName}&id=${firstId}`);
        if (!recordResponse.ok) throw new Error('Failed to fetch record');
        const recordJson = await recordResponse.json();
        const recordData = recordJson.data?.record || recordJson.data || recordJson;
        setRecordData(recordData);
      } else {
        setRecordError(`No records found for model "${modelName}"`);
      }
    } catch (err) {
      setRecordError(err instanceof Error ? err.message : 'Failed to fetch record');
    } finally {
      setRecordLoading(false);
    }
  }, []);

  // Fetch specific record by ID
  const fetchRecordById = useCallback(async (modelName: string, id: string) => {
    if (!id) return;
    setRecordLoading(true);
    setRecordError(null);
    
    try {
      const response = await fetch(`/wcapi/get/?model_name=${modelName}&id=${id}`);
      if (!response.ok) throw new Error(`Record not found (ID: ${id})`);
      const json = await response.json();
      // Handle API envelope: { status, code, message, data: { record: {...} } }
      const recordData = json.data?.record || json.data || json;
      setRecordData(recordData);
    } catch (err) {
      setRecordError(err instanceof Error ? err.message : 'Failed to fetch record');
      setRecordData(null);
    } finally {
      setRecordLoading(false);
    }
  }, []);

  // Auto-fetch when selected file changes
  useEffect(() => {
    if (selectedFile) {
      fetchFirstRecord(selectedFile.model);
    } else {
      setRecordData(null);
      setAvailableIds([]);
      setPreviewId('');
    }
  }, [selectedFile, fetchFirstRecord]);

  // Refresh handler
  const refreshRecord = useCallback(() => {
    if (selectedFile && previewId) {
      fetchRecordById(selectedFile.model, previewId);
    }
  }, [selectedFile, previewId, fetchRecordById]);

  // Load from localStorage
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      setReviewState(JSON.parse(saved));
    }
    const savedComments = localStorage.getItem(COMMENTS_STORAGE_KEY);
    if (savedComments) {
      setGlobalComments(JSON.parse(savedComments));
    }
  }, []);

  // Save to localStorage
  const saveReviewState = useCallback((newState: ReviewState) => {
    setReviewState(newState);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newState));
  }, []);

  // Save comments to localStorage
  const saveComments = useCallback((comments: GlobalComment[]) => {
    setGlobalComments(comments);
    localStorage.setItem(COMMENTS_STORAGE_KEY, JSON.stringify(comments));
  }, []);

  // Add a new comment
  const addComment = useCallback(() => {
    if (!newComment.trim()) return;
    const comment: GlobalComment = {
      id: Date.now().toString(),
      text: newComment.trim(),
      createdAt: new Date().toISOString(),
    };
    saveComments([...globalComments, comment]);
    setNewComment('');
  }, [newComment, globalComments, saveComments]);

  // Delete a comment
  const deleteComment = useCallback((id: string) => {
    saveComments(globalComments.filter(c => c.id !== id));
  }, [globalComments, saveComments]);

  // Update file status
  const updateFileStatus = useCallback((filePath: string, status: ReviewStatus, notes?: string) => {
    const newState = {
      ...reviewState,
      [filePath]: {
        status,
        notes: notes || reviewState[filePath]?.notes,
        reviewedAt: new Date().toISOString(),
      },
    };
    saveReviewState(newState);
  }, [reviewState, saveReviewState]);

  // Get file status
  const getFileStatus = useCallback((filePath: string): ReviewStatus => {
    return reviewState[filePath]?.status || 'pending';
  }, [reviewState]);

  // Categories
  const categories = useMemo(() => {
    return [...new Set(DETAIL_FILES.map(f => f.category))];
  }, []);

  // Filtered files
  const filteredFiles = useMemo(() => {
    return DETAIL_FILES.filter(file => {
      if (filterCategory !== 'all' && file.category !== filterCategory) return false;
      if (filterStatus !== 'all' && getFileStatus(file.path) !== filterStatus) return false;
      return true;
    });
  }, [filterCategory, filterStatus, getFileStatus]);

  // Grouped by category
  const groupedFiles = useMemo(() => {
    const groups: Record<string, DetailFileInfo[]> = {};
    filteredFiles.forEach(file => {
      if (!groups[file.category]) groups[file.category] = [];
      groups[file.category].push(file);
    });
    return groups;
  }, [filteredFiles]);

  // Stats
  const stats = useMemo(() => {
    const total = DETAIL_FILES.length;
    const approved = DETAIL_FILES.filter(f => getFileStatus(f.path) === 'approved').length;
    const rework = DETAIL_FILES.filter(f => getFileStatus(f.path) === 'rework').length;
    const pending = total - approved - rework;
    return { total, approved, rework, pending };
  }, [getFileStatus]);

  // Toggle category expansion
  const toggleCategory = useCallback((category: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  }, []);

  // Export to Markdown
  const exportToMarkdown = useCallback(() => {
    const lines: string[] = [
      '## Review Status by File',
      '',
      '| Category | Model | File | Pattern | Status | Notes |',
      '|----------|-------|------|---------|--------|-------|',
    ];

    DETAIL_FILES.forEach(file => {
      const status = getFileStatus(file.path);
      const review = reviewState[file.path];
      const statusEmoji = status === 'approved' ? '✅' : status === 'rework' ? '🔧' : '⏳';
      lines.push(
        `| ${file.category} | ${file.model} | ${file.fileName} | ${file.pattern} | ${statusEmoji} ${status} | ${review?.notes || file.notes || ''} |`
      );
    });

    lines.push('');
    lines.push(`**Summary:** ${stats.approved}/${stats.total} approved, ${stats.rework} need rework, ${stats.pending} pending`);
    lines.push('');
    
    // Add global comments section
    if (globalComments.length > 0) {
      lines.push('---');
      lines.push('');
      lines.push('## Review Comments');
      lines.push('');
      globalComments.forEach(comment => {
        const date = new Date(comment.createdAt).toLocaleDateString();
        lines.push(`- **${date}**: ${comment.text}`);
      });
      lines.push('');
    }
    
    lines.push(`*Generated: ${new Date().toISOString()}*`);

    const content = lines.join('\n');
    setExportContent(content);
    setShowExportDialog(true);
  }, [getFileStatus, reviewState, stats, globalComments]);

  // Download markdown file
  const downloadMarkdown = useCallback(() => {
    const blob = new Blob([exportContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'detail-review-status.md';
    a.click();
    URL.revokeObjectURL(url);
  }, [exportContent]);

  // Copy to clipboard
  const copyToClipboard = useCallback(() => {
    navigator.clipboard.writeText(exportContent);
  }, [exportContent]);

  // Handle approve/rework with navigation to next pending
  const handleApprove = useCallback(() => {
    if (!selectedFile) return;
    updateFileStatus(selectedFile.path, 'approved', reviewNotes);
    setReviewNotes('');
    // Find next pending file
    const currentIndex = filteredFiles.findIndex(f => f.path === selectedFile.path);
    const nextPending = filteredFiles.slice(currentIndex + 1).find(f => getFileStatus(f.path) === 'pending');
    if (nextPending) {
      setSelectedFile(nextPending);
    }
  }, [selectedFile, updateFileStatus, reviewNotes, filteredFiles, getFileStatus]);

  const handleRework = useCallback(() => {
    if (!selectedFile) return;
    updateFileStatus(selectedFile.path, 'rework', reviewNotes);
    setReviewNotes('');
    // Find next pending file
    const currentIndex = filteredFiles.findIndex(f => f.path === selectedFile.path);
    const nextPending = filteredFiles.slice(currentIndex + 1).find(f => getFileStatus(f.path) === 'pending');
    if (nextPending) {
      setSelectedFile(nextPending);
    }
  }, [selectedFile, updateFileStatus, reviewNotes, filteredFiles, getFileStatus]);

  // Status badge component
  const StatusBadge: React.FC<{ status: ReviewStatus }> = ({ status }) => {
    const colors = {
      pending: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
      approved: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
      rework: 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400',
    };
    return (
      <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[status]}`}>
        {status}
      </span>
    );
  };

  // Pattern badge component
  const PatternBadge: React.FC<{ pattern: string }> = ({ pattern }) => {
    const colors: Record<string, string> = {
      TransactionDetailBase: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
      DetailTabs: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      SimpleForm: 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300',
      CustomLayout: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400',
      ReadOnly: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
    };
    return (
      <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[pattern] || colors.SimpleForm}`}>
        {pattern}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Detail Page Review</h1>
        <p className="text-slate-600 dark:text-slate-400">Review and approve Detail.tsx standardization</p>
      </div>

      {/* Stats Bar */}
      <div className="mb-6 grid grid-cols-4 gap-4">
        <div className="rounded-lg bg-white dark:bg-slate-800 p-4 shadow-sm">
          <div className="text-2xl font-bold text-slate-900 dark:text-white">{stats.total}</div>
          <div className="text-sm text-slate-500 dark:text-slate-400">Total Files</div>
        </div>
        <div className="rounded-lg bg-white dark:bg-slate-800 p-4 shadow-sm border-l-4 border-emerald-500">
          <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{stats.approved}</div>
          <div className="text-sm text-slate-500 dark:text-slate-400">Approved</div>
        </div>
        <div className="rounded-lg bg-white dark:bg-slate-800 p-4 shadow-sm border-l-4 border-rose-500">
          <div className="text-2xl font-bold text-rose-600 dark:text-rose-400">{stats.rework}</div>
          <div className="text-sm text-slate-500 dark:text-slate-400">Rework</div>
        </div>
        <div className="rounded-lg bg-white dark:bg-slate-800 p-4 shadow-sm border-l-4 border-amber-500">
          <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">{stats.pending}</div>
          <div className="text-sm text-slate-500 dark:text-slate-400">Pending</div>
        </div>
      </div>

      {/* Filters & Actions */}
      <div className="mb-6 flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <FaFilter className="text-slate-400" />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as ReviewStatus | 'all')}
            className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rework">Rework</option>
          </select>
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
          >
            <option value="all">All Categories</option>
            {categories.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>
        <div className="ml-auto flex gap-2">
          <button
            onClick={() => setShowCommentDialog(true)}
            className="flex items-center gap-2 rounded bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700"
          >
            <FaComment />
            Comments ({globalComments.length})
          </button>
          <button
            onClick={exportToMarkdown}
            className="flex items-center gap-2 rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <FaDownload />
            Export Markdown
          </button>
        </div>
      </div>

      {/* Main Content - Review Panel Left, Preview Right */}
      <div className="grid grid-cols-[380px_1fr] gap-6" style={{ height: 'calc(100vh - 280px)' }}>
        {/* Left: Review Panel */}
        <div className="flex flex-col gap-4 overflow-hidden">
          {/* File List */}
          <div className="rounded-lg bg-white dark:bg-slate-800 shadow-sm overflow-hidden flex-1">
            <div className="border-b border-slate-200 dark:border-slate-700 px-4 py-3">
              <h2 className="font-semibold text-slate-900 dark:text-white">Files ({filteredFiles.length})</h2>
            </div>
            <div className="overflow-y-auto" style={{ maxHeight: 'calc(100vh - 520px)' }}>
              {Object.entries(groupedFiles).map(([category, files]) => (
                <div key={category}>
                  <button
                    onClick={() => toggleCategory(category)}
                    className="w-full flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-700/50 text-left text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                  >
                    {expandedCategories.has(category) ? <FaChevronDown size={12} /> : <FaChevronRight size={12} />}
                    {category} ({files.length})
                  </button>
                  {expandedCategories.has(category) && (
                    <div className="divide-y divide-slate-100 dark:divide-slate-700">
                      {files.map(file => {
                        const status = getFileStatus(file.path);
                        const isSelected = selectedFile?.path === file.path;
                        const hasRoute = !!file.route;
                        return (
                          <button
                            key={file.path}
                            onClick={() => setSelectedFile(file)}
                            className={`w-full px-4 py-2 text-left hover:bg-slate-50 dark:hover:bg-slate-700/50 ${
                              isSelected ? 'bg-blue-50 dark:bg-blue-900/20 border-l-2 border-blue-500' : ''
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <span className={`text-sm font-medium ${hasRoute ? 'text-slate-900 dark:text-white' : 'text-slate-400 dark:text-slate-500'}`}>
                                {file.fileName}
                              </span>
                              <StatusBadge status={status} />
                            </div>
                            <div className="mt-1 flex items-center gap-2">
                              <PatternBadge pattern={file.pattern} />
                              {!hasRoute && <span className="text-xs text-orange-500">No route</span>}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Review Controls */}
          {selectedFile && (
            <div className="rounded-lg bg-white dark:bg-slate-800 shadow-sm p-4">
              <div className="mb-3">
                <h3 className="font-semibold text-slate-900 dark:text-white truncate">{selectedFile.fileName}</h3>
                <div className="flex items-center gap-2 mt-1">
                  <PatternBadge pattern={selectedFile.pattern} />
                  <StatusBadge status={getFileStatus(selectedFile.path)} />
                </div>
                <code className="mt-2 block text-xs text-slate-500 dark:text-slate-400 truncate">{selectedFile.path}</code>
              </div>
              
              {/* Review Notes */}
              <textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Review notes..."
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white mb-3"
                rows={2}
              />

              {/* Action Buttons */}
              <div className="flex gap-2">
                <button
                  onClick={handleApprove}
                  className="flex-1 flex items-center justify-center gap-2 rounded bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700"
                >
                  <FaCheck size={12} />
                  Approve
                </button>
                <button
                  onClick={handleRework}
                  className="flex-1 flex items-center justify-center gap-2 rounded bg-rose-600 px-3 py-2 text-sm font-medium text-white hover:bg-rose-700"
                >
                  <FaRedo size={12} />
                  Rework
                </button>
              </div>

              {/* VS Code & Open in Tab */}
              <div className="mt-3 flex gap-2 text-xs">
                <button
                  onClick={() => navigator.clipboard.writeText(`code -g "${selectedFile.path}"`)}
                  className="flex items-center gap-1 text-blue-600 hover:text-blue-800 dark:text-blue-400"
                >
                  <FaEye size={10} />
                  Copy VS Code cmd
                </button>
                {selectedFile.route && previewId && (
                  <a
                    href={`${selectedFile.route}/${previewId}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-blue-600 hover:text-blue-800 dark:text-blue-400"
                  >
                    <FaExternalLinkAlt size={10} />
                    Open in tab
                  </a>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right: Preview Panel - Record Data */}
        <div className="rounded-lg bg-white dark:bg-slate-800 shadow-sm overflow-hidden flex flex-col">
          <div className="border-b border-slate-200 dark:border-slate-700 px-4 py-3 flex items-center justify-between">
            <h2 className="font-semibold text-slate-900 dark:text-white">
              Record Data {selectedFile ? `- ${selectedFile.model}` : ''}
            </h2>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <label className="text-sm text-slate-500 dark:text-slate-400">ID:</label>
                {availableIds.length > 0 ? (
                  <select
                    value={previewId}
                    onChange={(e) => {
                      setPreviewId(e.target.value);
                      if (selectedFile) fetchRecordById(selectedFile.model, e.target.value);
                    }}
                    className="w-24 rounded border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  >
                    {availableIds.map(id => (
                      <option key={id} value={id}>{id}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    value={previewId}
                    onChange={(e) => setPreviewId(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && selectedFile) {
                        fetchRecordById(selectedFile.model, previewId);
                      }
                    }}
                    className="w-20 rounded border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                    placeholder="ID"
                  />
                )}
              </div>
              <button
                onClick={refreshRecord}
                disabled={recordLoading}
                className="p-1.5 rounded text-slate-500 hover:text-slate-700 hover:bg-slate-100 dark:hover:text-slate-300 dark:hover:bg-slate-700 disabled:opacity-50"
                title="Refresh record"
              >
                <FaSyncAlt size={14} className={recordLoading ? 'animate-spin' : ''} />
              </button>
              {selectedFile?.route && (
                <a
                  href={`${selectedFile.route}/${previewId}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1.5 rounded text-slate-500 hover:text-slate-700 hover:bg-slate-100 dark:hover:text-slate-300 dark:hover:bg-slate-700"
                  title="Open Detail page in new tab"
                >
                  <FaExternalLinkAlt size={14} />
                </a>
              )}
            </div>
          </div>
          <div className="flex-1 bg-slate-50 dark:bg-slate-900 overflow-auto p-4">
            {recordLoading ? (
              <div className="h-full flex items-center justify-center text-slate-500 dark:text-slate-400">
                <p>Loading record...</p>
              </div>
            ) : recordError ? (
              <div className="h-full flex items-center justify-center text-rose-500">
                <p>{recordError}</p>
              </div>
            ) : recordData && selectedFile ? (
              <Suspense fallback={<div className="h-full flex items-center justify-center text-slate-500">Loading component...</div>}>
                {(() => {
                  const DetailComponent = DETAIL_COMPONENTS[selectedFile.model];
                  if (!DetailComponent) {
                    return (
                      <div className="p-4 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-300">
                        <p className="font-medium">No component mapped for: {selectedFile.model}</p>
                        <pre className="mt-2 text-xs font-mono whitespace-pre-wrap">{JSON.stringify(recordData, null, 2)}</pre>
                      </div>
                    );
                  }
                  return (
                    <div className="bg-white dark:bg-slate-800 rounded-lg shadow-sm overflow-hidden">
                      <DetailComponent
                        modeProp="view"
                        dataProp={recordData}
                        hideBreadcrumb={true}
                        inline={true}
                      />
                    </div>
                  );
                })()}
              </Suspense>
            ) : selectedFile ? (
              <div className="h-full flex items-center justify-center text-slate-500 dark:text-slate-400">
                <p>Fetching first record for {selectedFile.model}...</p>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500 dark:text-slate-400">
                <p>Select a file from the list to preview record data</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mt-6 flex gap-3">
        <button
          onClick={() => {
            // Expand all categories
            setExpandedCategories(new Set(categories));
          }}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
        >
          Expand All
        </button>
        <button
          onClick={() => setExpandedCategories(new Set())}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
        >
          Collapse All
        </button>
        <button
          onClick={() => {
            // Select first pending file
            const firstPending = DETAIL_FILES.find(f => getFileStatus(f.path) === 'pending');
            if (firstPending) {
              setSelectedFile(firstPending);
              setExpandedCategories(prev => new Set([...prev, firstPending.category]));
            }
          }}
          className="rounded border border-amber-500 px-3 py-1.5 text-sm text-amber-700 hover:bg-amber-50 dark:text-amber-400 dark:hover:bg-amber-900/20"
        >
          Start Reviewing Pending
        </button>
      </div>

      {/* Comment Dialog */}
      {showCommentDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-lg rounded-lg bg-white dark:bg-slate-800 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-700 px-6 py-4">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Review Comments</h3>
              <button
                onClick={() => setShowCommentDialog(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              >
                <FaTimes size={20} />
              </button>
            </div>
            <div className="p-6">
              {/* Add new comment */}
              <div className="mb-4">
                <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Add Comment
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && addComment()}
                    placeholder="Enter a review comment..."
                    className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  />
                  <button
                    onClick={addComment}
                    disabled={!newComment.trim()}
                    className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                  >
                    Add
                  </button>
                </div>
              </div>

              {/* Comments list */}
              <div className="max-h-64 overflow-y-auto">
                {globalComments.length === 0 ? (
                  <p className="text-sm text-slate-500 dark:text-slate-400">No comments yet</p>
                ) : (
                  <div className="space-y-2">
                    {globalComments.map(comment => (
                      <div
                        key={comment.id}
                        className="flex items-start gap-3 rounded bg-slate-100 dark:bg-slate-700 p-3"
                      >
                        <div className="flex-1">
                          <p className="text-sm text-slate-800 dark:text-slate-200">{comment.text}</p>
                          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                            {new Date(comment.createdAt).toLocaleString()}
                          </p>
                        </div>
                        <button
                          onClick={() => deleteComment(comment.id)}
                          className="text-rose-500 hover:text-rose-600"
                        >
                          <FaTimes size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="flex justify-end border-t border-slate-200 dark:border-slate-700 px-6 py-4">
              <button
                onClick={() => setShowCommentDialog(false)}
                className="rounded bg-slate-600 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Export Dialog */}
      {showExportDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-2xl rounded-lg bg-white dark:bg-slate-800 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-700 px-6 py-4">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Export Review Status</h3>
              <button
                onClick={() => setShowExportDialog(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              >
                <FaTimes size={20} />
              </button>
            </div>
            <div className="p-6">
              <p className="mb-3 text-sm text-slate-600 dark:text-slate-400">
                Copy this content to update <code className="rounded bg-slate-100 dark:bg-slate-700 px-1">readmes/detail-page-standardization-plan.md</code>
              </p>
              <textarea
                readOnly
                value={exportContent}
                className="h-64 w-full rounded border border-slate-300 p-3 font-mono text-xs dark:border-slate-600 dark:bg-slate-700 dark:text-white"
              />
            </div>
            <div className="flex justify-end gap-3 border-t border-slate-200 dark:border-slate-700 px-6 py-4">
              <button
                onClick={copyToClipboard}
                className="flex items-center gap-2 rounded bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700"
              >
                <FaCopy />
                Copy to Clipboard
              </button>
              <button
                onClick={downloadMarkdown}
                className="flex items-center gap-2 rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                <FaDownload />
                Download File
              </button>
              <button
                onClick={() => setShowExportDialog(false)}
                className="rounded bg-slate-600 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DetailReview;
