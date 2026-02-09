/**
 * DocumentsPanel - Display and manage entity documents/attachments
 * 
 * Data source: refs.links.document
 * 
 * Upload flow:
 * 1. File selected → upload to storage
 * 2. Create Document record with metadata
 * 3. Add RefLink to parent's refs.links.document[]
 * 
 * Role-based access:
 * - View: All roles (default)
 * - Edit: User+ roles (default)
 * 
 * @see readmes/topics/document-uploads.md
 */
import React, { useState, useRef } from 'react';
import { 
  FaFile, FaChevronDown, FaChevronUp, FaPlus, FaTrash, FaDownload,
  FaFilePdf, FaFileImage, FaFileWord, FaFileExcel, FaFileAlt, FaSpinner
} from 'react-icons/fa';
import { usePermissions } from './usePermissions';
import type { BasePanelProps, RefLink } from './types';
import { 
  uploadDocument, 
  deleteDocument as deleteDocRecord,
  getDocumentUrl,
  formatFileSize as formatSize,
} from './documentUpload';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Extended document entry with document_id for API tracking */
interface DocumentRefLink extends RefLink {
  /** Document record ID */
  document_id?: number;
  /** File size in bytes */
  size?: number;
  /** Upload timestamp */
  uploaded_at?: string;
  /** Uploader identifier */
  uploaded_by?: string;
  /** Direct URL to file */
  url?: string;
}

interface DocumentsPanelProps extends Omit<BasePanelProps<DocumentRefLink[]>, 'data' | 'entityType' | 'entityId'> {
  /** Parent entity type (e.g., 'sales_order', 'contact') */
  parentType?: string;
  /** Parent entity ID */
  parentId?: number;
  /** Documents array (RefLinks from refs.links.document) */
  data?: DocumentRefLink[];
  /** Purpose/category for uploaded documents */
  purpose?: string;
  /** Max file size in bytes */
  maxFileSize?: number;
  /** Allowed file extensions */
  allowedExtensions?: string[];
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
  return formatSize(bytes);
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
  doc: DocumentRefLink;
  canEdit: boolean;
  onDelete?: () => void;
  onDownload?: () => void;
}

const DocumentRow: React.FC<DocumentRowProps> = ({ doc, canEdit, onDelete, onDownload }) => (
  <div className="flex items-center gap-3 p-2 hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded group">
    {/* Icon */}
    <div className="text-xl">
      {getFileIcon(doc.type, doc.name)}
    </div>

    {/* Info */}
    <div className="flex-1 min-w-0">
      <p className="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">
        {doc.name || doc.display || 'Untitled'}
      </p>
      <div className="flex items-center gap-3 text-xs text-slate-500">
        <span>{formatFileSize(doc.size)}</span>
        {doc.uploaded_at && <span>{formatDate(doc.uploaded_at)}</span>}
        {doc.uploaded_by && <span>by {doc.uploaded_by}</span>}
      </div>
    </div>

    {/* Actions */}
    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
      {(doc.url || doc.document_id) && (
        <button
          onClick={onDownload}
          className="p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
          title="Download"
        >
          <FaDownload size={12} />
        </button>
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
  parentType,
  parentId,
  data = [],
  onChange,
  purpose = 'attachment',
  maxFileSize,
  allowedExtensions,
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
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Check permissions
  const { canView, canEdit: permCanEdit } = usePermissions({
    panelType: 'documents',
    viewRoles,
    editRoles,
    forceReadOnly: readOnly,
  });

  // Can edit only if we have onChange callback AND (parentType/parentId for API mode OR just onChange for local mode)
  const canEdit = permCanEdit && !!onChange;
  const hasApiPersistence = !!(parentType && parentId);

  if (!canView) return null;

  const validateFile = (file: File): string | null => {
    if (maxFileSize && file.size > maxFileSize) {
      return `File size exceeds maximum of ${formatSize(maxFileSize)}`;
    }
    if (allowedExtensions) {
      const ext = file.name.split('.').pop()?.toLowerCase() || '';
      if (!allowedExtensions.includes(ext)) {
        return `File type .${ext} not allowed`;
      }
    }
    return null;
  };

  const uploadFiles = async (files: File[]) => {
    if (!files.length) return;
    if (!onChange) return;

    const firstError = files
      .map((f) => validateFile(f))
      .find((msg) => msg);
    if (firstError) {
      setError(firstError);
      return;
    }

    setError(null);
    setIsUploading(true);
    setUploadProgress(0);
    setUploadStatus(null);

    try {
      let nextDocs = [...data];

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setUploadStatus(`Uploading ${file.name} (${i + 1}/${files.length})`);

        if (hasApiPersistence) {
          const result = await uploadDocument(
            {
              file,
              parentType: parentType!,
              parentId: parentId!,
              purpose,
            },
            (p) => {
              const overall = ((i + p / 100) / files.length) * 100;
              setUploadProgress(Math.max(0, Math.min(100, Math.round(overall))));
            },
          );

          const docRefLink: DocumentRefLink = {
            id: result.document.id,
            document_id: result.document.id,
            name: result.document.name,
            display: result.document.name,
            type: result.document.mime_type,
            purpose,
            size: result.document.size_bytes,
            uploaded_at: new Date().toISOString(),
            url: result.url,
          };

          nextDocs = [...nextDocs, docRefLink];
          onChange(nextDocs);
        } else {
          const localDoc: DocumentRefLink = {
            id: Date.now() + i,
            name: file.name,
            display: file.name,
            type: file.type,
            size: file.size,
            uploaded_at: new Date().toISOString(),
            uploaded_by: 'current_user',
          };
          nextDocs = [...nextDocs, localDoc];
          onChange(nextDocs);
        }
      }
    } catch (err) {
      console.error('Upload failed:', err);
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
      setUploadStatus(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    await uploadFiles(files);
  };

  const handleDelete = async (index: number) => {
    if (!onChange) return;

    const ok = window.confirm('Delete this document? This cannot be undone.');
    if (!ok) return;

    const doc = data[index];

    // If we have a document_id, delete the Document record too
    if (hasApiPersistence && doc.document_id) {
      try {
        await deleteDocRecord(doc.document_id);
      } catch (err) {
        console.error('Failed to delete document record:', err);
      }
    }

    onChange(data.filter((_, i) => i !== index));
  };

  const handleDownload = async (doc: DocumentRefLink) => {
    if (doc.url) {
      window.open(doc.url, '_blank');
      return;
    }

    // Get presigned URL if we have document_id
    if (doc.document_id) {
      const url = await getDocumentUrl(doc.document_id);
      if (url) {
        window.open(url, '_blank');
      }
    }
  };

  // Build accept attribute for file input
  const acceptAttr = allowedExtensions 
    ? allowedExtensions.map(ext => `.${ext}`).join(',')
    : undefined;

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
              {isUploading ? <FaSpinner className="animate-spin" size={12} /> : <FaPlus size={12} />}
            </button>
          )}
          {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={acceptAttr}
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Content */}
      {!isCollapsed && (
        <div className={compact ? 'p-2' : 'p-4'}>
          {/* Dropzone */}
          {canEdit && (
            <div
              className={`mb-3 rounded-lg border border-dashed px-4 py-3 text-sm transition-colors ${
                isDragging
                  ? 'border-blue-400 bg-blue-50 dark:border-blue-700 dark:bg-blue-900/20'
                  : 'border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/30'
              }`}
              onDragEnter={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setIsDragging(true);
              }}
              onDragOver={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setIsDragging(true);
              }}
              onDragLeave={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setIsDragging(false);
              }}
              onDrop={async (e) => {
                e.preventDefault();
                e.stopPropagation();
                setIsDragging(false);
                const files = Array.from(e.dataTransfer.files ?? []);
                await uploadFiles(files);
              }}
              role="button"
              tabIndex={0}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  fileInputRef.current?.click();
                }
              }}
              aria-label="Upload documents"
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="font-medium text-slate-700 dark:text-slate-200">
                    Drag and drop files here
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    or click to browse
                  </div>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    fileInputRef.current?.click();
                  }}
                  disabled={isUploading}
                  className="px-3 py-2 rounded bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 disabled:opacity-50"
                >
                  {isUploading ? 'Uploading…' : 'Upload'}
                </button>
              </div>
            </div>
          )}

          {/* Upload progress */}
          {isUploading && (
            <div className="mb-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded text-xs text-blue-600">
              <div className="flex items-center gap-2">
                <FaSpinner className="animate-spin" size={10} />
                <span>
                  {uploadStatus || 'Uploading…'} {uploadProgress}%
                </span>
              </div>
              <div className="mt-1 h-1 bg-blue-100 rounded overflow-hidden">
                <div 
                  className="h-full bg-blue-500 transition-all duration-200"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="mb-2 p-2 bg-red-50 dark:bg-red-900/20 rounded text-xs text-red-600">
              {error}
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
                  + Upload documents
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
                  onDownload={() => handleDownload(doc)}
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
