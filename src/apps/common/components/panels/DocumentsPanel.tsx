/**
 * DocumentsPanel - Display and manage entity documents/attachments
 * 
 * Data source: refs.links.document
 * 
 * Role-based access:
 * - View: All roles (default)
 * - Edit: User+ roles (default)
 */
import React, { useState, useRef } from 'react';
import { 
  FaFile, FaChevronDown, FaChevronUp, FaPlus, FaTrash, FaDownload,
  FaFilePdf, FaFileImage, FaFileWord, FaFileExcel, FaFileAlt
} from 'react-icons/fa';
import { usePermissions } from './usePermissions';
import type { BasePanelProps, DocumentEntry } from './types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DocumentsPanelProps extends Omit<BasePanelProps<DocumentEntry[]>, 'data'> {
  /** Documents array */
  data?: DocumentEntry[];
  /** Callback for file upload */
  onUpload?: (file: File) => Promise<DocumentEntry>;
}

// ---------------------------------------------------------------------------
// File Type Helpers
// ---------------------------------------------------------------------------

const getFileIcon = (type?: string, name?: string): React.ReactNode => {
  const ext = name?.split('.').pop()?.toLowerCase() || type?.split('/').pop() || '';
  
  if (['pdf'].includes(ext) || type?.includes('pdf')) {
    return <FaFilePdf className="text-red-500" />;
  }
  if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext) || type?.startsWith('image/')) {
    return <FaFileImage className="text-blue-500" />;
  }
  if (['doc', 'docx'].includes(ext) || type?.includes('word')) {
    return <FaFileWord className="text-blue-600" />;
  }
  if (['xls', 'xlsx', 'csv'].includes(ext) || type?.includes('sheet') || type?.includes('excel')) {
    return <FaFileExcel className="text-green-600" />;
  }
  return <FaFileAlt className="text-slate-500" />;
};

const formatFileSize = (bytes?: number): string => {
  if (!bytes) return '--';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const formatDate = (dateStr?: string): string => {
  if (!dateStr) return '--';
  return new Date(dateStr).toLocaleDateString(undefined, { 
    month: 'short', 
    day: 'numeric', 
    year: 'numeric' 
  });
};

// ---------------------------------------------------------------------------
// Document Row Component
// ---------------------------------------------------------------------------

interface DocumentRowProps {
  doc: DocumentEntry;
  canEdit: boolean;
  onDelete?: () => void;
}

const DocumentRow: React.FC<DocumentRowProps> = ({ doc, canEdit, onDelete }) => (
  <div className="flex items-center gap-3 p-2 hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded group">
    {/* Icon */}
    <div className="text-xl">
      {getFileIcon(doc.type, doc.name)}
    </div>

    {/* Info */}
    <div className="flex-1 min-w-0">
      <p className="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">
        {doc.name}
      </p>
      <div className="flex items-center gap-3 text-xs text-slate-500">
        <span>{formatFileSize(doc.size)}</span>
        {doc.uploaded_at && <span>{formatDate(doc.uploaded_at)}</span>}
        {doc.uploaded_by && <span>by {doc.uploaded_by}</span>}
      </div>
    </div>

    {/* Actions */}
    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
      {doc.url && (
        <a
          href={doc.url}
          target="_blank"
          rel="noopener noreferrer"
          className="p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
          title="Download"
        >
          <FaDownload size={12} />
        </a>
      )}
      {canEdit && onDelete && (
        <button
          onClick={onDelete}
          className="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
          title="Delete"
        >
          <FaTrash size={12} />
        </button>
      )}
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Main DocumentsPanel Component
// ---------------------------------------------------------------------------

const DocumentsPanel: React.FC<DocumentsPanelProps> = ({
  entityType: _entityType,
  entityId: _entityId,
  data = [],
  onChange,
  onUpload,
  readOnly = false,
  viewRoles,
  editRoles,
  className = '',
  compact = false,
  title = 'Documents',
  defaultCollapsed = false,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Check permissions
  const { canView, canEdit: permCanEdit } = usePermissions({
    panelType: 'documents',
    viewRoles,
    editRoles,
    forceReadOnly: readOnly,
  });

  const canEdit = permCanEdit && !!onChange;

  if (!canView) return null;

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (onUpload) {
      setIsUploading(true);
      try {
        const newDoc = await onUpload(file);
        if (onChange) {
          onChange([...data, newDoc]);
        }
      } catch (err) {
        console.error('Upload failed:', err);
      } finally {
        setIsUploading(false);
      }
    } else if (onChange) {
      // Create local document entry without actual upload
      const newDoc: DocumentEntry = {
        id: Date.now(),
        name: file.name,
        type: file.type,
        size: file.size,
        uploaded_at: new Date().toISOString(),
        uploaded_by: 'current_user',
      };
      onChange([...data, newDoc]);
    }

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDelete = (index: number) => {
    if (!onChange) return;
    onChange(data.filter((_, i) => i !== index));
  };

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 ${className}`}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 cursor-pointer"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaFile className="text-slate-400" size={14} />
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">{title}</h3>
          {data.length > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-full">
              {data.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {canEdit && !isCollapsed && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                fileInputRef.current?.click();
              }}
              disabled={isUploading}
              className="p-1 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded disabled:opacity-50"
              title="Upload document"
            >
              <FaPlus size={12} />
            </button>
          )}
          {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Content */}
      {!isCollapsed && (
        <div className={compact ? 'p-2' : 'p-4'}>
          {isUploading && (
            <div className="mb-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded text-xs text-blue-600">
              Uploading...
            </div>
          )}

          {data.length === 0 ? (
            <div className="text-center py-4 text-slate-400 text-sm">
              <FaFile size={24} className="mx-auto mb-2 opacity-50" />
              <p>No documents attached</p>
              {canEdit && (
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="mt-2 text-blue-600 hover:underline text-xs"
                >
                  + Upload first document
                </button>
              )}
            </div>
          ) : (
            <div className="divide-y divide-slate-100 dark:divide-slate-700">
              {data.map((doc, index) => (
                <DocumentRow
                  key={doc.id || index}
                  doc={doc}
                  canEdit={canEdit}
                  onDelete={() => handleDelete(index)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DocumentsPanel;
