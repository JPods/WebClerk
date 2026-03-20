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
      let cls = "text-violet-700 dark:text-violet-400";
      if (/^"/.test(match)) {
        cls = /:$/.test(match)
          ? "text-sky-700 dark:text-sky-400"
          : "text-emerald-700 dark:text-emerald-400";
      } else if (/true|false/.test(match)) {
        cls = "text-amber-700 dark:text-amber-400";
      } else if (/null/.test(match)) {
        cls = "text-rose-700 dark:text-rose-400";
      }
      return `<span class="${cls}">${match}</span>`;
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
    <div className="border-b border-slate-100 dark:border-slate-700 last:border-b-0 py-2">
      {/* Header */}
      <div
        className="flex items-center gap-2 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="text-slate-400">{icon}</span>
        <span className="text-xs font-semibold text-slate-600 dark:text-slate-300 capitalize">
          {type.replace(/_/g, " ")}
        </span>
        <span className="text-xs text-slate-400">({links.length})</span>
        {isExpanded ? <FaChevronUp size={10} /> : <FaChevronDown size={10} />}
      </div>

      {/* Links */}
      {isExpanded && (
        <div className="mt-2 ml-6 space-y-1">
          {links.map((link, idx) => (
            <div key={link.id || idx} className="flex items-center gap-2 group">
              <span className="text-xs text-slate-500 font-mono">
                #{link.id}
              </span>
              {link.ida && (
                <span className="text-xs text-slate-400">[{link.ida}]</span>
              )}
              <span
                className={`text-xs text-slate-700 dark:text-slate-300 flex-1 truncate ${
                  navigable && onNavigate
                    ? "cursor-pointer hover:text-blue-600 hover:underline"
                    : ""
                }`}
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
                <span className="text-xs px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-500 rounded">
                  {link.purpose}
                </span>
              )}
              {canEdit && onDelete && (
                <button
                  onClick={() => onDelete(type, link.id)}
                  className="p-1 text-red-500 opacity-0 group-hover:opacity-100 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
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
    <div className="border-b border-slate-100 dark:border-slate-700 py-2">
      <div className="flex items-center gap-2 mb-2">
        <FaProjectDiagram className="text-slate-400" size={12} />
        <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">
          Lineage
        </span>
      </div>
      <div className="ml-6 space-y-1">
        {parent_id && parent_model && (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500">Parent:</span>
            <span
              className={`text-slate-700 dark:text-slate-300 ${
                navigable && onNavigate
                  ? "cursor-pointer hover:text-blue-600 hover:underline"
                  : ""
              }`}
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
            <span className="text-slate-500">Source:</span>
            <span
              className={`text-slate-700 dark:text-slate-300 ${
                navigable && onNavigate
                  ? "cursor-pointer hover:text-blue-600 hover:underline"
                  : ""
              }`}
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
      className={`bg-white dark:bg-slate-800 rounded-lg border border-cyan-200 dark:border-cyan-800 ${className}`}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-cyan-50 dark:bg-cyan-900/20 border-b border-cyan-200 dark:border-cyan-800 cursor-pointer rounded-t-lg"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaLink className="text-cyan-500" size={14} />
          <h3 className="text-sm font-semibold text-cyan-700 dark:text-cyan-300">
            {title}
          </h3>
          <span className="px-1.5 py-0.5 text-xs bg-cyan-200 dark:bg-cyan-800 text-cyan-700 dark:text-cyan-300 rounded">
            Admin
          </span>
          <span className="text-xs text-cyan-600 dark:text-cyan-400">
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
            <div className="text-center py-4 text-slate-400 text-sm">
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
              <summary className="text-xs text-slate-400 cursor-pointer hover:text-slate-600">
                View raw JSON
              </summary>
              <pre
                className="mt-2 text-xs font-mono bg-slate-50 dark:bg-slate-900 p-2 rounded overflow-x-auto max-h-48 whitespace-pre-wrap"
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

export default withDevIdentifier(RefsPanel, "RefsPanel", "teal");
