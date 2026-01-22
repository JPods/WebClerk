/**
 * AttachmentsTab - Manage document attachments
 * Upload, view, download, and delete attachments
 */
import React, { useState, useRef, useCallback } from 'react';
import { 
  FaPaperclip, 
  FaUpload,
  FaDownload,
  FaTrash,
  FaFile,
  FaFilePdf,
  FaFileImage,
  FaFileWord,
  FaFileExcel,
  FaFileAlt,
  FaEye,
  FaTimes,
  FaCloudUploadAlt,
  FaSpinner
} from 'react-icons/fa';

interface Attachment {
  id: number;
  name: string;
  type: string;
  size: number;
  uploadedBy: string;
  uploadedAt: string;
  url?: string;
}

interface AttachmentsTabProps {
  transactionId?: number;
  attachments?: Attachment[];
  isEditing: boolean;
  isLocked?: boolean;
  onUpload?: (files: File[]) => Promise<void>;
  onDelete?: (attachmentId: number) => Promise<void>;
  onDownload?: (attachment: Attachment) => void;
}

// File type icons
const getFileIcon = (type: string): React.ElementType => {
  if (type.includes('pdf')) return FaFilePdf;
  if (type.includes('image')) return FaFileImage;
  if (type.includes('word') || type.includes('doc')) return FaFileWord;
  if (type.includes('excel') || type.includes('sheet') || type.includes('xls')) return FaFileExcel;
  if (type.includes('text')) return FaFileAlt;
  return FaFile;
};

// File type colors
const getFileColor = (type: string): string => {
  if (type.includes('pdf')) return 'text-red-500';
  if (type.includes('image')) return 'text-green-500';
  if (type.includes('word') || type.includes('doc')) return 'text-blue-500';
  if (type.includes('excel') || type.includes('sheet') || type.includes('xls')) return 'text-emerald-500';
  return 'text-slate-500';
};

// Format file size
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// Demo attachments
const demoAttachments: Attachment[] = [
  {
    id: 1,
    name: 'Quote_Request.pdf',
    type: 'application/pdf',
    size: 245000,
    uploadedBy: 'John Smith',
    uploadedAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 2,
    name: 'Product_Specs.docx',
    type: 'application/msword',
    size: 128000,
    uploadedBy: 'Jane Doe',
    uploadedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 3,
    name: 'Site_Photo.jpg',
    type: 'image/jpeg',
    size: 1540000,
    uploadedBy: 'Customer',
    uploadedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
  },
];

const AttachmentsTab: React.FC<AttachmentsTabProps> = ({
  transactionId: _transactionId, // For future API integration
  attachments = demoAttachments,
  isEditing,
  isLocked = false,
  onUpload,
  onDelete,
  onDownload,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);
  const [previewAttachment, setPreviewAttachment] = useState<Attachment | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const canUpload = isEditing && !isLocked;

  // Handle file selection
  const handleFileSelect = useCallback(async (files: FileList | File[]) => {
    if (!onUpload || !canUpload) return;
    
    const fileArray = Array.from(files);
    setIsUploading(true);
    try {
      await onUpload(fileArray);
    } finally {
      setIsUploading(false);
    }
  }, [onUpload, canUpload]);

  // Drag and drop handlers
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (canUpload) setIsDragging(true);
  }, [canUpload]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    if (!canUpload) return;
    
    const { files } = e.dataTransfer;
    if (files.length > 0) {
      handleFileSelect(files);
    }
  }, [canUpload, handleFileSelect]);

  // Handle delete
  const handleDelete = async (attachment: Attachment) => {
    if (pendingDeleteId === attachment.id) {
      if (onDelete) {
        await onDelete(attachment.id);
      }
      setPendingDeleteId(null);
    } else {
      setPendingDeleteId(attachment.id);
    }
  };

  // Handle download
  const handleDownload = (attachment: Attachment) => {
    if (onDownload) {
      onDownload(attachment);
    } else if (attachment.url) {
      window.open(attachment.url, '_blank');
    }
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FaPaperclip className="text-slate-400" />
          <h3 className="text-lg font-medium text-slate-900 dark:text-white">Attachments</h3>
          <span className="px-2 py-0.5 text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-full">
            {attachments.length} files
          </span>
        </div>
        
        {canUpload && (
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors disabled:opacity-50"
          >
            {isUploading ? (
              <>
                <FaSpinner className="animate-spin" size={14} />
                Uploading...
              </>
            ) : (
              <>
                <FaUpload size={14} />
                Upload Files
              </>
            )}
          </button>
        )}
        
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => e.target.files && handleFileSelect(e.target.files)}
        />
      </div>

      {/* Drop zone */}
      {canUpload && (
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            isDragging
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
              : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
          }`}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          <FaCloudUploadAlt className={`mx-auto mb-3 ${isDragging ? 'text-blue-500' : 'text-slate-300 dark:text-slate-600'}`} size={40} />
          <p className="text-sm text-slate-600 dark:text-slate-400">
            {isDragging ? 'Drop files here...' : 'Drag and drop files here, or click Upload Files'}
          </p>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
            Supports PDF, Word, Excel, Images up to 10MB
          </p>
        </div>
      )}

      {/* Attachments list */}
      {attachments.length === 0 ? (
        <div className="text-center py-8 bg-slate-50 dark:bg-slate-900/50 rounded-lg">
          <FaPaperclip className="mx-auto text-slate-300 dark:text-slate-600 mb-3" size={32} />
          <p className="text-slate-500 dark:text-slate-400">No attachments</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {attachments.map((attachment) => {
            const FileIcon = getFileIcon(attachment.type);
            const iconColor = getFileColor(attachment.type);
            const isPendingDelete = pendingDeleteId === attachment.id;

            return (
              <div
                key={attachment.id}
                className="flex items-center gap-4 p-4 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg hover:border-slate-300 dark:hover:border-slate-600 transition-colors"
              >
                {/* File icon */}
                <div className={`p-3 rounded-lg bg-slate-100 dark:bg-slate-900 ${iconColor}`}>
                  <FileIcon size={24} />
                </div>

                {/* File info */}
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-900 dark:text-white truncate">
                    {attachment.name}
                  </p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    {formatFileSize(attachment.size)} • Uploaded by {attachment.uploadedBy} on {formatDate(attachment.uploadedAt)}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  {/* Preview button for images */}
                  {attachment.type.includes('image') && (
                    <button
                      onClick={() => setPreviewAttachment(attachment)}
                      className="p-2 text-slate-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                      title="Preview"
                    >
                      <FaEye size={16} />
                    </button>
                  )}
                  
                  {/* Download button */}
                  <button
                    onClick={() => handleDownload(attachment)}
                    className="p-2 text-slate-400 hover:text-green-500 hover:bg-green-50 dark:hover:bg-green-900/30 rounded-lg transition-colors"
                    title="Download"
                  >
                    <FaDownload size={16} />
                  </button>
                  
                  {/* Delete button */}
                  {canUpload && (
                    isPendingDelete ? (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleDelete(attachment)}
                          className="px-2 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
                        >
                          Confirm
                        </button>
                        <button
                          onClick={() => setPendingDeleteId(null)}
                          className="px-2 py-1 text-xs bg-slate-300 dark:bg-slate-600 text-slate-700 dark:text-slate-200 rounded hover:bg-slate-400 dark:hover:bg-slate-500 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => handleDelete(attachment)}
                        className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                        title="Delete"
                      >
                        <FaTrash size={16} />
                      </button>
                    )
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Image preview modal */}
      {previewAttachment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
          <div className="relative max-w-4xl max-h-[90vh] p-4">
            <button
              onClick={() => setPreviewAttachment(null)}
              className="absolute top-2 right-2 p-2 bg-white/80 rounded-full hover:bg-white transition-colors"
            >
              <FaTimes size={16} />
            </button>
            {previewAttachment.url && (
              <img
                src={previewAttachment.url}
                alt={previewAttachment.name}
                className="max-w-full max-h-[85vh] object-contain rounded-lg"
              />
            )}
            <p className="text-center text-white mt-2">{previewAttachment.name}</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default AttachmentsTab;
