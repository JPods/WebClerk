/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * RefsPanel - Display and edit entity .refs object (relationships & lineage)
 *
 * Role-based access:
 * - View: Admin only (default)
 * - Edit: Admin only (default)
 *
 * @example
 * <RefsPanel
 *   entityType="contact"
 *   entityId={123}
 *   data={contact.refs}
 *   onChange={(refs) => setContact({ ...contact, refs })}
 * />
 */
import React, { useState } from "react";
import {
  FaLink,
  FaChevronDown,
  FaChevronUp,
  FaTrash,
  FaUser,
  FaBuilding,
  FaFileAlt,
  FaEnvelope,
  FaPhone,
  FaMapMarkerAlt,
  FaShoppingCart,
  FaFileInvoice,
  FaBox,
  FaGlobe,
  FaProjectDiagram,
} from "react-icons/fa";
import { usePermissions } from "./usePermissions";
import type { BasePanelProps, EntityRefs, RefLink } from "./types";
import { withDevIdentifier } from "@/components/common/DevIdentifier";

function syntaxHighlightJson(json: string): string {
  return json.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
    (match) => {
      let color = "var(--db-accent)";
      if (/^"/.test(match)) {
        color = /:$/.test(match)
          ? "var(--db-accent)"
          : "var(--db-accent-green)";
      } else if (/true|false/.test(match)) {
        color = "var(--db-accent-gold)";
      } else if (/null/.test(match)) {
        color = "var(--db-accent-red)";
      }
      return `<span style="color:${color}">${match}</span>`;
    },
  );
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RefsPanelProps extends Omit<BasePanelProps<EntityRefs>, "data"> {
  /** Refs object */
  data?: EntityRefs;
  /** Whether to show link navigation */
  navigable?: boolean;
  /** Callback when navigating to a linked entity */
  onNavigate?: (type: string, id: number) => void;
}

// ---------------------------------------------------------------------------
// Link Type Icons
// ---------------------------------------------------------------------------

const LINK_ICONS: Record<string, React.ReactNode> = {
  contact: <FaUser size={12} />,
  customer: <FaBuilding size={12} />,
  vendor: <FaBuilding size={12} />,
  manufacturer: <FaBuilding size={12} />,
  employee: <FaUser size={12} />,
  rep: <FaUser size={12} />,
  order: <FaShoppingCart size={12} />,
  invoice: <FaFileInvoice size={12} />,
  purchase: <FaShoppingCart size={12} />,
  proposal: <FaFileAlt size={12} />,
  workorder: <FaBox size={12} />,
  item: <FaBox size={12} />,
  email: <FaEnvelope size={12} />,
  phone: <FaPhone size={12} />,
  address: <FaMapMarkerAlt size={12} />,
  domain: <FaGlobe size={12} />,
  document: <FaFileAlt size={12} />,
  project: <FaProjectDiagram size={12} />,
};

// ---------------------------------------------------------------------------
// Link List Component
// ---------------------------------------------------------------------------

interface LinkListProps {
  type: string;
  links: RefLink[];
  canEdit: boolean;
  navigable: boolean;
  onNavigate?: (type: string, id: number) => void;
  onDelete?: (type: string, id: number) => void;
}

const LinkList: React.FC<LinkListProps> = ({
  type,
  links,
  canEdit,
  navigable,
  onNavigate,
  onDelete,
}) => {
  const [isExpanded, setIsExpanded] = useState(links.length <= 5);
  const icon = LINK_ICONS[type] || <FaLink size={12} />;

  if (links.length === 0) return null;

  return (
    <div className="last:border-b-0 py-2" style={{ borderBottom: '1px solid var(--db-border-light)' }}>
      {/* Header */}
      <div
        className="flex items-center gap-2 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span style={{ color: 'var(--db-text-dim)' }}>{icon}</span>
        <span className="text-xs font-semibold capitalize" style={{ color: 'var(--db-text)' }}>
          {type.replace(/_/g, " ")}
        </span>
        <span className="text-xs" style={{ color: 'var(--db-text-dim)' }}>({links.length})</span>
        {isExpanded ? <FaChevronUp size={10} /> : <FaChevronDown size={10} />}
      </div>

      {/* Links */}
      {isExpanded && (
        <div className="mt-2 ml-6 space-y-1">
          {links.map((link, idx) => (
            <div key={link.id || idx} className="flex items-center gap-2 group">
              <span className="text-xs font-mono" style={{ color: 'var(--db-text-muted)' }}>
                #{link.id}
              </span>
              {link.ida && (
                <span className="text-xs" style={{ color: 'var(--db-text-dim)' }}>[{link.ida}]</span>
              )}
              <span
                className={`text-xs flex-1 truncate ${
                  navigable && onNavigate
                    ? "cursor-pointer hover:underline"
                    : ""
                }`}
                style={{ color: 'var(--db-text)' }}
                onClick={() =>
                  navigable &&
                  onNavigate &&
                  link.id &&
                  onNavigate(type, link.id)
                }
                title={link.display || link.name || ""}
              >
                {link.email ||
                  link.number ||
                  link.full ||
                  link.domain ||
                  link.display ||
                  link.name ||
                  `${type} #${link.id}`}
              </span>
              {link.purpose && (
                <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: 'var(--db-surface-alt)', color: 'var(--db-text-muted)' }}>
                  {link.purpose}
                </span>
              )}
              {canEdit && onDelete && (
                <button
                  onClick={() => onDelete(type, link.id)}
                  className="p-1 opacity-0 group-hover:opacity-100 rounded"
                  style={{ color: 'var(--db-accent-red)' }}
                  title="Remove link"
                >
                  <FaTrash size={10} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Lineage Component
// ---------------------------------------------------------------------------

interface LineageProps {
  lineage: EntityRefs["lineage"];
  navigable: boolean;
  onNavigate?: (type: string, id: number) => void;
}

const Lineage: React.FC<LineageProps> = ({
  lineage,
  navigable,
  onNavigate,
}) => {
  if (!lineage) return null;

  const { parent_id, parent_model, source_id, source_type } = lineage;
  const hasLineage = parent_id || source_id;

  if (!hasLineage) return null;

  return (
    <div className="py-2" style={{ borderBottom: '1px solid var(--db-border-light)' }}>
      <div className="flex items-center gap-2 mb-2">
        <FaProjectDiagram style={{ color: 'var(--db-text-dim)' }} size={12} />
        <span className="text-xs font-semibold" style={{ color: 'var(--db-text)' }}>
          Lineage
        </span>
      </div>
      <div className="ml-6 space-y-1">
        {parent_id && parent_model && (
          <div className="flex items-center gap-2 text-xs">
            <span style={{ color: 'var(--db-text-muted)' }}>Parent:</span>
            <span
              className={`${
                navigable && onNavigate
                  ? "cursor-pointer hover:underline"
                  : ""
              }`}
              style={{ color: 'var(--db-text)' }}
              onClick={() =>
                navigable && onNavigate && onNavigate(parent_model, parent_id)
              }
            >
              {parent_model} #{parent_id}
            </span>
          </div>
        )}
        {source_id && source_type && (
          <div className="flex items-center gap-2 text-xs">
            <span style={{ color: 'var(--db-text-muted)' }}>Source:</span>
            <span
              className={`${
                navigable && onNavigate
                  ? "cursor-pointer hover:underline"
                  : ""
              }`}
              style={{ color: 'var(--db-text)' }}
              onClick={() =>
                navigable && onNavigate && onNavigate(source_type, source_id)
              }
            >
              {source_type} #{source_id}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main RefsPanel Component
// ---------------------------------------------------------------------------

const RefsPanel: React.FC<RefsPanelProps> = ({
  entityType: _entityType,
  entityId: _entityId,
  data = {},
  onChange,
  readOnly = false,
  viewRoles,
  editRoles,
  className = "",
  compact = false,
  title = "References",
  defaultCollapsed = false,
  navigable = true,
  onNavigate,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);

  // Check permissions (admin only by default)
  const {
    canView,
    canEdit: permCanEdit,
    isAdmin,
  } = usePermissions({
    panelType: "refs",
    viewRoles,
    editRoles,
    forceReadOnly: readOnly,
  });

  const canEdit = permCanEdit && !!onChange;

  // Don't render if user can't view
  if (!canView) return null;

  const handleDeleteLink = (type: string, id: number) => {
    if (!onChange || !data.links) return;

    const typeLinks = data.links[type];
    if (!typeLinks) return;

    const newLinks = typeLinks.filter((link: RefLink) => link.id !== id);
    onChange({
      ...data,
      links: {
        ...data.links,
        [type]: newLinks,
      },
    });
  };

  // Count total links
  const links = data?.links || {};
  const linkTypes = Object.keys(links).filter((key) => {
    const arr = links[key];
    return Array.isArray(arr) && arr.length > 0;
  });
  const totalLinks = linkTypes.reduce((sum, key) => {
    const arr = links[key];
    return sum + (Array.isArray(arr) ? arr.length : 0);
  }, 0);

  return (
    <div
      className={`rounded-lg ${className}`}
      style={{ background: 'var(--db-surface)', border: '1px solid var(--db-border)' }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer rounded-t-lg"
        style={{ background: 'var(--db-surface-alt)', borderBottom: '1px solid var(--db-border)' }}
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaLink style={{ color: 'var(--db-accent)' }} size={14} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--db-text)' }}>
            {title}
          </h3>
          <span className="px-1.5 py-0.5 text-xs rounded" style={{ background: 'var(--db-surface-alt)', color: 'var(--db-text)' }}>
            Admin
          </span>
          <span className="text-xs" style={{ color: 'var(--db-text-muted)' }}>
            {totalLinks} {totalLinks === 1 ? "link" : "links"}
          </span>
        </div>
        {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className={`${compact ? "p-2" : "p-4"}`}>
          {/* Lineage */}
          <Lineage
            lineage={data?.lineage}
            navigable={navigable}
            onNavigate={onNavigate}
          />

          {/* Links */}
          {linkTypes.length === 0 && !data?.lineage ? (
            <div className="text-center py-4 text-sm" style={{ color: 'var(--db-text-dim)' }}>
              No references defined
            </div>
          ) : (
            linkTypes.map((type) => (
              <LinkList
                key={type}
                type={type}
                links={links[type] as RefLink[]}
                canEdit={canEdit}
                navigable={navigable}
                onNavigate={onNavigate}
                onDelete={canEdit ? handleDeleteLink : undefined}
              />
            ))
          )}

          {/* Raw JSON toggle for admin */}
          {isAdmin && (
            <details className="mt-4">
              <summary className="text-xs cursor-pointer" style={{ color: 'var(--db-text-dim)' }}>
                View raw JSON
              </summary>
              <pre
                className="mt-2 text-xs font-mono p-2 rounded overflow-x-auto max-h-48 whitespace-pre-wrap"
                style={{ background: 'var(--db-surface-alt)', color: 'var(--db-text)' }}
                dangerouslySetInnerHTML={{
                  __html: syntaxHighlightJson(JSON.stringify(data, null, 2)),
                }}
              />
            </details>
          )}
        </div>
      )}
    </div>
  );
};

export default withDevIdentifier(RefsPanel, "RefsPanel", "teal", 'apps/common/components/panels/RefsPanel.tsx');
