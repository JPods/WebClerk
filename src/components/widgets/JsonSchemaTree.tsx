/**
 * JsonSchemaTree — shows JSON envelope structure for a model with
 * click-to-copy dot-paths. Two modes:
 *   1. Inline popup (shift-click model name in DataBrowser)
 *   2. Printable reference (standalone or in Report)
 *
 * The schema data comes from the Python model defaults — this is the
 * canonical shape. If the Python changes, update ENVELOPE_SCHEMAS.
 */
import React, { useState, useCallback } from 'react';

// ═══════════════════════════════════════════════════════════════════════
// Canonical envelope schemas — mirror Python default_*() functions
// ═══════════════════════════════════════════════════════════════════════

type SchemaNode = {
  type: 'number' | 'string' | 'boolean' | 'object' | 'array' | 'null';
  description?: string;
  children?: Record<string, SchemaNode>;
  /** true = query index only, never read for display/computation */
  indexOnly?: boolean;
};

type ModelSchema = {
  label: string;
  envelopes: Record<string, SchemaNode>;
};

const NUM = (desc: string, indexOnly?: boolean): SchemaNode => ({ type: 'number', description: desc, indexOnly });
const STR = (desc: string): SchemaNode => ({ type: 'string', description: desc });
const BOOL = (desc: string): SchemaNode => ({ type: 'boolean', description: desc });
const ARR = (desc: string): SchemaNode => ({ type: 'array', description: desc });
const OBJ = (desc: string, children: Record<string, SchemaNode>): SchemaNode => ({ type: 'object', description: desc, children });

// ─── CoreModel fields (inherited by ALL models) ─────────────────────

const CORE_FIELDS: Record<string, SchemaNode> = {
  id:             NUM('Primary key (BigAutoField)'),
  uuid:           STR('Universal unique ID — immutable after creation'),
  ida:            STR('Soft ID from external system or auto-generated'),
  dt_created:     NUM('UTC epoch ms — when record was created'),
  dt_modified:    NUM('UTC epoch ms — when record was last modified'),
  version:        NUM('Optimistic concurrency version — increments on save'),
  is_active:      BOOL('Record is logically active'),
  security_level: NUM('Security level or classification'),
  dt_approved:    NUM('UTC epoch ms — when approved; 0 = not approved'),
  times_used:     NUM('Lifetime use count'),
  dt_last_used:   NUM('UTC epoch ms — last used; 0 = never'),
  purpose:        STR('Why this record exists: team_memory, template, etc.'),
};

const BASE_EXTRA_FIELDS: Record<string, SchemaNode> = {
  name:           STR('Display name'),
  display_name:   STR('Display name (legacy column)'),
  description:    STR('Description text'),
  health_rating:  NUM('Data health score 0-100'),
};

// ─── BaseModel envelopes (inherited by ALL models) ───────────────────

const METADATA_ENVELOPE: Record<string, SchemaNode> = {
  security:    STR('Security classification'),
  publish:     STR('Publish status'),
  priority:    STR('Priority level'),
  version:     STR('Record version'),
  explanation: STR('Explanation/notes'),
  access: OBJ('Access control', {
    view: ARR('Contact IDs with view access'),
    edit: ARR('Contact IDs with edit access'),
  }),
  resources: OBJ('Resource allocation', {
    required: OBJ('Required resources', {}),
    allocated: OBJ('Allocated resources', {}),
  }),
  flow:   OBJ('Workflow state', {}),
  source: OBJ('Source attribution', {}),
  history: OBJ('Timestamp history', {
    created:  OBJ('Creation', { dt: NUM('UTC epoch ms'), contact_id: NUM('Who') }),
    modified: OBJ('Last modified', { dt: NUM('UTC epoch ms'), contact_id: NUM('Who') }),
    accessed: OBJ('Last accessed', { dt: NUM('UTC epoch ms'), contact_id: NUM('Who') }),
    verified: OBJ('Last verified', { dt: NUM('UTC epoch ms'), contact_id: NUM('Who') }),
    synced:   OBJ('Last synced', { dt: NUM('UTC epoch ms'), contact_id: NUM('Who') }),
  }),
  health: OBJ('Data quality scores', {
    rating:       NUM('Overall rating 0-100'),
    completeness: NUM('Field completeness 0-100'),
    accuracy:     NUM('Data accuracy 0-100'),
    freshness:    NUM('Data freshness 0-100'),
    consistency:  NUM('Cross-field consistency 0-100'),
  }),
  flags: OBJ('System flags', {
    schema_rev:       NUM('Schema revision number'),
    keywords_pending: BOOL('Keywords need recomputation'),
  }),
  versioning: OBJ('Change tracking', {
    size_activity:  OBJ('Size/activity metrics', {}),
    changed_fields: ARR('Fields changed in last update'),
  }),
  small_stings:  ARR('Customer-assessed fines'),
  erosions:      ARR('Erosion entries'),
  temp:          ARR('Temporary data'),
  userdefined:   OBJ('User-defined metadata', {}),
  images: OBJ('Image status', {
    source:  STR('Image source path'),
    tn:      BOOL('Thumbnail exists'),
    display: BOOL('Display image exists'),
    hires:   BOOL('Hi-res image exists'),
  }),
  audit_trail: ARR('Audit trail entries'),
  import_data: OBJ('Original import data', {}),
};

const REFS_ENVELOPE: Record<string, SchemaNode> = {
  keywords:    ARR('Search keywords'),
  tags:        ARR('Tags'),
  links: OBJ('Related entity links', {
    contact: ARR('Linked contacts'),
    item:    ARR('Linked items'),
  }),
  parents:     ARR('Parent action IDs (Gantt dependencies)'),
  depends_on:  OBJ('Dependencies by model', {}),
  categories:  ARR('Category assignments'),
  related_ids: ARR('Related record IDs'),
  source:      OBJ('Source reference', {}),
};

const PREFS_ENVELOPE: Record<string, SchemaNode> = {
  userdefined: OBJ('User-defined preferences', {}),
  tags:        ARR('User tags'),
  pinned:      BOOL('Pinned in UI'),
  search:      ARR('Saved search terms'),
};

const COMMENTS_ENVELOPE: Record<string, SchemaNode> = {
  general: OBJ('General comments', {
    public:  ARR('Customer-visible comments'),
    process: ARR('Internal process notes'),
    foreign: ARR('External/imported comments'),
  }),
  records: OBJ('Per-record comments keyed by model/id', {}),
};

const ACTIONS_ENVELOPE: Record<string, SchemaNode> = {
  required: BOOL('Action required'),
  status:   STR('pending | done | blocked'),
  who:      NUM('Contact ID assigned'),
  when:     NUM('Due date (UTC epoch ms)'),
  what:     STR('Action description'),
  kind:     STR('followup | review | ship | approve'),
  extra:    OBJ('Domain-specific data', {}),
};

const BASE_ENVELOPES: Record<string, SchemaNode> = {
  metadata: OBJ('Record metadata — history, health, flags, images', METADATA_ENVELOPE),
  refs:     OBJ('References — links, tags, keywords, dependencies', REFS_ENVELOPE),
  prefs:    OBJ('User preferences', PREFS_ENVELOPE),
  comments: OBJ('Comments — public, process, foreign', COMMENTS_ENVELOPE),
  actions:  OBJ('Action tracking', ACTIONS_ENVELOPE),
  config:   OBJ('Model-specific configuration', {}),
};

// ─── Transaction-specific envelopes ──────────────────────────────────

const TOTALS_ENVELOPE: Record<string, SchemaNode> = {
  subtotal:  NUM('Sum of line extended sell before tax/ship/discount'),
  discount:  NUM('Header discount amount'),
  taxable:   NUM('Subtotal minus discount, subject to tax'),
  tax:       NUM('Sales tax amount'),
  shipping:  NUM('Shipping/handling charged to customer'),
  other:     NUM('Misc charges'),
  total:     NUM('Grand total customer-facing'),
  cost:      NUM('Total cost (for margin)'),
  margin:    NUM('Total minus cost'),
  margin_pc: NUM('Margin percentage'),
  received:  NUM('Payments received'),
  balance:   NUM('Total minus received'),
};

const SELL_ENVELOPE: Record<string, SchemaNode> = {
  line_sum_goods:    NUM('Sum of product line extended prices'),
  line_sum_tax:      NUM('Sum of tax lines'),
  line_sum_shipping: NUM('Sum of shipping lines'),
  line_sum_handling: NUM('Sum of handling lines'),
  handling:          NUM('Header handling charge'),
  freight:           NUM('Header freight charge'),
  tax_rate:          NUM('Applied tax rate'),
  tax:               NUM('Computed tax'),
  discount:          NUM('Discount amount'),
  total:             NUM('Sell-side total'),
};

const COST_ENVELOPE: Record<string, SchemaNode> = {
  line_sum_goods:    NUM('Sum of product line extended costs'),
  line_sum_tax:      NUM('Sum of cost-side tax lines'),
  line_sum_shipping: NUM('Sum of cost-side shipping'),
  line_sum_handling: NUM('Sum of cost-side handling'),
  handling:          NUM('Header cost handling'),
  freight:           NUM('Header cost freight'),
  tax_rate:          NUM('Cost-side tax rate'),
  tax:               NUM('Cost-side tax'),
  commissions:       NUM('Commission amount'),
  total:             NUM('Cost-side total'),
};

const FINANCE_ENVELOPE: Record<string, SchemaNode> = {
  sales_tax_id:   NUM('Tax jurisdiction ID'),
  sales_tax_name: STR('Tax jurisdiction name'),
  sales_tax_rate: NUM('Sales tax rate (decimal)'),
  sales_tax:      NUM('Computed sales tax'),
  cost_tax_id:    NUM('Cost tax jurisdiction ID'),
  cost_tax_name:  STR('Cost tax jurisdiction name'),
  cost_tax_rate:  NUM('Cost tax rate'),
  cost_tax:       NUM('Computed cost tax'),
  tax_subtotal:   NUM('Tax subtotal'),
  tax_pc:         NUM('Tax percentage'),
  collection_expense: NUM('Collection expense'),
  exchange_expense:   NUM('Exchange/currency expense'),
};

const LINE_PRICE_ENVELOPE: Record<string, SchemaNode> = {
  unit:            NUM('Unit sell price'),
  extended:        NUM('Qty × unit price'),
  discount_amount: NUM('Per-line discount amount'),
  discount_pc:     NUM('Discount percentage'),
  msrp:            NUM('Manufacturer suggested retail'),
  level:           STR('Price level applied'),
};

const LINE_COST_ENVELOPE: Record<string, SchemaNode> = {
  unit:     NUM('Unit cost'),
  extended: NUM('Qty × unit cost'),
  shipping: NUM('Per-line shipping cost'),
  handling: NUM('Per-line handling cost'),
  tax_code: STR('Tax code (EXEMPT, NONTAXABLE, or blank)'),
};

const LINE_QUANTITY_ENVELOPE: Record<string, SchemaNode> = {
  staged:    NUM('Quantity on document'),
  active:    NUM('Quantity active/shipped'),
  remaining: NUM('Quantity remaining'),
};

const SOURCE_ENVELOPE: Record<string, SchemaNode> = {
  campaign_id:      NUM('Campaign ID'),
  campaign_name:    STR('Campaign name'),
  catalog_id:       NUM('Catalog ID'),
  vendor_id:        NUM('Vendor ID'),
  manufacturer_id:  NUM('Manufacturer ID'),
};

const FLOW_ENVELOPE: Record<string, SchemaNode> = {
  source:   ARR('Source references [{type, id}]'),
  children: ARR('Child references [{type, id}]'),
};

// ─── Payment-specific ────────────────────────────────────────────────

const PAYMENT_FIELDS: Record<string, SchemaNode> = {
  amount:     NUM('Positive=received, negative=disbursed'),
  available:  NUM('Remaining to apply (starts = amount)'),
  tendered:   NUM('Amount physically tendered (cash)'),
  change:     NUM('Change returned (tendered - amount)'),
  fee_amount: NUM('Processing fee'),
  parent_id:  NUM('Origin transaction ID'),
  parent_model: STR('Origin model (invoice, order, etc.)'),
};

// ─── Document-specific ───────────────────────────────────────────────

const COPYRIGHT_ENVELOPE: Record<string, SchemaNode> = {
  level:  NUM('Copyright level'),
  path:   STR('Document path'),
  holder: STR('Copyright holder'),
  notes:  ARR('Copyright notes'),
};

// ─── Transaction-specific scalar fields ──────────────────────────────

const TXN_FIELDS: Record<string, SchemaNode> = {
  status:         STR('planned | released | in_progress | hold | complete | canceled'),
  priority:       STR('Priority level'),
  price_level:    STR('Price level (retail, wholesale, etc.)'),
  terms:          STR('Payment terms'),
  ship_via:       STR('Carrier/shipping method'),
  is_commission:  BOOL('Commission-based order from manufacturer'),
  customer_id:    NUM('FK → OrgBase'),
  manufacturer_id: NUM('FK → OrgBase'),
  vendor_id:      NUM('FK → OrgBase'),
  contact_id:     NUM('FK → Contact'),
  parent_id:      NUM('Parent transaction ID (polymorphic)'),
  parent_model:   STR('Parent model discriminator'),
  company:        STR('Company name'),
  attention:      STR('Attention line'),
  address_full:   STR('Denormalized full address'),
  email:          STR('Primary email'),
  phone:          STR('Primary phone'),
  dt_needed:      NUM('Date needed (UTC epoch ms)'),
  line_increment: NUM('Next line_number increment (default 10)'),
  source_name:    STR('Source attribution (Facebook, Referral, Walk-in, etc.)'),
  conditions_id:  NUM('Conditions/terms FK'),
  conditions_description: STR('Conditions description'),
  dt_journaled:   NUM('UTC epoch ms when journalized to GL; 0 = editable'),
};

const LINE_FIELDS: Record<string, SchemaNode> = {
  line_number: NUM('Line sequence number'),
  line_type:   STR('product | tax | shipping | discount'),
  item_id:     NUM('FK → Item'),
};

// ─── Build model schemas ─────────────────────────────────────────────

function txnSchema(label: string): ModelSchema {
  return {
    label,
    envelopes: {
      _core:   OBJ('CoreModel fields (all models)', CORE_FIELDS),
      _base:   OBJ('BaseModel fields', BASE_EXTRA_FIELDS),
      _txn:    OBJ('Transaction fields', TXN_FIELDS),
      totals:  OBJ('Header totals — source of truth for all financial display', TOTALS_ENVELOPE),
      sell:    OBJ('Sell-side aggregates', SELL_ENVELOPE),
      cost:    OBJ('Cost-side aggregates', COST_ENVELOPE),
      finance: OBJ('Tax configuration and rates', FINANCE_ENVELOPE),
      source:  OBJ('Source attribution', SOURCE_ENVELOPE),
      flow:    OBJ('Transaction flow', FLOW_ENVELOPE),
      total:   NUM('⚠ QUERY INDEX ONLY — use totals.total', true),
      balance: NUM('⚠ QUERY INDEX ONLY — use totals.balance', true),
      ...BASE_ENVELOPES,
    },
  };
}

function lineSchema(label: string): ModelSchema {
  return {
    label,
    envelopes: {
      _core:    OBJ('CoreModel fields (all models)', CORE_FIELDS),
      _line:    OBJ('Line fields', LINE_FIELDS),
      price:    OBJ('Sell-side pricing per line', LINE_PRICE_ENVELOPE),
      cost:     OBJ('Cost-side per line', LINE_COST_ENVELOPE),
      quantity: OBJ('Quantity envelope', LINE_QUANTITY_ENVELOPE),
      ...BASE_ENVELOPES,
    },
  };
}

function baseSchema(label: string, extra?: Record<string, SchemaNode>): ModelSchema {
  return {
    label,
    envelopes: {
      _core: OBJ('CoreModel fields (all models)', CORE_FIELDS),
      _base: OBJ('BaseModel fields', BASE_EXTRA_FIELDS),
      ...BASE_ENVELOPES,
      ...extra,
    },
  };
}

export const ENVELOPE_SCHEMAS: Record<string, ModelSchema> = {
  // Transaction headers
  invoice:    txnSchema('Invoice'),
  order:      txnSchema('Order'),
  proposal:   txnSchema('Proposal'),
  purchase:   txnSchema('Purchase'),
  workorder:  txnSchema('Work Order'),

  // Transaction lines
  invoice_line:   lineSchema('Invoice Line'),
  order_line:     lineSchema('Order Line'),
  proposal_line:  lineSchema('Proposal Line'),
  purchase_line:  lineSchema('Purchase Line'),
  workorder_line: lineSchema('Work Order Line'),

  // Payment
  payment: {
    label: 'Payment',
    envelopes: {
      _core:    OBJ('CoreModel fields (all models)', CORE_FIELDS),
      _base:    OBJ('BaseModel fields', BASE_EXTRA_FIELDS),
      _payment: OBJ('Payment fields', PAYMENT_FIELDS),
      ...BASE_ENVELOPES,
    },
  },

  // Core models
  contact:    baseSchema('Contact'),
  item:       baseSchema('Item'),
  serial:     baseSchema('Serial'),
  action:     baseSchema('Action'),
  setting:    baseSchema('Setting'),
  pending:    baseSchema('Pending'),
  ledger:     baseSchema('Ledger'),
  orgbase:    baseSchema('Organization'),

  // Accounts
  taxjurisdiction: baseSchema('Tax Jurisdiction', {
    scripts: OBJ('Tax calculation scripts', {}),
  }),
  audit: baseSchema('Audit', {
    conflicts:       OBJ('Conflict data', {}),
    changes:         OBJ('Change data', {}),
    recommendations: OBJ('Recommendations', {}),
  }),
  paymentterm: baseSchema('Payment Term'),

  // Documents
  document: baseSchema('Document', {
    copyright: OBJ('Copyright info', COPYRIGHT_ENVELOPE),
    path:      OBJ('Document path/location', {}),
  }),
  tag: baseSchema('Tag'),
  questionanswer: baseSchema('Question/Answer', {
    answered_by: OBJ('Who answered', {
      id:        NUM('Contact ID'),
      attention: STR('Contact name'),
    }),
  }),

  // Reports
  report: baseSchema('Report', {
    paths: OBJ('Report file paths', {}),
  }),

  // Sync
  connection: baseSchema('Connection', {
    scripts:       OBJ('Sync scripts', {}),
    relationships: OBJ('Relationship maps', {}),
    maps:          OBJ('Field maps', {}),
    encryption:    OBJ('Encryption config', {}),
    rules:         OBJ('Sync rules', {}),
    conflicts:     OBJ('Conflict resolution', {}),
    changes:       OBJ('Change tracking', {}),
  }),
  bundle: baseSchema('Bundle', {
    response:   OBJ('Response data', {}),
    payload:    OBJ('Payload data', {}),
    maps:       OBJ('Field maps', {}),
    encryption: OBJ('Encryption config', {}),
    rules:      OBJ('Sync rules', {}),
    conflicts:  OBJ('Conflict data', {}),
  }),

  // Conversion
  conversionproject: baseSchema('Conversion Project', {
    stats: OBJ('Conversion statistics', {}),
  }),

  // Products
  receipt: baseSchema('Receipt'),
  bom:     baseSchema('Bill of Materials'),
  project: baseSchema('Project'),

  // Scheduler
  scheduledtask: baseSchema('Scheduled Task', {
    default_kwargs: OBJ('Default task arguments', {}),
  }),
  taskrun: baseSchema('Task Run', {
    kwargs: OBJ('Arguments passed to task', {}),
    result: OBJ('Task return value', {}),
  }),

  // Statement
  statement_line: baseSchema('Statement Line'),

  // Payment application
  payment_application: baseSchema('Payment Application'),
};

// ═══════════════════════════════════════════════════════════════════════
// Tree node renderer
// ═══════════════════════════════════════════════════════════════════════

interface NodeProps {
  name: string;
  node: SchemaNode;
  path: string;
  depth: number;
  onCopy: (path: string) => void;
}

const SchemaTreeNode: React.FC<NodeProps> = ({ name, node, path, depth, onCopy }) => {
  // Keys starting with _ are structural groups (e.g., _core, _base, _txn).
  // Their children are direct model fields — don't include the group name in paths.
  const isGroup = name.startsWith('_');
  const [open, setOpen] = useState(depth < 2);
  const hasChildren = node.children && Object.keys(node.children).length > 0;
  const fullPath = isGroup ? '' : (path ? `${path}.${name}` : name);
  const displayName = isGroup ? name.slice(1) : name;

  const typeColor = node.indexOnly ? '#dc2626'
    : node.type === 'number' ? '#0d6efd'
    : node.type === 'string' ? '#198754'
    : node.type === 'boolean' ? '#d97706'
    : node.type === 'array' ? '#8b5cf6'
    : node.type === 'object' ? '#6c757d'
    : '#adb5bd';

  return (
    <div style={{ marginLeft: depth * 16 }}>
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '2px 4px', borderRadius: 3, cursor: 'pointer',
          fontFamily: 'monospace', fontSize: 13, lineHeight: '22px',
        }}
        className="hover:bg-slate-100 dark:hover:bg-slate-800"
        onClick={(e) => {
          if (hasChildren) { setOpen(!open); return; }
          onCopy(fullPath);
        }}
        title={hasChildren ? 'Click to expand' : `Click to copy: ${fullPath}`}
      >
        {hasChildren
          ? <span style={{ width: 14, textAlign: 'center', color: '#94a3b8' }}>{open ? '▾' : '▸'}</span>
          : <span style={{ width: 14, textAlign: 'center', color: '#cbd5e1' }}>·</span>
        }
        <span style={{ fontWeight: hasChildren ? 600 : 400 }}>{displayName}</span>
        <span style={{ color: typeColor, fontSize: 11 }}>
          {node.indexOnly ? '⚠ index' : node.type}
        </span>
        {node.description && (
          <span style={{ color: '#94a3b8', fontSize: 11, marginLeft: 4 }}>
            — {node.description}
          </span>
        )}
        {!hasChildren && !node.indexOnly && (
          <span style={{ color: '#cbd5e1', fontSize: 10, marginLeft: 'auto' }}>
            {fullPath}
          </span>
        )}
      </div>
      {open && hasChildren && Object.entries(node.children!).map(([key, child]) => (
        <SchemaTreeNode key={key} name={key} node={child} path={fullPath} depth={depth + 1} onCopy={onCopy} />
      ))}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════
// Main component
// ═══════════════════════════════════════════════════════════════════════

interface JsonSchemaTreeProps {
  /** Model name (e.g., 'invoice', 'order_line') */
  modelName: string;
  /** Print mode — full page, no interactivity */
  printMode?: boolean;
  /** Called when user copies a path */
  onCopy?: (path: string) => void;
}

export const JsonSchemaTree: React.FC<JsonSchemaTreeProps> = ({ modelName, printMode = false, onCopy }) => {
  const [copied, setCopied] = useState('');
  const schema = ENVELOPE_SCHEMAS[modelName];

  const handleCopy = useCallback((path: string) => {
    navigator.clipboard?.writeText(path);
    setCopied(path);
    setTimeout(() => setCopied(''), 1500);
    onCopy?.(path);
  }, [onCopy]);

  if (!schema) {
    return (
      <div style={{ padding: 16, fontSize: 13 }}>
        <div style={{ color: '#94a3b8', fontFamily: 'monospace' }}>
          No JSON envelope schema defined for "{modelName}".
        </div>
        <div style={{ color: '#64748b', fontSize: 11, marginTop: 8 }}>
          This model inherits BaseModel envelopes (metadata, refs, prefs, comments, actions, config).
          Add its schema to JsonSchemaTree.tsx to see the full tree.
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: printMode ? 0 : 12 }}>
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 15, fontWeight: 700 }}>{schema.label}</div>
        {!printMode && (
          <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
            Click a leaf to copy its path. JSON envelope is the source of truth.
          </div>
        )}
        {printMode && (
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
            JSON envelope paths — use these in field references.
          </div>
        )}
      </div>

      {copied && !printMode && (
        <div style={{
          padding: '4px 10px', marginBottom: 8, borderRadius: 4,
          background: '#059669', color: '#fff', fontSize: 12, fontFamily: 'monospace',
          display: 'inline-block',
        }}>
          Copied: {copied}
        </div>
      )}

      {Object.entries(schema.envelopes).map(([key, node]) => (
        <SchemaTreeNode key={key} name={key} node={node} path="" depth={0} onCopy={handleCopy} />
      ))}

      {printMode && (
        <div style={{ marginTop: 24, fontSize: 10, color: '#94a3b8', borderTop: '1px solid #e2e8f0', paddingTop: 8 }}>
          Generated by WebClerk — JSON envelope is the single source of truth.
        </div>
      )}
    </div>
  );
};

export default JsonSchemaTree;
